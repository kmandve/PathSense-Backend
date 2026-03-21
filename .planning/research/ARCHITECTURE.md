# Architecture Research

**Domain:** Assistive vision API — local image-to-audio navigation pipeline
**Researched:** 2026-03-21
**Confidence:** HIGH (core pipeline patterns verified against official docs and live repos)

## Standard Architecture

### System Overview

```
Smart Cane Device
    │
    │  HTTP POST /analyze
    │  multipart/form-data (image bytes)
    ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │               API Layer (routes.py)                   │   │
│  │  • Accepts UploadFile (multipart)                     │   │
│  │  • Validates content-type (image/*)                   │   │
│  │  • Returns JSON { text, audio_b64 } or audio bytes   │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │                                        │
│  ┌──────────────────▼───────────────────────────────────┐   │
│  │             Vision Service (vision.py)                │   │
│  │  • Primary: Moondream2 local inference (CUDA)         │   │
│  │  • Fallback: GPT-4o via OpenAI API (base64 image)    │   │
│  │  • Returns navigation-focused text description        │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │                                        │
│  ┌──────────────────▼───────────────────────────────────┐   │
│  │              TTS Service (tts.py)                     │   │
│  │  • Piper TTS (ONNX, CPU inference by default)         │   │
│  │  • Converts text → WAV bytes (16-bit PCM, 22050 Hz)  │   │
│  │  • Returns raw audio bytes                            │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │                                        │
│  ┌──────────────────▼───────────────────────────────────┐   │
│  │            Response Builder (routes.py)               │   │
│  │  • Packages text + audio (base64 or binary)           │   │
│  │  • Returns to cane device                             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌───────────────── App State (lifespan) ──────────────┐    │
│  │  app.state.vision_model  ← loaded once at startup   │    │
│  │  app.state.tts_voice     ← loaded once at startup   │    │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow (end-to-end)

```
[Image bytes from cane]
    │
    ▼
[Decode → PIL Image object]
    │
    ▼
[Moondream2: model.query(image, navigation_prompt)]
    │  ~1–2 seconds on GTX 1650 (INT4/FP16)
    │  On failure / low confidence → GPT-4o API (base64 image)
    ▼
[Navigation description text]
    │  "There is a step up ahead on your left. A door is straight ahead."
    ▼
[Piper TTS: voice.synthesize_to_file(text) → WAV bytes]
    │  ~200–400ms on CPU (ONNX, no GPU needed)
    ▼
[Response: { "text": "...", "audio": "<base64 WAV>" }]
    │
    ▼
[Cane plays audio on headphones]
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| API Layer | Accept image upload, validate, route, return response | FastAPI endpoint with `UploadFile` |
| Vision Service | Convert image → navigation text; manage fallback logic | Moondream2 (transformers) + OpenAI SDK |
| TTS Service | Convert text → WAV audio bytes | Piper TTS (`piper-tts` package, ONNX) |
| App State (lifespan) | Load models once at startup; share as singletons | FastAPI `lifespan` context manager |
| Response Builder | Package text + audio for cane device | Inline in route handler |

## Recommended Project Structure

```
pathsense/
├── main.py                 # FastAPI app creation, lifespan, mounts routes
├── routes/
│   └── analyze.py          # POST /analyze endpoint
├── services/
│   ├── vision.py           # Moondream inference + GPT-4o fallback
│   └── tts.py              # Piper TTS synthesis
├── models/
│   └── state.py            # AppState dataclass (vision_model, tts_voice)
├── config.py               # Settings via pydantic-settings (env vars)
└── requirements.txt
```

### Structure Rationale

- **`services/`**: Vision and TTS are independent units with single responsibility; swapping either (e.g., Kokoro for Piper) touches only one file.
- **`models/state.py`**: Typed `AppState` prevents accidental None access to unloaded models.
- **`routes/`**: Keeps endpoint logic (HTTP concerns) separate from inference logic.
- **Flat `main.py`**: For a hackathon API with a single endpoint, minimal abstraction layers are appropriate.

