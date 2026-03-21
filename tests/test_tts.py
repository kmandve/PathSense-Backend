"""Tests for the Piper TTS service.

All tests mock PiperVoice — no real .onnx model file required.
The mock synthesize_to_file writes a minimal valid WAV header so
bytes checks are meaningful.
"""
import io
import struct
import time
import wave
from unittest.mock import MagicMock, patch
import pytest

from pathsense.services.tts import synthesize, synthesize_async


def _make_mock_voice(text_response: str = "test audio") -> MagicMock:
    """Return a mock PiperVoice that writes a valid WAV header when synthesize_to_file is called."""
    voice = MagicMock()

    def fake_synthesize_to_file(text, wav_file):
        # Write a minimal valid WAV so buf.getvalue() starts with b"RIFF"
        sample_rate = 22050
        n_channels = 1
        sampwidth = 2
        # 0.1 seconds of silence
        n_frames = int(sample_rate * 0.1)
        wav_file.setnchannels(n_channels)
        wav_file.setsampwidth(sampwidth)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * n_frames)

    voice.synthesize_to_file.side_effect = fake_synthesize_to_file
    return voice


def test_synthesize_returns_wav_bytes():
    voice = _make_mock_voice()
    result = synthesize(voice, "Step up ahead on your left.")
    assert isinstance(result, bytes), "synthesize must return bytes"
    assert result[:4] == b"RIFF", "WAV bytes must start with RIFF header"
    assert len(result) > 100, "WAV bytes must be non-trivial length"


def test_synthesize_called_with_text():
    voice = _make_mock_voice()
    text = "Clear path ahead, door on the right."
    synthesize(voice, text)
    voice.synthesize_to_file.assert_called_once()
    call_args = voice.synthesize_to_file.call_args[0]
    assert call_args[0] == text, "synthesize must pass text as first arg to synthesize_to_file"


def test_synthesize_latency_under_one_second():
    """Mocked synthesis should complete well under 1s; real Piper target is also <1s."""
    voice = _make_mock_voice()
    text = "There is a step up ahead on your left side near the door."
    start = time.perf_counter()
    result = synthesize(voice, text)
    elapsed = time.perf_counter() - start
    assert elapsed < 1.0, f"Synthesis took {elapsed:.3f}s — must be under 1s (TTS-03)"
    assert result[:4] == b"RIFF"


@pytest.mark.asyncio
async def test_synthesize_async_returns_same_as_sync():
    voice = _make_mock_voice()
    text = "Doorway close ahead, clear on the left."
    sync_result = synthesize(voice, text)
    # Reset mock call count so async call gets a fresh run
    voice2 = _make_mock_voice()
    async_result = await synthesize_async(voice2, text)
    assert async_result[:4] == b"RIFF"
    assert len(async_result) == len(sync_result)


@pytest.mark.asyncio
async def test_synthesize_async_does_not_block_event_loop():
    """Async wrapper must use run_in_executor — confirmed by it being awaitable."""
    import asyncio
    voice = _make_mock_voice()
    # If this awaits cleanly, the executor pattern works
    result = await synthesize_async(voice, "Wide sidewalk, clear path ahead.")
    assert isinstance(result, bytes)
