"""Vision inference service for PathSense navigation descriptions."""

import asyncio
from concurrent.futures import ThreadPoolExecutor

import torch
from PIL import Image

from pathsense.config import MAX_IMAGE_DIM

# Navigation prompt encoding all six locked decisions (D-01 through D-06).
NAVIGATION_PROMPT = (
    "In 1-2 short sentences under 15 words total, describe immediate navigation hazards "
    "directly ahead. Prioritize nearest hazard first: obstacles, steps, doors, signs, people. "
    "Use relative distance words only: 'close', 'nearby', 'far ahead'. "
    "No numeric distance estimates. "
    "Tone: calm guidance, not urgent commands. "
    "If path is clear, describe the scene briefly with spatial context: "
    "'Open hallway, clear path ahead.' Not just 'Clear.' "
    "End with directional framing when relevant: 'clear on the left', 'obstacle on the right'."
)

# Single-worker executor to serialize GPU access and prevent VRAM contention.
_executor = ThreadPoolExecutor(max_workers=1)


def _run_inference(model, image: Image.Image) -> str:
    """Run Moondream inference synchronously. Call via run_in_executor only."""
    try:
        # Resize to MAX_IMAGE_DIM preserving aspect ratio (IMG-03)
        image.thumbnail((MAX_IMAGE_DIM, MAX_IMAGE_DIM))
        result = model.query(image, NAVIGATION_PROMPT)
        return result["answer"]
    finally:
        torch.cuda.empty_cache()  # Prevent VRAM fragmentation (Pitfall 3)


async def run_inference_async(model, image: Image.Image) -> str:
    """Non-blocking inference wrapper. Keeps event loop free for health checks."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _run_inference, model, image)
