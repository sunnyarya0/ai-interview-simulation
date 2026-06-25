from functools import lru_cache

import numpy as np
from faster_whisper import WhisperModel

from app.core.config import settings
from app.core.logger import logger


@lru_cache
def _get_model() -> WhisperModel:
    logger.info(
        "Loading Whisper model {} (device={}, compute={})",
        settings.WHISPER_MODEL,
        settings.WHISPER_DEVICE,
        settings.WHISPER_COMPUTE_TYPE,
    )
    return WhisperModel(
        settings.WHISPER_MODEL,
        device=settings.WHISPER_DEVICE,
        compute_type=settings.WHISPER_COMPUTE_TYPE,
    )


def _pcm_to_float32(audio_bytes: bytes) -> np.ndarray:
    """16kHz mono int16 little-endian PCM bytes -> float32 array in [-1, 1]."""
    return np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0


class STTAdapter:
    """Local speech-to-text via faster-whisper. Methods are sync/CPU-bound;
    callers in the live loop run them through asyncio.to_thread."""

    def __init__(self):
        self.model = _get_model()

    def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        audio = _pcm_to_float32(audio_bytes)
        segments, _ = self.model.transcribe(audio, language="en")
        return " ".join(seg.text.strip() for seg in segments).strip()

    def transcribe_with_vad(self, audio_bytes: bytes, sample_rate: int = 16000) -> tuple[str, bool]:
        """Transcribe with voice-activity filtering. Returns (text, is_speech)."""
        audio = _pcm_to_float32(audio_bytes)
        segments, _ = self.model.transcribe(audio, language="en", vad_filter=True)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text, bool(text)


if __name__ == "__main__":
    import subprocess
    import sys
    import wave

    # Generate a known-words clip with macOS `say`, decode to 16kHz mono PCM via ffmpeg.
    phrase = "I have experience building machine learning systems in python"
    subprocess.run(
        ["say", "-o", "/tmp/stt_test.aiff", phrase], check=True
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", "/tmp/stt_test.aiff", "-ar", "16000", "-ac", "1",
         "-acodec", "pcm_s16le", "/tmp/stt_test.wav"],
        check=True, capture_output=True,
    )
    with wave.open("/tmp/stt_test.wav", "rb") as wf:
        pcm = wf.readframes(wf.getnframes())

    text = STTAdapter().transcribe(pcm)
    print("spoken :", phrase)
    print("heard  :", text)
    assert "machine learning" in text.lower(), "expected key words to round-trip"
    print("OK")
    sys.exit(0)
