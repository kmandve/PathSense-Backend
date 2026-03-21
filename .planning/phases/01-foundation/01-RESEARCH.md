# Phase 1: Foundation - Research

**Researched:** 2026-03-21
**Domain:** Local vision model inference (Moondream2 4-bit on GTX 1650) + FastAPI service skeleton
**Confidence:** HIGH (stack and pitfalls verified against PyPI, official HuggingFace docs, and prior project research)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Tone is calm guidance — informative but not alarming. Example: "There's a step down nearby, clear on the left." NOT urgent commands like "Stop. Step down."
- **D-02:** When multiple objects are present, always lead with the nearest hazard first. Closest danger gets mentioned before anything further away.
- **D-03:** Distance uses relative words only: "close", "nearby", "far ahead". No numeric estimates (no "2 meters") — avoids false precision from a vision model that can't measure distance.
- **D-04:** When the path is clear, still describe the scene with spatial context: "Open hallway, clear path ahead" or "Wide sidewalk, no obstacles nearby." Don't just say "Clear."
- **D-05:** Output must be 1-2 short sentences, under 15 words total. Prioritize: obstacles, doors, steps, signs, people.
- **D-06:** End descriptions with directional framing when relevant: "clear on the left", "obstacle on the right."

### Claude's Discretion

- Project scaffold and dependency pinning (versions from research STACK.md)
- FastAPI lifespan handler and model loading pattern
- `run_in_executor` wiring for non-blocking inference
- `torch.cuda.empty_cache()` placement for VRAM management
- Health check endpoint implementation
- Image resize dimensions and preprocessing

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope. TTS, audio output, and GPT-4o fallback are later phases.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INF-01 | FastAPI server with single uvicorn worker (VRAM constraint) | ARCHITECTURE.md Pattern 1 (lifespan singleton) + PITFALLS.md Anti-pattern 1; `--workers 1` is mandatory |
| INF-02 | Models load once at startup via lifespan handler, not per-request | ARCHITECTURE.md lifespan code example; PITFALLS.md confirms per-request loading causes 10-50x slowdown + VRAM churn |
| INF-03 | CUDA acceleration enabled for vision model inference | STACK.md: PyTorch 2.10.0+cu126 with `device_map={"": "cuda"}`; GTX 1650 (sm_75) fully supported |
| INF-04 | Health check endpoint confirms model is loaded and GPU is available | Claude's discretion; implement as `GET /health` returning model load status + torch.cuda.is_available() |
| IMG-01 | API accepts image upload via HTTP POST (multipart/form-data) | STACK.md: FastAPI `UploadFile` + python-multipart 0.0.22; ARCHITECTURE.md Pattern 2 shows the route shape |
| IMG-02 | API validates uploaded file is a supported image format (JPEG, PNG) | PITFALLS.md gotcha: read UploadFile bytes once only; validate content-type header + PIL open to confirm |
| IMG-03 | API resizes image to model's expected input dimensions before inference | PITFALLS.md performance trap: full-res images add 200-500ms; resize to 384px max before inference |
| VIS-01 | Moondream2 4-bit quantized model loads on GTX 1650 within 4GB VRAM budget | STACK.md: `moondream/moondream-2b-2025-04-14-4bit` uses ~2.5GB VRAM; leaves ~1.2GB headroom |
| VIS-02 | Model analyzes image and produces navigation-focused text description | ARCHITECTURE.md: `model.query(image, NAVIGATION_PROMPT)["answer"]`; run via `run_in_executor` |
| VIS-03 | Descriptions identify obstacles, doors, steps, signs, and people | Achieved by navigation-optimized prompt (VIS-07); these are the five hazard categories to enumerate |
| VIS-04 | Descriptions include distance/proximity language ("2 meters ahead", "on your left") | D-03 locks this to relative words only ("close", "nearby", "far ahead") — no numeric estimates |
| VIS-05 | Descriptions end with actionable directional framing ("clear left, obstacle right") | D-06 locked; prompt must instruct model to close with directional framing |
| VIS-06 | Output is constrained to 1-2 short sentences (under 15 words target) | Set `max_new_tokens=60` in model.query(); validate output length post-inference |
| VIS-07 | Navigation-optimized system prompt drives description quality | D-01 through D-06 all feed into prompt design; final prompt is Phase 1's core deliverable |
</phase_requirements>