## Architectural Patterns

### Pattern 1: Lifespan Singleton for Models

**What:** Load GPU-resident models once at application startup using FastAPI's `lifespan` context manager; store references in `app.state`.

**When to use:** Always, for any model loaded onto GPU. Loading per-request is 10–50x slower and risks VRAM exhaustion.

**Trade-offs:** Startup is slower (~5–10s); requests are fast. State is process-global (fine for single-worker Uvicorn).

**Example:**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from transformers import AutoModelForCausalLM
from piper.voice import PiperVoice

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load everything once
    app.state.vision_model = AutoModelForCausalLM.from_pretrained(
        "vikhyatk/moondream2",
        revision="2025-06-21",
        trust_remote_code=True,
        device_map={"": "cuda"},
    )
    app.state.tts_voice = PiperVoice.load("en_US-lessac-medium.onnx")
    yield
    # Shutdown: release CUDA memory
    del app.state.vision_model
    import torch; torch.cuda.empty_cache()

app = FastAPI(lifespan=lifespan)
```

### Pattern 2: Sequential Pipeline (not async/parallel)

**What:** Run vision inference → TTS synthesis as a blocking sequential chain, not concurrent tasks.

**When to use:** When both steps share the same GPU or when the second step depends entirely on the first step's output (which it does here: TTS needs the text).

**Trade-offs:** Simple, no concurrency bugs, no thread safety issues. Latency is additive (vision + TTS), but both are fast enough for the target < 3s budget.

**Example:**
```python
@router.post("/analyze")
async def analyze(file: UploadFile, request: Request):
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes))

    # Step 1: vision (GPU)
    text = request.app.state.vision_model.query(
        image, NAVIGATION_PROMPT
    )["answer"]

    # Step 2: TTS (CPU/ONNX)
    audio_bytes = synthesize(request.app.state.tts_voice, text)

    return {"text": text, "audio": base64.b64encode(audio_bytes).decode()}
```

### Pattern 3: Try/Except Fallback for Vision

**What:** Wrap Moondream inference in try/except; on failure call GPT-4o via OpenAI SDK with base64-encoded image.

**When to use:** When local model may fail (OOM, model error, low-quality output).

**Trade-offs:** Adds latency on fallback path (~1–3s network round-trip). Requires `OPENAI_API_KEY` env var and internet access. For hackathon, a simple boolean flag or env var can force-enable fallback for testing.

```python
async def describe_image(model, image: Image.Image) -> str:
    try:
        return model.query(image, NAVIGATION_PROMPT)["answer"]
    except Exception:
        return await gpt4o_fallback(image)

async def gpt4o_fallback(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    client = AsyncOpenAI()
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            {"type": "text", "text": NAVIGATION_PROMPT},
        ]}],
        max_tokens=100,
    )
    return response.choices[0].message.content
```

## Data Flow

### Request Flow

```
POST /analyze (multipart image)
    │
    ▼
UploadFile.read() → bytes
    │
    ▼
Image.open(BytesIO(bytes)) → PIL Image
    │
    ▼
VisionService.describe(image) → str
    ├── try: moondream2.query(image, prompt)["answer"]
    └── except: gpt4o_fallback(image)
    │
    ▼
TTSService.synthesize(text) → bytes (WAV)
    │
    ▼
