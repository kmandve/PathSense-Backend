"""Integration tests for POST /analyze endpoint."""
import io
import pytest
from PIL import Image


@pytest.mark.asyncio
async def test_upload_jpeg(async_client, test_image_bytes):
    """IMG-01: POST /analyze with valid JPEG returns 200."""
    response = await async_client.post(
        "/analyze",
        files={"file": ("test.jpg", test_image_bytes, "image/jpeg")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "description" in data
    assert len(data["description"]) > 0


@pytest.mark.asyncio
async def test_upload_png(async_client):
    """IMG-01: POST /analyze with valid PNG returns 200."""
    img = Image.new("RGB", (100, 100), color="green")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    response = await async_client.post(
        "/analyze",
        files={"file": ("test.png", buf.getvalue(), "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "description" in data


@pytest.mark.asyncio
async def test_invalid_content_type(async_client):
    """IMG-02: Non-image content type returns 415."""
    response = await async_client.post(
        "/analyze",
        files={"file": ("test.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_unsupported_image_type(async_client):
    """IMG-02: Unsupported image format returns 415."""
    response = await async_client.post(
        "/analyze",
        files={"file": ("test.gif", b"fake gif", "image/gif")},
    )
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_corrupt_image_returns_400(async_client):
    """IMG-02: Valid content type but corrupt data returns 400."""
    response = await async_client.post(
        "/analyze",
        files={"file": ("bad.jpg", b"not actually jpeg data", "image/jpeg")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_description_is_string(async_client, test_image_bytes):
    """VIS-02: Response description is a non-empty string."""
    response = await async_client.post(
        "/analyze",
        files={"file": ("test.jpg", test_image_bytes, "image/jpeg")},
    )
    data = response.json()
    assert isinstance(data["description"], str)
    assert len(data["description"]) > 0


@pytest.mark.asyncio
async def test_description_mentions_navigation_object(async_client, test_image_bytes):
    """VIS-03: Description identifies at least one navigation-relevant object.
    Note: With mock model returning 'Doorway close ahead, clear path through.',
    this should find 'doorway' which maps to the 'door' category."""
    response = await async_client.post(
        "/analyze",
        files={"file": ("test.jpg", test_image_bytes, "image/jpeg")},
    )
    data = response.json()
    desc_lower = data["description"].lower()
    hazard_words = {"obstacle", "door", "doorway", "step", "stairs", "sign", "person",
                    "people", "chair", "table", "wall", "curb", "pole", "clear", "path"}
    found = any(word in desc_lower for word in hazard_words)
    assert found, f"No navigation object found in: {data['description']}"
