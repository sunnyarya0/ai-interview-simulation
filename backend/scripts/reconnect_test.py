"""S28 verification: prove a transient drop is resumable and only a graceful end completes.

Usage: uv run python scripts/reconnect_test.py <interview_id>
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import wave

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import websockets
from sqlalchemy import func, select

from app.db.models import Feedback, Interview, TranscriptTurn
from app.db.session import AsyncSessionLocal

URI = "ws://localhost:8000/interviews/{}/stream"


def synth_pcm(text: str) -> bytes:
    aiff, wav = tempfile.mktemp(suffix=".aiff"), tempfile.mktemp(suffix=".wav")
    try:
        subprocess.run(["say", "-o", aiff, text], check=True)
        subprocess.run(
            ["ffmpeg", "-y", "-i", aiff, "-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le", wav],
            check=True, capture_output=True,
        )
        with wave.open(wav, "rb") as w:
            return w.readframes(w.getnframes())
    finally:
        for f in (aiff, wav):
            if os.path.exists(f):
                os.unlink(f)


async def drain_until_ready(ws):
    """Collect text transcripts until state listening/done. Returns (last_ai_text, final_state)."""
    last_ai = None
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=120)
        if isinstance(raw, (bytes, bytearray)):
            continue
        msg = json.loads(raw)
        if msg["type"] == "transcript" and msg["speaker"] == "ai":
            last_ai = msg["text"]
        elif msg["type"] == "state" and msg["value"] in ("listening", "done"):
            return last_ai, msg["value"]
        elif msg["type"] == "interview_end":
            return last_ai, "done"


async def send_answer(ws, text):
    pcm = synth_pcm(text)
    for j in range(0, len(pcm), 3200):
        await ws.send(pcm[j : j + 3200])
    await ws.send(json.dumps({"type": "end_of_utterance"}))


async def db_state(iid):
    async with AsyncSessionLocal() as s:
        interview = await s.get(Interview, iid)
        n_turns = (await s.execute(select(func.count()).select_from(TranscriptTurn).where(TranscriptTurn.interview_id == iid))).scalar()
        fb = (await s.execute(select(Feedback).where(Feedback.interview_id == iid))).scalars().first()
        return interview.status, n_turns, fb is not None


async def main(iid):
    # --- First connection: greeting + one answered turn, then DROP (no end_interview) ---
    async with websockets.connect(URI.format(iid), max_size=None) as ws:
        ai_q1, _ = await drain_until_ready(ws)
        print(f"[1] greeting/Q: {ai_q1[:60]!r}")
        await send_answer(ws, "I built scalable recommendation systems at DataCorp using Python.")
        ai_q2, _ = await drain_until_ready(ws)
        print(f"[1] AI follow-up: {ai_q2[:60]!r}")
        # simulate a network drop: close the socket abruptly, no end_interview
    print("[1] socket dropped (no end_interview)")

    await asyncio.sleep(1)
    status, turns, has_fb = await db_state(iid)
    print(f"[check] after drop -> status={status}, turns={turns}, feedback={has_fb}")
    assert status == "active", f"expected active after drop, got {status}"
    assert not has_fb, "feedback should NOT be generated on a transient drop"

    # --- Reconnect: expect resume (replay last AI question), NOT a new greeting ---
    async with websockets.connect(URI.format(iid), max_size=None) as ws:
        replayed, _ = await drain_until_ready(ws)
        print(f"[2] resumed, replayed AI: {replayed[:60]!r}")
        # ai_q2 was the last streamed sentence; resume replays the full last AI turn.
        assert replayed and ai_q2 in replayed, "resume should replay the last AI question, not greet anew"
        # answer once more, then gracefully end
        await send_answer(ws, "The main challenge was latency, solved with Redis caching.")
        await drain_until_ready(ws)
        await ws.send(json.dumps({"type": "end_interview"}))
        try:
            await asyncio.wait_for(ws.recv(), timeout=10)
        except Exception:
            pass
    print("[2] ended gracefully")

    # --- After graceful end: completed + feedback scheduled ---
    for _ in range(15):
        status, turns, has_fb = await db_state(iid)
        if status == "completed" and has_fb:
            break
        await asyncio.sleep(2)
    print(f"[check] after end -> status={status}, turns={turns}, feedback={has_fb}")
    assert status == "completed", f"expected completed, got {status}"
    assert has_fb, "feedback should be generated on graceful end"
    print("RECONNECT TEST PASSED")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
