MAX_IMAGE_DIM = 512
SUPPORTED_CONTENT_TYPES = {"image/jpeg", "image/png"}

import os
PIPER_VOICE_MODEL_PATH = os.getenv(
    "PIPER_VOICE_MODEL_PATH",
    "models/en_US-lessac-medium.onnx"
)
