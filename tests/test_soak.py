"""Soak test verifying stability of POST /analyze under repeated use."""
import io
import pytest
from PIL import Image


@pytest.mark.asyncio
async def test_20_sequential_inferences_no_error(async_client):
    """Soak test: 20 sequential POST /analyze calls complete without error.
    Uses mock model so no GPU needed. Validates endpoint stability."""
    img = Image.new("RGB", (200, 200), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    jpeg_bytes = buf.getvalue()

    for i in range(20):
        response = await async_client.post(
            "/analyze",
            files={"file": (f"test_{i}.jpg", jpeg_bytes, "image/jpeg")},
        )
        assert response.status_code == 200, f"Request {i+1}/20 failed with status {response.status_code}"
        data = response.json()
        assert "description" in data, f"Request {i+1}/20 missing 'description' key"
        assert len(data["description"]) > 0, f"Request {i+1}/20 returned empty description"