---

## Summary

Phase 1 establishes the entire working spine of PathSense: a FastAPI server that loads Moondream2 4-bit once at startup onto the GTX 1650, accepts image uploads, runs CUDA inference via a navigation-optimized prompt, and returns a short text description. No TTS, no fallback — just the local vision path working reliably.

The highest-risk element is VRAM. The GTX 1650 has 4GB, and full-precision Moondream2 (BF16) requires 4.2GB — it overflows. The 4-bit checkpoint (`moondream/moondream-2b-2025-04-14-4bit`) drops usage to ~2.5GB, leaving safe headroom for CUDA overhead and activation buffers. This is a hard requirement, not an optimization.

The second critical concern is event loop blocking. PyTorch inference is synchronous CPU/GPU-bound work. Running it directly inside an `async def` handler blocks the entire uvicorn event loop. The fix — `loop.run_in_executor(executor, ...)` with a single-worker `ThreadPoolExecutor` — must be wired in from the start. It is expensive to retrofit.

The navigation prompt is the third deliverable of equivalent importance to the model loading code. All six tone/format decisions (D-01 through D-06) translate into a single prompt constant. Getting it right is essential to meeting VIS-03, VIS-04, VIS-05, and VIS-06.

**Primary recommendation:** Build in order — scaffold and deps first, then model loading verification (VRAM confirmed), then prompt engineering, then the full HTTP endpoint with image handling. Validate each layer independently before stacking the next.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.11 | Runtime | Sweet spot: faster than 3.10, full ML ecosystem support; transformers 5.x requires >=3.10 |
| FastAPI | 0.135.1 | HTTP API framework | Native async, UploadFile for multipart, lifespan context manager, auto-docs |
| Uvicorn | 0.42.0 | ASGI server | Only production ASGI server for FastAPI; `--workers 1` is critical for single-GPU |
| PyTorch | 2.10.0 + CUDA 12.6 | GPU inference backend | GTX 1650 (Turing sm_75) fully supported by CUDA 12.6 builds |
| HuggingFace Transformers | 5.3.0 | Moondream2 model loading | `AutoModelForCausalLM.from_pretrained()` with `device_map={"": "cuda"}` is the canonical local path |
| Pillow | 12.1.1 | Image decoding + resize | `Image.open(io.BytesIO(data))` + `image.resize()` before model input |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-multipart | 0.0.22 | Multipart form parsing | Always — FastAPI silently fails on file uploads without this |
| python-dotenv | latest | Env var management | Always — prevents hardcoded credentials, needed for Phase 4 OPENAI_API_KEY |
| io (stdlib) | — | BytesIO wrapper | Always — wraps upload bytes for PIL without temp files |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| moondream/moondream-2b-2025-04-14-4bit | vikhyatk/moondream2 (BF16) | BF16 = 4.2GB VRAM — overflows GTX 1650 on first inference |
| moondream/moondream-2b-2025-04-14-4bit | Moondream 0.5B | Quality degrades noticeably on complex indoor/outdoor navigation scenes |
| onnxruntime (CPU) | onnxruntime-gpu | GPU variant wastes VRAM the vision model needs; CPU is fast enough for short phrases |

**Installation:**

```bash
# Python 3.11 venv
python3.11 -m venv .venv && source .venv/bin/activate

# PyTorch with CUDA 12.6 (GTX 1650 sm_75 compatible)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126

# Core API
pip install fastapi==0.135.1 uvicorn[standard]==0.42.0 python-multipart==0.0.22

# Vision model stack
pip install "transformers[torch]==5.3.0" Pillow==12.1.1

# Utilities
pip install python-dotenv
```

