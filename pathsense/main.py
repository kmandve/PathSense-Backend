from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from piper.voice import PiperVoice
from pathsense.config import PIPER_VOICE_MODEL_PATH
from pathsense.routes.analyze import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load Piper TTS voice once at startup (CPU ONNX — leaves VRAM for vision model)
    app.state.tts_voice = PiperVoice.load(PIPER_VOICE_MODEL_PATH)
    yield
    # No explicit cleanup needed for ONNX CPU model


app = FastAPI(title="PathSense", lifespan=lifespan)
app.include_router(router)
