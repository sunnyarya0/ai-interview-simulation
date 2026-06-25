import asyncio
import re
from collections.abc import Awaitable, Callable
from functools import lru_cache

from app.core.config import settings
from app.core.logger import logger
from app.db.models import TranscriptTurn
from app.db.session import AsyncSessionLocal
from app.orchestrator.prompt import (
    build_closing_prompt,
    build_greeting_prompt,
    build_system_prompt,
    build_turn_prompt,
)
from app.orchestrator.state import InterviewState

SendJson = Callable[[dict], Awaitable[None]]
SendBytes = Callable[[bytes], Awaitable[None]]


# Heavy adapters are shared singletons (models are cached); lazy so importing this
# module stays light and the orchestrator is unit-testable without loading them.
@lru_cache
def _stt():
    from app.pipeline.stt import STTAdapter

    return STTAdapter()


@lru_cache
def _tts():
    from app.pipeline.tts import TTSAdapter

    return TTSAdapter()


@lru_cache
def _llm():
    from app.pipeline.llm import LLMAdapter

    return LLMAdapter()


@lru_cache
def _retriever():
    from app.pipeline.retriever import Retriever

    return Retriever()


def _split_complete_sentences(buffer: str) -> tuple[list[str], str]:
    """Return (complete sentences, remainder) — flush only sentences ending in . ! ?."""
    parts = re.split(r"(?<=[.!?])\s+", buffer)
    if not buffer or buffer.rstrip()[-1:] in ".!?":
        return [p for p in parts if p.strip()], ""
    return [p for p in parts[:-1] if p.strip()], parts[-1]


class InterviewOrchestrator:
    """Owns one interview's live state and conducts the conversation
    (listen -> transcribe -> retrieve -> think -> speak)."""

    def __init__(
        self,
        interview_id: str,
        resume_id: str,
        profile: dict,
        send_json: SendJson,
        send_bytes: SendBytes,
    ):
        self.interview_id = interview_id
        self.resume_id = resume_id
        self.profile = profile or {}
        self._send_json = send_json
        self._send_bytes = send_bytes

        self.state = InterviewState.GREETING
        self.history: list[dict] = []
        self.audio_buf = bytearray()
        self.turn_count = 0
        self._turn_index = 0
        self.system_prompt = build_system_prompt(self.profile)

    # ---- bookkeeping -------------------------------------------------------

    async def transition(self, new_state: InterviewState) -> None:
        self.state = new_state
        await self._send_json({"type": "state", "value": new_state.value})

    def on_audio(self, frame: bytes) -> None:
        self.audio_buf.extend(frame)

    def _take_audio(self) -> bytes:
        data = bytes(self.audio_buf)
        self.audio_buf.clear()
        return data

    async def _persist_turn(self, speaker: str, text: str) -> None:
        async with AsyncSessionLocal() as session:
            session.add(
                TranscriptTurn(
                    interview_id=self.interview_id,
                    speaker=speaker,
                    text=text,
                    turn_index=self._turn_index,
                )
            )
            await session.commit()
        self._turn_index += 1

    async def append_turn(self, speaker: str, text: str) -> None:
        """history + persist + emit transcript (used for the candidate turn and in tests)."""
        self.history.append({"speaker": speaker, "text": text})
        await self._persist_turn(speaker, text)
        await self._send_json({"type": "transcript", "speaker": speaker, "text": text})

    # ---- speaking pipeline -------------------------------------------------

    async def _speak_sentence(self, sentence: str) -> None:
        wav = await asyncio.to_thread(_tts().synthesize, sentence)
        await self._send_bytes(wav)
        await self._send_json({"type": "transcript", "speaker": "ai", "text": sentence})

    async def _generate_and_speak(self, prompt: str) -> str:
        """Stream the LLM, speaking each sentence as it completes (pipeline overlap).
        Records the full AI turn at the end."""
        spoken: list[str] = []
        buffer = ""
        async for token in _llm().stream(prompt, self.system_prompt):
            buffer += token
            sentences, buffer = _split_complete_sentences(buffer)
            for sentence in sentences:
                await self._speak_sentence(sentence)
                spoken.append(sentence)
        if buffer.strip():
            await self._speak_sentence(buffer.strip())
            spoken.append(buffer.strip())

        text = " ".join(spoken).strip()
        self.history.append({"speaker": "ai", "text": text})
        await self._persist_turn("ai", text)
        return text

    # ---- conversation flow -------------------------------------------------

    async def start(self) -> None:
        await self.transition(InterviewState.GREETING)
        await self._generate_and_speak(build_greeting_prompt(self.profile))
        await self.transition(InterviewState.LISTENING)

    async def on_end_of_utterance(self) -> None:
        if self.state != InterviewState.LISTENING:
            return  # ignore stray signals while thinking/speaking
        audio = self._take_audio()
        if not audio:
            return

        await self.transition(InterviewState.THINKING)
        text = await asyncio.to_thread(_stt().transcribe, audio)
        if not text.strip():
            await self.transition(InterviewState.LISTENING)
            return

        # Emit + persist the candidate turn; build the prompt from history BEFORE
        # appending this answer (build_turn_prompt adds it via the last_answer arg).
        await self._send_json({"type": "transcript", "speaker": "candidate", "text": text})
        await self._persist_turn("candidate", text)
        rag_context = await _retriever().retrieve(text, self.resume_id)
        prompt = build_turn_prompt(self.history, rag_context, text)
        self.history.append({"speaker": "candidate", "text": text})

        await self.transition(InterviewState.SPEAKING)
        await self._generate_and_speak(prompt)
        self.turn_count += 1

        if self.turn_count >= settings.MAX_INTERVIEW_TURNS:
            await self._close()
        else:
            await self.transition(InterviewState.LISTENING)

    async def _close(self) -> None:
        await self.transition(InterviewState.CLOSING)
        await self._generate_and_speak(build_closing_prompt(self.profile))
        await self.transition(InterviewState.DONE)
        await self._send_json({"type": "interview_end"})
        logger.info("interview {} closed at turn cap ({})", self.interview_id, self.turn_count)

    async def on_end_interview(self) -> None:
        await self.transition(InterviewState.DONE)
        await self._send_json({"type": "interview_end"})
        logger.info("interview {} ended early ({} turns)", self.interview_id, self.turn_count)
