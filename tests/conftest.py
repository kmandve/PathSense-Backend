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
