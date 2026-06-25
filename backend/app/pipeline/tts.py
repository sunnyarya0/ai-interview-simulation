import asyncio
import re
import subprocess
import tempfile
from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path

from app.core.config import settings
from app.core.logger import logger

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


class SayBackend:
    """macOS built-in TTS via the `say` command. Zero install; macOS only."""

    def synthesize(self, text: str) -> bytes:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            out_path = tmp.name
        try:
            subprocess.run(
                ["say", "--data-format=LEI16@16000", "--file-format=WAVE", "-o", out_path, text],
                check=True,
                capture_output=True,
            )
            return Path(out_path).read_bytes()
        finally:
            Path(out_path).unlink(missing_ok=True)


class PiperBackend:
    """Cross-platform local neural TTS via piper-tts. Requires `uv add piper-tts`
    and a downloaded voice model at settings.PIPER_VOICE_PATH."""

    def __init__(self):
        import io  # noqa: F401 — keep heavy imports lazy
        from piper import PiperVoice

        self._voice = PiperVoice.load(settings.PIPER_VOICE_PATH)

    def synthesize(self, text: str) -> bytes:
        import io
        import wave

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            self._voice.synthesize(text, wav_file)
        return buffer.getvalue()


@lru_cache
def _get_backend():
    engine = settings.TTS_ENGINE.lower()
    logger.info("Initialising TTS backend: {}", engine)
    if engine == "piper":
        return PiperBackend()
    return SayBackend()


class TTSAdapter:
    """Local text-to-speech. Emits WAV bytes. Methods are sync/CPU-bound;
    the live loop runs them via asyncio.to_thread."""

    def __init__(self):
        self.backend = _get_backend()

    def synthesize(self, text: str) -> bytes:
        return self.backend.synthesize(text)

    async def synthesize_stream(self, text: str) -> AsyncIterator[bytes]:
        """Yield one WAV clip per sentence so playback can begin early."""
        sentences = [s for s in _SENTENCE_SPLIT.split(text.strip()) if s]
        for sentence in sentences:
            yield await asyncio.to_thread(self.backend.synthesize, sentence)


if __name__ == "__main__":
    wav = TTSAdapter().synthesize("Hello, I am your AI interviewer. Tell me about yourself.")
    out = "/tmp/tts_test.wav"
    Path(out).write_bytes(wav)
    print(f"wrote {len(wav)} bytes -> {out}")
    # Play it (macOS). Comment out in CI.
    subprocess.run(["afplay", out], check=False)
    print("OK")
