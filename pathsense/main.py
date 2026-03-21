from contextlib import asynccontextmanager
from fastapi import FastAPI
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from pathsense.config import MODEL_ID, TOKENIZER_ID, TOKENIZER_REVISION
from pathsense.routes.analyze import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load model once (INF-02)
    app.state.vision_model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        trust_remote_code=True,
        device_map={"": "cuda"},  # INF-03: CUDA acceleration
    )
    app.state.tokenizer = AutoTokenizer.from_pretrained(
        TOKENIZER_ID,
        revision=TOKENIZER_REVISION,
        trust_remote_code=True,
    )
    yield
    # Shutdown: cleanup
    del app.state.vision_model
    del app.state.tokenizer
    torch.cuda.empty_cache()


app = FastAPI(title="PathSense", lifespan=lifespan)
app.include_router(router)
