import base64
import torch
from fastapi import APIRouter, Request, HTTPException, UploadFile
import io
from PIL import Image, UnidentifiedImageError

from pathsense.config import SUPPORTED_CONTENT_TYPES
from pathsense.services.vision import run_inference_async
from pathsense.services.tts import synthesize_async

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    model_loaded = (
        hasattr(request.app.state, "vision_model")
        and request.app.state.vision_model is not None
    )
    if not model_loaded:
        raise HTTPException(status_code=503, detail="Model not loaded")
    vram_mb = (
        torch.cuda.memory_reserved() / 1024 ** 2
        if torch.cuda.is_available()
        else 0.0
    )
    return {"status": "ok", "model_loaded": True, "vram_reserved_mb": vram_mb}


@router.post("/analyze")
async def analyze(request: Request, file: UploadFile):
    # Validate content type
    if file.content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image type: {file.content_type}. Accepted: JPEG, PNG"
        )

    image_bytes = await file.read()

    # Decode and validate
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except (UnidentifiedImageError, Exception):
        raise HTTPException(
            status_code=400,
            detail="File is not a valid image or is corrupted"
        )

    # Run vision inference
    try:
        description = await run_inference_async(img)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Inference failed: {str(e)}"
        )

    # Run TTS synthesis
    try:
        wav_bytes = await synthesize_async(request.app.state.tts_voice, description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")

    audio_b64 = base64.b64encode(wav_bytes).decode("utf-8")
    return {"description": description, "audio": audio_b64}