**Model checkpoint (no pip install):** Loaded via transformers from HuggingFace on first run:
- 4-bit checkpoint: `moondream/moondream-2b-2025-04-14-4bit` (~2.5GB VRAM)
- Tokenizer from: `vikhyatk/moondream2` revision `2025-06-21`

---

## Architecture Patterns

### Recommended Project Structure

```
pathsense/
├── main.py                 # FastAPI app creation, lifespan, route mounting
├── routes/
│   └── analyze.py          # POST /analyze endpoint + GET /health
├── services/
│   └── vision.py           # Moondream inference, image preprocessing, prompt constant
├── models/
│   └── state.py            # AppState dataclass (vision_model, tokenizer)
├── config.py               # Settings (model path, max tokens, image resize dim)
└── requirements.txt
```

Note: TTS service (`services/tts.py`) is Phase 2. The `state.py` dataclass should be defined now and extended in Phase 2 to add `tts_voice`.

### Pattern 1: Lifespan Singleton for Model Loading (INF-02)

**What:** Load Moondream2 once at application startup via FastAPI's `lifespan` context manager; hold reference in `app.state`.

**When to use:** Always. Loading per-request takes 5-30 seconds and causes VRAM churn that eventually causes OOM.

**Example:**
```python
# Source: FastAPI official docs + ARCHITECTURE.md
from contextlib import asynccontextmanager
from fastapi import FastAPI
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.vision_model = AutoModelForCausalLM.from_pretrained(
        "moondream/moondream-2b-2025-04-14-4bit",
        trust_remote_code=True,
        device_map={"": "cuda"},
    )
    app.state.tokenizer = AutoTokenizer.from_pretrained(
        "vikhyatk/moondream2",
        revision="2025-06-21",
        trust_remote_code=True,
    )
    yield
    # Shutdown
    del app.state.vision_model
    torch.cuda.empty_cache()

app = FastAPI(lifespan=lifespan)
```

### Pattern 2: run_in_executor for Non-Blocking Inference (INF-03, VIS-02)

**What:** Wrap synchronous PyTorch inference in a `ThreadPoolExecutor` so the asyncio event loop is never blocked.

**When to use:** Always, for any CPU/GPU-bound blocking call inside an async handler.

**Example:**
```python
# Source: ARCHITECTURE.md + PITFALLS.md Pitfall 2
import asyncio
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=1)  # 1 worker serializes GPU access

def _run_inference(model, tokenizer, image_bytes: bytes) -> str:
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_bytes))
        img = img.resize((384, 384))  # INF: resize before inference
        answer = model.query(img, NAVIGATION_PROMPT)["answer"]
        return answer
    finally:
        torch.cuda.empty_cache()  # Prevent VRAM fragmentation (Pitfall 3)

@router.post("/analyze")
async def analyze(file: UploadFile, request: Request):
    image_bytes = await file.read()  # Read once only (Pitfall: UploadFile read twice)
    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(
        _executor, _run_inference,
        request.app.state.vision_model,
        request.app.state.tokenizer,
        image_bytes,
    )
    return {"text": text}
```

### Pattern 3: Navigation-Optimized Prompt (VIS-07)

**What:** A single, tightly constrained prompt constant encoding all six D-01 through D-06 decisions.

**When to use:** Passed to every `model.query()` call. Must never be generated dynamically.

**Example (incorporates all locked decisions):**
```python
NAVIGATION_PROMPT = (
    "In 1-2 short sentences under 15 words total, describe immediate navigation hazards "
    "directly ahead. Prioritize nearest hazard first: obstacles, steps, doors, signs, people. "
    "Use relative distance words only: 'close', 'nearby', 'far ahead'. "
    "Tone: calm guidance, not commands. "
    "If path is clear, describe the scene briefly: 'Open hallway, clear path ahead.' "
    "End with directional framing when relevant: 'clear on the left', 'obstacle on the right'."
)
```

### Pattern 4: Health Check Endpoint (INF-04)

**What:** A `GET /health` route that confirms model is loaded and CUDA is available, returning a fast 200 or 503.

