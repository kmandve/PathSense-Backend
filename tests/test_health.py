import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_health_returns_200_with_model(async_client):
    with patch("pathsense.routes.analyze.torch.cuda.is_available", return_value=True), \
         patch("pathsense.routes.analyze.torch.cuda.memory_reserved", return_value=2621440000):
        response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True
    assert "vram_reserved_mb" in data


@pytest.mark.asyncio
async def test_health_returns_503_without_model():
    from httpx import AsyncClient, ASGITransport
    from pathsense.main import app
    # Ensure no model loaded
    app.state.vision_model = None
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 503
