from fastapi import APIRouter, Request, HTTPException, UploadFile
import io
import torch
from PIL import Image, UnidentifiedImageError

from pathsense.config import SUPPORTED_CONTENT_TYPES
from pathsense.services.vision import run_inference_async

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    model_loaded = hasattr(request.app.state, "vision_model") and request.app.state.vision_model is not None
    cuda_ok = torch.cuda.is_available()
    if not model_loaded or not cuda_ok:
        raise HTTPException(status_code=503, detail="Model not ready")
    vram_reserved_mb = round(torch.cuda.memory_reserved() / 1024**2, 1)
    return {
        "status": "ok",
        "model_loaded": model_loaded,
        "cuda": cuda_ok,
        "vram_reserved_mb": vram_reserved_mb,
    }


@router.post("/analyze")
async def analyze(file: UploadFile, request: Request):
    # IMG-02: Validate content type before reading bytes (fail fast)
    if file.content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image type: {file.content_type}. Accepted: JPEG, PNG"
        )

    # IMG-01: Read upload bytes ONCE (Pitfall 4: UploadFile read twice returns empty)
    image_bytes = await file.read()

    # Decode and validate actual image data
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except (UnidentifiedImageError, Exception):
        raise HTTPException(
            status_code=400,
            detail="File is not a valid image or is corrupted"
        )

    # Check model is available
    model = request.app.state.vision_model
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    # VIS-02: Run inference via vision service (handles resize + VRAM cleanup)
    try:
        description = await run_inference_async(model, img)
    except Exception as e:
        # D-09: Return 500 with message for inference failures (fallback is Phase 4)
        raise HTTPException(
            status_code=500,
            detail=f"Inference failed: {str(e)}"
        )

    return {"description": description}
