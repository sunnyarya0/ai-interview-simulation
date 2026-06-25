"""Phase 4 verification client: drives a full voice interview over the WebSocket.

Usage: uv run python scripts/interview_client.py <interview_id>
Synthesizes candidate answers with macOS `say`, streams them as 16kHz PCM, and
prints the AI interviewer's spoken responses (transcripts + audio byte counts).
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import wave

import websockets


def synth_pcm(text: str) -> bytes:
    """text -> 16kHz mono int16 PCM bytes (the STT input contract), via say + ffmpeg."""
    aiff = tempfile.mktemp(suffix=".aiff")
    wav = tempfile.mktemp(suffix=".wav")
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


async def drain_until_ready(ws) -> str:
    """Receive AI messages until the server returns to 'listening' or ends. Returns final state."""
    audio_bytes = 0
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=120)
        if isinstance(raw, (bytes, bytearray)):
            audio_bytes += len(raw)
            continue
        msg = json.loads(raw)
        if msg["type"] == "transcript":
            print(f"   [{msg['speaker']}] {msg['text']}")
        elif msg["type"] == "state" and msg["value"] in ("listening", "done"):
            print(f"   (ai audio: {audio_bytes} bytes; state -> {msg['value']})")
            return msg["value"]
        elif msg["type"] == "interview_end":
            print("   (interview_end)")
            return "done"
        elif msg["type"] == "error":
            print(f"   ERROR: {msg['message']}")
            return "done"


async def main(interview_id: str):
    answers = [
        "I worked as a senior machine learning engineer at DataCorp, where I built recommendation systems serving millions of users.",
        "The hardest part was scaling model serving. I solved it by migrating our inference to kubernetes with autoscaling.",
    ]
    uri = f"ws://localhost:8000/interviews/{interview_id}/stream"
    async with websockets.connect(uri, max_size=None) as ws:
        print("--- GREETING ---")
        state = await drain_until_ready(ws)

        for i, ans in enumerate(answers, 1):
            if state == "done":
                break
            print(f"--- CANDIDATE ANSWER {i} ---\n   [candidate-spoken] {ans}")
            pcm = synth_pcm(ans)
            for j in range(0, len(pcm), 3200):  # ~100ms frames
                await ws.send(pcm[j : j + 3200])
            await ws.send(json.dumps({"type": "end_of_utterance"}))
            print("--- AI RESPONSE ---")
            state = await drain_until_ready(ws)

        if state != "done":
            print("--- ENDING INTERVIEW ---")
            await ws.send(json.dumps({"type": "end_interview"}))
            try:
                await asyncio.wait_for(ws.recv(), timeout=10)
            except Exception:
                pass
    print("CLIENT DONE")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
