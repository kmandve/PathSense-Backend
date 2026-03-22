"""Vision inference service using GPT-4o for navigation descriptions."""

import base64
import os
from openai import AsyncOpenAI
from PIL import Image

from pathsense.config import MAX_IMAGE_DIM

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    """Lazily initialize the OpenAI client so imports succeed without OPENAI_API_KEY."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


NAVIGATION_PROMPT = (
    "You are a navigation assistant for a blind person using a smart cane. "
    "Describe what is directly ahead in this image in one short sentence (under 15 words). "
    "Focus on: obstacles, steps, doors, signs, people. "
    "Use relative distance words like 'close', 'nearby', 'far ahead' — no exact measurements. "
    "Be calm and informative, not alarming. "
    "If the path is clear, briefly describe the scene: 'Wide sidewalk, clear path ahead.' "
    "End with directional context when relevant: 'clear on the left', 'obstacle on the right'. "
    "IMPORTANT: Always provide your best description, even if the image is blurry, dark, or unclear. "
    "Never apologize or say you cannot describe the image. Instead, describe what you can see "
    "and note any uncertainty briefly, e.g. 'Dim area, possibly a hallway ahead — proceed with caution.'"
)


async def run_inference_async(image: Image.Image) -> str:
    """Send image to GPT-4o vision API and return navigation description."""
    client = _get_client()

    # Resize preserving aspect ratio
    image.thumbnail((MAX_IMAGE_DIM, MAX_IMAGE_DIM))

    # Encode to base64 JPEG
    import io
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    b64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": NAVIGATION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
                    },
                ],
            }
        ],
        max_tokens=60,
    )

    return response.choices[0].message.content.strip()
