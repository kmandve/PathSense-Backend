FROM python:3.12-slim

WORKDIR /app

# Install system deps for piper-tts
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download Piper voice model at build time
RUN mkdir -p models && \
    wget -q -O models/en_US-lessac-medium.onnx \
      'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx' && \
    wget -q -O models/en_US-lessac-medium.onnx.json \
      'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json'

# Copy app code
COPY pathsense/ pathsense/

EXPOSE 8000

CMD ["uvicorn", "pathsense.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