**Example:**
```python
@router.get("/health")
async def health(request: Request):
    model_loaded = hasattr(request.app.state, "vision_model")
    cuda_ok = torch.cuda.is_available()
    if not model_loaded or not cuda_ok:
        raise HTTPException(status_code=503, detail="Model not ready")
    vram_used_mb = torch.cuda.memory_reserved() / 1024**2
    return {"status": "ok", "cuda": cuda_ok, "vram_reserved_mb": round(vram_used_mb, 1)}
```

### Anti-Patterns to Avoid

- **Loading model per request:** Results in 5-30s cold start, VRAM churn, and eventual OOM. Always use lifespan.
- **Calling `model.query()` directly in `async def` handler:** Blocks the event loop; health checks time out. Always use `run_in_executor`.
- **Using `vikhyatk/moondream2` (BF16) instead of 4-bit checkpoint:** BF16 = 4.2GB VRAM, overflows GTX 1650 on first inference.
- **Using `moondream` PyPI package:** That package wraps the cloud API; it requires an API key and sends images to Moondream's servers.
- **Reading UploadFile twice:** Second `.read()` returns empty bytes. Read once, store in variable.
- **Skipping `torch.cuda.empty_cache()` after inference:** VRAM fragmentation causes OOM on request 5-10, not request 1.
- **Multiple uvicorn workers:** Each worker loads Moondream into VRAM separately; 2 workers = 5GB needed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multipart file upload parsing | Custom body parser | FastAPI `UploadFile` + python-multipart | Handles chunked uploads, boundary parsing, memory management |
| Image format detection | Magic byte inspection | PIL `Image.open()` — raises on invalid data | PIL validates format headers and raises `UnidentifiedImageError` for non-images |
| CUDA memory management | Custom tensor lifecycle tracking | `torch.cuda.empty_cache()` in finally block | PyTorch's allocator handles fragmentation; empty_cache releases reserved but unallocated memory |
| Thread-safe model singleton | Global variable with locks | FastAPI `app.state` + single `lifespan` context | Lifespan guarantees load-once, app.state is process-scoped |
| GPU serialization for concurrent requests | Request queue / semaphore | `ThreadPoolExecutor(max_workers=1)` | max_workers=1 naturally serializes GPU access at the OS thread level |

**Key insight:** The GPU inference serialization problem is solved by a one-line `ThreadPoolExecutor(max_workers=1)`. Any custom queuing or semaphore solution adds complexity without benefit at single-user demo scale.

---

## Common Pitfalls

### Pitfall 1: BF16 Moondream Overflows GTX 1650 on First Inference

**What goes wrong:** The BF16 checkpoint requires 4.2GB VRAM. GTX 1650 has 4GB. The model loads successfully — the crash happens on the first inference call when activation buffers push past the physical limit.

**Why it happens:** Developers see "1.6B params" and estimate ~3GB. Missed: CUDA context init (~200MB), activation buffer spikes during forward pass.

**How to avoid:** Use `moondream/moondream-2b-2025-04-14-4bit` (2.5GB peak). Set `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512` to reduce fragmentation.

**Warning signs:** `torch.cuda.memory_reserved()` > 3.5GB before first request; `nvidia-smi` shows 99%+ VRAM at startup.

### Pitfall 2: Inference Blocks the Event Loop

**What goes wrong:** `model.query()` is a blocking C++/CUDA operation. Inside `async def`, it blocks uvicorn's event loop. Health checks and other requests queue behind it.

**Why it happens:** `async def` looks non-blocking but isn't for CPU/GPU-bound calls.

**How to avoid:** `loop.run_in_executor(_executor, _run_inference, ...)` with `ThreadPoolExecutor(max_workers=1)`.

**Warning signs:** Health check times out during active inference; Piper TTS takes 10+ seconds despite being fast.

### Pitfall 3: VRAM Fragmentation Causes OOM After N Requests