JSONResponse { text: str, audio: base64-WAV-str }
```

### Key Data Flows

1. **Image to text:** PIL Image object passed directly to Moondream's `.query()` method. No temp file needed. The vision model lives on GPU (`cuda:0`); image is transferred to GPU at inference time.

2. **Text to audio:** String passed to Piper's `PiperVoice`; synthesis runs in-process via ONNX Runtime. Output is raw 16-bit PCM WAV bytes — base64-encode before JSON serialization, or return as `Response(content=bytes, media_type="audio/wav")`.

3. **GPU handoff:** Moondream runs on CUDA. Piper runs on CPU via ONNX (GPU optional). These two can co-exist on the same 4GB card because Piper uses ~100–200MB of RAM (not VRAM) for ONNX inference by default.

## GPU Memory Management (GTX 1650, 4GB VRAM)

This is the tightest constraint in the system.

### VRAM Budget

| Component | VRAM Usage | Notes |
|-----------|------------|-------|
| CUDA driver overhead | ~300–400MB | Always consumed |
| Moondream2 FP16 (2B params) | ~3.8GB | At full precision |
| Moondream2 INT4/Q4 quantized | ~1.0GB | Via bitsandbytes or GGUF |
| Moondream2 Q8 quantized | ~2.0GB | Near-FP16 quality |
| Piper TTS (ONNX, CPU) | 0MB VRAM | Runs entirely on CPU |
| Piper TTS (ONNX, CUDA) | ~100–200MB | Optional GPU path |
| KV cache + activations | ~200–400MB | Varies with output length |

**Recommended configuration for GTX 1650:**
- Load Moondream2 in **FP16 with bitsandbytes 8-bit quantization** → ~2GB VRAM
- Run Piper on **CPU** (default ONNX) → 0 VRAM usage
- Leaves ~1.5GB headroom for KV cache, activations, and CUDA overhead
- If 8-bit is still tight, INT4 quantization drops to ~1GB VRAM with acceptable quality loss for navigation descriptions

### Memory Management Rules

1. **Never load models inside request handlers.** Load once in lifespan; reuse for every request.
2. **Call `torch.cuda.empty_cache()` on shutdown**, not between requests (adds latency, doesn't help if only one model is running).
3. **Limit output tokens** in Moondream query (`max_new_tokens=80` is sufficient for navigation descriptions). KV cache grows with output length.
4. **Do not enable `reasoning=True`** in Moondream for this use case — it trades speed for accuracy and uses more memory.
5. **Run one request at a time.** Uvicorn single-worker mode; no concurrent GPU inference. A request queue forms naturally in the event loop.

## Suggested Build Order

Dependencies flow strictly forward — each component must exist before the next can be tested end-to-end.

```
1. Project scaffold + config
       │
       ▼
2. Vision Service (Moondream local)
   └── Verify: model loads, VRAM fits, returns text for test image
       │
       ▼
3. TTS Service (Piper)
   └── Verify: text in → WAV bytes out, plays correctly
       │
       ▼
4. API Layer (POST /analyze endpoint)
   └── Verify: curl with test image returns { text, audio }
       │
       ▼
5. GPT-4o Fallback
   └── Verify: force-trigger fallback, still returns valid response
       │
       ▼
6. Response packaging + latency measurement
   └── Verify: end-to-end < 3s on GTX 1650
