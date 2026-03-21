from fastapi import APIRouter, Request, HTTPException
import torch

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