**What goes wrong:** PyTorch's caching allocator holds tensors in a reserved pool. After several requests, `memory_reserved()` = 3.8GB while `memory_allocated()` = 1.2GB. New allocation fails despite most of that memory being "free."

**Why it happens:** Intermediate tensors from inference accumulate in the reserved pool.

**How to avoid:** Call `torch.cuda.empty_cache()` in the `finally` block of every inference function. Never accumulate image tensors in lists.

**Warning signs:** `nvidia-smi` VRAM usage climbs monotonically across requests; OOM on request 5-10 but not request 1.

### Pitfall 4: UploadFile Read Twice Returns Empty Bytes

**What goes wrong:** Validation code calls `await file.read()`, then the inference code calls `await file.read()` again. Second call returns empty bytes (`b""`).

**Why it happens:** FastAPI's `UploadFile` is a stream; reading advances the cursor to EOF.

**How to avoid:** `image_bytes = await file.read()` once at route entry. Pass `image_bytes` everywhere.

**Warning signs:** PIL raises `UnidentifiedImageError` or model returns empty string on valid images.

### Pitfall 5: Verbose Non-Navigational Descriptions

**What goes wrong:** Without prompt constraints, Moondream describes the full scene — "A wooden table on the left, a potted plant in the corner, and a window..." — which takes 6+ seconds to speak and is stale by the time audio finishes.

**Why it happens:** Moondream's default output is general Q&A. The navigation use case requires a constrained, hazard-focused prompt.

**How to avoid:** Use the `NAVIGATION_PROMPT` constant (see Pattern 3). Set `max_new_tokens=60` to hard-cap output. Validate output length < 80 characters at integration time.

**Warning signs:** TTS audio file > 3MB or > 6 seconds; Moondream output regularly exceeds 100 characters.

---

## Code Examples

### Complete lifespan + startup

```python
# Source: ARCHITECTURE.md + FastAPI official lifespan docs
from contextlib import asynccontextmanager
from fastapi import FastAPI
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

MODEL_ID = "moondream/moondream-2b-2025-04-14-4bit"
TOKENIZER_ID = "vikhyatk/moondream2"
TOKENIZER_REVISION = "2025-06-21"

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.vision_model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        trust_remote_code=True,
        device_map={"": "cuda"},
    )
    app.state.tokenizer = AutoTokenizer.from_pretrained(
        TOKENIZER_ID,
        revision=TOKENIZER_REVISION,
        trust_remote_code=True,
    )
    yield
    del app.state.vision_model
    torch.cuda.empty_cache()

app = FastAPI(lifespan=lifespan)
```

### Image validation + resize

```python
# Source: PITFALLS.md integration gotchas + ARCHITECTURE.md data flow
from PIL import Image, UnidentifiedImageError
import io

SUPPORTED_CONTENT_TYPES = {"image/jpeg", "image/png"}
MAX_IMAGE_DIM = 384  # resize to this before inference

async def validate_and_decode(file: UploadFile) -> Image.Image:
    if file.content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported image type: {file.content_type}")
    image_bytes = await file.read()  # Read ONCE
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="File is not a valid image")
    img.thumbnail((MAX_IMAGE_DIM, MAX_IMAGE_DIM))  # Resize in-place, preserves aspect ratio
    return img
```

### Inference with VRAM cleanup

```python
# Source: PITFALLS.md Pitfall 2 + Pitfall 3
import torch

NAVIGATION_PROMPT = (
    "In 1-2 short sentences under 15 words total, describe immediate navigation hazards "
    "directly ahead. Prioritize nearest hazard first: obstacles, steps, doors, signs, people. "
    "Use relative distance words only: 'close', 'nearby', 'far ahead'. "
    "Tone: calm guidance, not commands. "
    "If path is clear, describe the scene: 'Open hallway, clear path ahead.' "
    "End with directional framing when relevant: 'clear on the left', 'obstacle on the right'."
)

def _run_inference(model, img: Image.Image) -> str:
    try:
        result = model.query(img, NAVIGATION_PROMPT)
        return result["answer"]
    finally:
        torch.cuda.empty_cache()
```