```

**Rationale:** Vision service is the highest-risk component (VRAM fit, model quality). Validate it first in isolation before building the HTTP layer around it. TTS is second because it's the second step in the pipeline. API layer is last because it's the thinnest layer.

## Anti-Patterns

### Anti-Pattern 1: Loading Models Per Request

**What people do:** `model = AutoModelForCausalLM.from_pretrained(...)` inside the route handler.

**Why it's wrong:** GPU model loading takes 5–30 seconds. VRAM is allocated and freed on every request, eventually causing OOM or instability. First-request latency is catastrophically high.

**Do this instead:** Load in `lifespan` at startup; pass via `request.app.state`.

### Anti-Pattern 2: Storing Raw Image Files on Disk

**What people do:** `shutil.copy(upload.file, "/tmp/image.jpg")` then load from disk.

**Why it's wrong:** Unnecessary I/O for a stateless pipeline. Adds latency. Temp files accumulate if cleanup fails.

**Do this instead:** Read upload bytes into memory (`await file.read()`), wrap in `io.BytesIO`, pass to PIL directly.

### Anti-Pattern 3: Returning Audio as Separate Request

**What people do:** First request returns text + audio URL; cane makes second GET request to fetch audio file.

**Why it's wrong:** Doubles round-trip time. Requires temp file storage and cleanup logic. Adds complexity for no benefit in a single-endpoint hackathon API.

**Do this instead:** Return base64-encoded WAV inline in the same JSON response, or return `audio/wav` binary directly. The cane can decode once.

### Anti-Pattern 4: Running Piper on GPU When Moondream Is Active

**What people do:** Enable `use_cuda=True` in Piper TTS service to maximize speed.

**Why it's wrong:** On a 4GB card with Moondream already consuming 2–4GB, adding Piper's GPU allocation risks OOM. Piper on CPU via ONNX is fast enough (~200–400ms for short navigation phrases) and uses 0 VRAM.

**Do this instead:** Let Piper run on CPU. Reserve GPU entirely for the vision model.

### Anti-Pattern 5: Elaborate Async Concurrency

**What people do:** `asyncio.gather(vision_task, tts_task)` to parallelize steps.

**Why it's wrong:** TTS depends on vision output — parallelization is impossible here. Attempting it with background tasks or message queues adds unnecessary complexity for a hackathon scope where one request at a time is the expected load.

**Do this instead:** Sequential `await` calls. FastAPI handles concurrency at the HTTP layer; single requests run to completion before the next begins.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| OpenAI GPT-4o | Async HTTP via `openai` Python SDK; base64 image in message content | Requires `OPENAI_API_KEY` env var; network dependency; only hit on fallback |
| Piper voice models | Downloaded once to local disk (`~/.local/share/piper/`); loaded as ONNX file | First run auto-downloads ~50MB model; subsequent runs load from disk |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| API Layer ↔ Vision Service | Direct function call; passes `PIL.Image`, returns `str` | No serialization needed; same process |
| API Layer ↔ TTS Service | Direct function call; passes `str`, returns `bytes` | No serialization needed; same process |
| Route handler ↔ App State | `request.app.state.vision_model`, `request.app.state.tts_voice` | FastAPI's built-in app state; type-safe with dataclass |
| Vision Service ↔ GPU | PyTorch CUDA tensors; `device_map={"": "cuda"}` at load time | Model weights stay on GPU for lifetime of process |

## Scaling Considerations

This is a hackathon demo designed for single-user, single-request-at-a-time load. Scale considerations are noted for awareness only.

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 user (demo) | Single Uvicorn worker, models in app state. Current design. |
| 5–10 concurrent users | Add Redis queue + Celery worker; one GPU worker process processes requests serially; multiple API processes enqueue. |
| 100+ users | Multiple GPU workers (requires multiple GPUs or API-only with cloud VLM); CDN for audio responses. |

### First Bottleneck

GPU inference is single-threaded by model design. Two simultaneous requests compete for the same GPU. At demo scale, this is irrelevant — one user, one button press at a time.

## Sources

- [Moondream2 — Hugging Face model card](https://huggingface.co/vikhyatk/moondream2) — model loading API, query method signature, revision pinning
- [Moondream2 VRAM requirements by quantization](https://localai.computer/models/vikhyatk-moondream2) — Q4=1GB, Q8=2GB, FP16=4GB
- [Piper TTS Python interface — DeepWiki](https://deepwiki.com/rhasspy/piper/5-python-interface) — PiperVoice class, synthesis pipeline, ONNX runtime
- [Piper TTS — GitHub rhasspy/piper](https://github.com/rhasspy/piper) — GPU support, WAV output format
- [FastAPI Lifespan Events — official docs](https://fastapi.tiangolo.com/advanced/events/) — lifespan context manager pattern
- [FastAPI Model Serving — singleton patterns](https://medium.com/@hieutrantrung.it/using-fastapi-like-a-pro-with-singleton-and-dependency-injection-patterns-28de0a833a52) — app.state for shared models
- [Moondream Docker + FastAPI example](https://github.com/webnizam/moondream-docker) — reference implementation
- [Piper on Pipecat — integration docs](https://docs.pipecat.ai/server/services/tts/piper) — use_cuda option, GPU support details
- [OpenAI Vision API — official guide](https://platform.openai.com/docs/guides/vision) — base64 image format for fallback

---
*Architecture research for: assistive vision API (image → navigation text → TTS audio)*
*Researched: 2026-03-21*
