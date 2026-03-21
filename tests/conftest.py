import os
import pytest
from unittest.mock import MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport
from pathsense.main import app


@pytest.fixture
def mock_model():
    """Mock vision model that returns a navigation description."""
    model = MagicMock()
    model.query.return_value = {"answer": "Doorway close ahead, clear path through."}
    return model


@pytest.fixture
def mock_tokenizer():
    return MagicMock()


@pytest.fixture
def app_with_model(mock_model, mock_tokenizer):
    """App with mocked model in state (no GPU needed for tests)."""
    app.state.vision_model = mock_model
    app.state.tokenizer = mock_tokenizer
    yield app
    # Cleanup
    app.state.vision_model = None
    app.state.tokenizer = None


@pytest.fixture
async def async_client(app_with_model):
    transport = ASGITransport(app=app_with_model)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def test_image_path():
    return os.path.join(os.path.dirname(__file__), "fixtures", "test_image.jpg")


@pytest.fixture
def test_image_bytes(test_image_path):
    with open(test_image_path, "rb") as f:
        return f.read()


@pytest.fixture
def mock_tts_voice():
    """Mock Piper TTS voice for tests — no .onnx file needed."""
    from unittest.mock import MagicMock
    import wave

    voice = MagicMock()

    def fake_synthesize_to_file(text, wav_file):
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(b"\x00\x00" * 2205)  # 0.1s silence

    voice.synthesize_to_file.side_effect = fake_synthesize_to_file
    return voice


@pytest.fixture
def app_with_tts(mock_tts_voice):
    """App with mocked TTS voice in state — no .onnx file needed."""
    app.state.tts_voice = mock_tts_voice
    yield app
    app.state.tts_voice = None