### VRAM verification command

```bash
# Run after startup warmup — target: < 3GB reserved
nvidia-smi --query-gpu=memory.used,memory.free,memory.total --format=csv,noheader,nounits

# Also check from Python
python -c "import torch; print(f'Reserved: {torch.cuda.memory_reserved()/1e9:.2f}GB, Allocated: {torch.cuda.memory_allocated()/1e9:.2f}GB')"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` | `lifespan` context manager | FastAPI 0.93+ (2023) | Cleaner startup/shutdown pairing; `on_event` deprecated |
| `vikhyatk/moondream2` (BF16 only) | `moondream/moondream-2b-2025-04-14-4bit` (INT4/QAT) | April 2025 | 42% VRAM reduction; 2.5GB vs 4.2GB; 0.6% accuracy drop |
| `moondream` PyPI package | `transformers` with HuggingFace model ID | Early 2025 | PyPI package now wraps cloud API; local GPU requires transformers path |

**Deprecated/outdated:**
- `@app.on_event("startup")`: Replaced by `lifespan` context manager; still works but flagged as deprecated in FastAPI docs.
- `vikhyatk/moondream2` BF16 for 4GB VRAM hardware: Cannot fit; use 4-bit checkpoint.

---

## Open Questions

1. **Confirm 4-bit checkpoint revision string**
   - What we know: `moondream/moondream-2b-2025-04-14-4bit` is the HuggingFace repo ID; the checkpoint was released April 2025
   - What's unclear: Whether `trust_remote_code=True` requires a specific revision pin for reproducibility, or whether `main` is stable
   - Recommendation: During Phase 1 Wave 0, run `from_pretrained` without revision pin first; if behavior is inconsistent, pin the commit SHA shown in HuggingFace model card

2. **Actual inference latency on GTX 1650**
   - What we know: Research estimates 1-2 seconds for Moondream2 4-bit on GTX 1650
   - What's unclear: Actual measured latency with 384x384 images and a ~60-token output constraint
   - Recommendation: Measure empirically in the model loading verification step; if > 2s, reduce image to 256x256

3. **Moondream `model.query()` signature for 4-bit checkpoint**
   - What we know: `vikhyatk/moondream2` uses `model.query(image, prompt)["answer"]`; the 4-bit checkpoint uses `trust_remote_code=True`
   - What's unclear: Whether the 4-bit checkpoint's `query()` interface is identical to the BF16 checkpoint
   - Recommendation: In Wave 0, run a standalone smoke test (`python -c "model.query(test_image, 'hello')"`) before building the API layer on top

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (latest) + httpx (async client) |
| Config file | None — Wave 0 creates `pytest.ini` |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INF-01 | Server starts with 1 uvicorn worker | smoke | `pytest tests/test_startup.py::test_single_worker -x` | Wave 0 |
| INF-02 | Model loaded in app.state after startup | unit | `pytest tests/test_startup.py::test_model_in_app_state -x` | Wave 0 |
| INF-03 | CUDA device is active after model load | unit | `pytest tests/test_startup.py::test_cuda_available -x` | Wave 0 |
| INF-04 | GET /health returns 200 with model_loaded=true | integration | `pytest tests/test_health.py::test_health_ok -x` | Wave 0 |
| IMG-01 | POST /analyze with valid JPEG returns 200 | integration | `pytest tests/test_analyze.py::test_upload_jpeg -x` | Wave 0 |
| IMG-02 | POST /analyze with non-image returns 415 | integration | `pytest tests/test_analyze.py::test_invalid_content_type -x` | Wave 0 |
| IMG-03 | Image is resized to <=384px before inference | unit | `pytest tests/test_vision.py::test_image_resize -x` | Wave 0 |
| VIS-01 | VRAM reserved < 3GB after model load and warmup | smoke | `pytest tests/test_startup.py::test_vram_under_budget -x` | Wave 0 |
| VIS-02 | model.query() returns a non-empty string | unit | `pytest tests/test_vision.py::test_inference_returns_text -x` | Wave 0 |
| VIS-03 | Description mentions at least one: obstacle/door/step/sign/person | integration | `pytest tests/test_analyze.py::test_description_mentions_hazard -x` | Wave 0 |
| VIS-04 | Description contains relative distance words (no numeric meters) | unit | `pytest tests/test_vision.py::test_no_numeric_distances -x` | Wave 0 |
| VIS-05 | Description ends with directional framing word | unit | `pytest tests/test_vision.py::test_directional_framing -x` | Wave 0 |
| VIS-06 | Output is under 15 words | unit | `pytest tests/test_vision.py::test_output_length -x` | Wave 0 |
| VIS-07 | Prompt constant encodes all D-01 to D-06 requirements | unit | `pytest tests/test_vision.py::test_prompt_content -x` | Wave 0 |

