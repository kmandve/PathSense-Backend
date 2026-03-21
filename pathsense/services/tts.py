"""TTS service using Piper for local, offline speech synthesis."""

import asyncio
import io
import wave
from piper.voice import PiperVoice


def synthesize(voice: PiperVoice, text: str) -> bytes:
    """Convert text to WAV bytes using Piper TTS (runs on CPU via ONNX).

    Returns raw WAV bytes (16-bit PCM, 22050Hz) — standard format for
    headphone playback. Runs synchronously; call synthesize_async from
    async contexts to avoid blocking the event loop.
    """
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        voice.synthesize_to_file(text, wav_file)
    return buf.getvalue()


async def synthesize_async(voice: PiperVoice, text: str) -> bytes:
    """Non-blocking wrapper around synthesize().

    Uses the default executor (ThreadPoolExecutor) so the FastAPI event
    loop remains free during CPU-bound ONNX inference. Pattern mirrors
    vision.py's run_inference_async design (per D-05).
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, synthesize, voice, text)