**VRAM soak test (success criterion 5):**
```bash
pytest tests/test_soak.py::test_20_sequential_inferences_no_oom -x --timeout=120
```

### Sampling Rate

- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/__init__.py` — package marker
- [ ] `pytest.ini` — rootdir config, asyncio mode
- [ ] `tests/conftest.py` — shared `async_client` fixture using `httpx.AsyncClient` + `ASGITransport`
- [ ] `tests/test_startup.py` — covers INF-01, INF-02, INF-03, VIS-01
- [ ] `tests/test_health.py` — covers INF-04
- [ ] `tests/test_analyze.py` — covers IMG-01, IMG-02, VIS-03
- [ ] `tests/test_vision.py` — covers IMG-03, VIS-02, VIS-04, VIS-05, VIS-06, VIS-07
- [ ] `tests/test_soak.py` — covers success criterion 5 (20 sequential inferences, no OOM)
- [ ] `tests/fixtures/test_image.jpg` — a small JPEG for use in integration tests

**Framework install (if not present):**
```bash
pip install pytest pytest-asyncio httpx
```

---

## Sources

### Primary (HIGH confidence)
- `.planning/research/STACK.md` — full stack with verified PyPI versions (FastAPI 0.135.1, uvicorn 0.42.0, transformers 5.3.0, Pillow 12.1.1, PyTorch 2.10.0+cu126, piper-tts 1.4.1)
- `.planning/research/ARCHITECTURE.md` — lifespan pattern, run_in_executor pattern, project structure, VRAM budget breakdown
- `.planning/research/PITFALLS.md` — all six critical pitfalls with code examples
- [FastAPI official lifespan docs](https://fastapi.tiangolo.com/advanced/events/) — lifespan context manager API
- [moondream/moondream-2b-2025-04-14-4bit HuggingFace](https://huggingface.co/moondream/moondream-2b-2025-04-14-4bit) — 4-bit checkpoint, ~2.5GB VRAM
- [PyTorch official installer](https://pytorch.org/get-started/locally/) — CUDA 12.6 install command for sm_75

### Secondary (MEDIUM confidence)
- [Moondream QAT blog](https://moondream.ai/blog/smaller-faster-moondream-with-qat) — confirmed 42% VRAM reduction vs full precision
- [vikhyatk/moondream2 HuggingFace](https://huggingface.co/vikhyatk/moondream2) — tokenizer revision `2025-06-21`, query API shape

### Tertiary (LOW confidence — flag for validation)
- Inference latency estimate of 1-2s on GTX 1650: from STACK.md research notes; must be measured empirically
- `model.query()` interface identical between BF16 and 4-bit checkpoints: assumed from trust_remote_code=True loading; validate in Wave 0

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified against PyPI and official docs in prior research
- Architecture: HIGH — lifespan, run_in_executor, and sequential pipeline patterns verified against FastAPI docs and ARCHITECTURE.md
- Pitfalls: HIGH (VRAM, event loop); MEDIUM (prompt quality) — VRAM and blocking pitfalls verified with PyTorch memory docs and community reports

**Research date:** 2026-03-21
**Valid until:** 2026-04-20 (stable ML stack; Moondream checkpoint revision dates are the most likely drift point)
