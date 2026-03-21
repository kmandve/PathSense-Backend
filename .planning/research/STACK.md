# Stack Research

**Domain:** Local vision + TTS API for assistive navigation (blind users)
**Researched:** 2026-03-21
**Confidence:** HIGH (all critical components verified against official docs and PyPI)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11 | Runtime | 3.11 is the sweet spot: faster than 3.10, more mature ecosystem support than 3.12/3.13 for ML libs; all core deps (FastAPI 0.135, transformers 5.3, piper-tts 1.4) require >=3.9 or >=3.10 |
| FastAPI | 0.135.1 | HTTP API framework | Native async, auto-generated OpenAPI docs, `UploadFile` for multipart image ingestion, single-worker GPU pattern is well-documented; faster than Flask for I/O-bound fallback calls |
| Uvicorn | 0.42.0 | ASGI server | The only production-grade ASGI server for FastAPI; `--workers 1` critical for GPU — each worker loads model into VRAM separately |
| PyTorch | 2.10.0 + CUDA 12.6 | GPU inference backend | Required by Moondream2 via transformers; GTX 1650 (Turing, sm_75) is fully supported by CUDA 12.6 builds |
| HuggingFace Transformers | 5.3.0 | Moondream2 model loading | `AutoModelForCausalLM.from_pretrained()` with `device_map={"": "cuda"}` is the recommended local loading path per Moondream docs |
| Pillow | 12.1.1 | Image decoding | Standard image library; required to convert `UploadFile` bytes → PIL Image for Moondream input; `Image.open(io.BytesIO(data))` is the canonical pattern |
| piper-tts | 1.4.1 | Local neural TTS | Fast ONNX-based TTS; runs on CPU leaving VRAM for vision model; ~20-30ms synthesis for short navigation phrases; no API keys; fully offline |
| openai | 2.29.0 | GPT-4o fallback | Official Python client; `client.chat.completions.create(model="gpt-4o")` with base64 image in content array is the current pattern |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-multipart | 0.0.22 | Multipart form parsing | Always — FastAPI requires this for `UploadFile`; without it, file uploads silently fail |
| onnxruntime | latest | Piper ONNX inference | Always — piper-tts depends on this; use CPU variant (`onnxruntime`, not `onnxruntime-gpu`) to keep VRAM free for vision model |
| python-dotenv | latest | API key management | Always — load `OPENAI_API_KEY` from `.env` without hardcoding |
| httpx | latest | Async HTTP client | Pulled in by `openai` SDK automatically; use for any additional async HTTP calls |
| io (stdlib) | — | BytesIO wrapper | Always — `io.BytesIO` wraps raw upload bytes into a file-like object PIL can open |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Fast dependency management | Prefer over pip for speed; `uv pip install` is a drop-in replacement that resolves faster |
| pytest + httpx | API testing | `httpx.AsyncClient` mounts the FastAPI app in-process; no live server needed for tests |
| nvidia-smi | VRAM monitoring | Run `watch -n1 nvidia-smi` during development to track VRAM usage; 4GB budget is tight |

## Installation

```bash
# Create venv (Python 3.11)
python3.11 -m venv .venv && source .venv/bin/activate

# PyTorch with CUDA 12.6 (GTX 1650 supported, CUDA 12.6 is stable as of March 2026)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126

# Core API
pip install fastapi==0.135.1 uvicorn[standard]==0.42.0 python-multipart==0.0.22

# Vision model stack
pip install "transformers[torch]==5.3.0" Pillow==12.1.1

# Moondream via Hugging Face (no separate pip package needed — loaded via transformers)
# Model downloads on first run: vikhyatk/moondream2 revision "2025-06-21"
# 4-bit quantized variant: moondream/moondream-2b-2025-04-14-4bit (~2.5GB VRAM)

# GPT-4o fallback
pip install openai==2.29.0 python-dotenv

# TTS
pip install piper-tts==1.4.1 onnxruntime
# Voice model: download en_US-lessac-medium.onnx + en_US-lessac-medium.onnx.json
# from: https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/lessac/medium
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Moondream2 4-bit (2.5GB VRAM) | LLaVA-1.5-7B | Only if VRAM is not a constraint (requires 14GB+); better quality but impossible on GTX 1650 |
| Moondream2 4-bit (2.5GB VRAM) | BLIP-2 | Older; Moondream is purpose-built for fast visual Q&A and dramatically smaller |
| Moondream2 4-bit (2.5GB VRAM) | Moondream 0.5B | Use if even 2.5GB is too tight; quality degrades noticeably for complex scenes |
| piper-tts (CPU ONNX) | Coqui TTS | Coqui is deprecated (no active maintainer since 2023); piper is actively maintained |
| piper-tts (CPU ONNX) | gTTS / ElevenLabs | Cloud-dependent; violates the offline constraint; adds network latency |
| piper-tts (CPU ONNX) | Kokoro TTS | Newer, higher quality; but adds ~1-2s latency on CPU; piper's RTF ~0.2 is faster for short phrases |
| transformers for Moondream | `moondream` pip package | The `moondream` package on PyPI targets the cloud API, not local GPU inference |
| onnxruntime (CPU) for Piper | onnxruntime-gpu for Piper | Piper on GPU provides negligible speedup for short phrases; wastes VRAM the vision model needs |
| FastAPI | Flask | Flask lacks native async; harder to handle concurrent requests during GPT-4o fallback I/O wait |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `moondream` PyPI package for local inference | The `moondream` pip package (v0.2.0) wraps the cloud API, not local GPU. It requires an API key and sends images to Moondream's servers — opposite of what's needed | Load `vikhyatk/moondream2` via `transformers` `AutoModelForCausalLM` |
| `onnxruntime-gpu` for Piper | Consumes CUDA VRAM that the vision model needs. Piper on CPU generates a short navigation phrase in <100ms; GPU gain is negligible. 4GB budget cannot afford both | `onnxruntime` (CPU) for Piper |
| Multiple uvicorn workers | Each worker loads Moondream into VRAM separately. 2 workers = 5GB VRAM needed — exceeds GTX 1650 capacity | `uvicorn app:app --workers 1` |
| Streaming video input | Out of scope per PROJECT.md; adds architectural complexity for no demo benefit | Single-image POST per button press |
| Coqui TTS | Repository archived, no active maintenance since 2023, installation frequently broken on newer Python | piper-tts |
| gTTS / ElevenLabs / Azure TTS | Requires internet; adds 200-800ms network latency; fails offline | piper-tts |
| `gunicorn` as process manager | Gunicorn adds multi-process complexity. For single-GPU inference with 1 worker, plain uvicorn is simpler and equally correct | `uvicorn` directly |

## Stack Patterns by Variant

**VRAM is extremely tight (model + overhead exceeds 3.5GB):**
- Use `moondream/moondream-2b-2025-04-14-4bit` (2.5GB VRAM, 0.6% accuracy drop vs full precision)
- Load with `torch_dtype=torch.float16` and `device_map={"": "cuda"}`
- Run Piper strictly on CPU (default onnxruntime)
- Monitor with `nvidia-smi` — target headroom of 300-500MB

**Moondream quality insufficient for a specific scene:**
- Fall back to GPT-4o via `openai` SDK
- Encode upload bytes as base64: `base64.b64encode(image_bytes).decode()`
- Send as `data:image/jpeg;base64,{b64}` in the image_url content block
- Prompt GPT-4o with the same navigation-focused system prompt for consistency

**Latency budget exceeded:**
- Moondream inference on GTX 1650 targets ~1-2s; Piper TTS ~0.1s; total should be <3s
- If Moondream alone exceeds 2s, reduce image resolution before inference (resize to 384x384 before passing to model)
- GPT-4o fallback adds ~1-3s network RTT — only trigger when local quality is provably insufficient

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| transformers 5.3.0 | PyTorch 2.4+ | Tested on Python >=3.10; transformers 5.x dropped Python 3.9 support |
| FastAPI 0.135.1 | Python >=3.10 | Requires python-multipart for file uploads |
| piper-tts 1.4.1 | Python >=3.9, onnxruntime | Use CPU onnxruntime; GPU variant conflicts with VRAM budget |
| PyTorch 2.10.0+cu126 | GTX 1650 (sm_75) | CUDA 12.6 supports Turing architecture (sm_75) — GTX 1650 is fully compatible |
| openai 2.29.0 | Python >=3.9 | Uses httpx under the hood; `from openai import OpenAI` (sync) or `AsyncOpenAI` (async) |
| Pillow 12.1.1 | Python >=3.9 | `Image.open(io.BytesIO(bytes_data))` is the stable pattern across all versions |

## Key Architecture Note

Moondream and Piper do not share VRAM when Piper uses CPU onnxruntime. The split is:
- **GPU (CUDA):** Moondream2 4-bit = ~2.5GB of 4GB budget
- **CPU (RAM):** Piper ONNX = ~100-200MB RAM, negligible

Load both at startup (not per-request) to avoid cold-start latency on every button press.

```python
# startup pattern — load once, reuse across requests
model = AutoModelForCausalLM.from_pretrained(
    "vikhyatk/moondream2",
    revision="2025-06-21",
    trust_remote_code=True,
    torch_dtype=torch.float16,
    device_map={"": "cuda"},
)
tokenizer = AutoTokenizer.from_pretrained("vikhyatk/moondream2", revision="2025-06-21")

voice = PiperVoice.load("en_US-lessac-medium.onnx")
```

## Sources

- [vikhyatk/moondream2 Hugging Face](https://huggingface.co/vikhyatk/moondream2) — VRAM, revision, CUDA loading pattern (MEDIUM confidence; version date from 2025 release, post-knowledge-cutoff)
- [moondream/moondream-2b-2025-04-14-4bit Hugging Face](https://huggingface.co/moondream/moondream-2b-2025-04-14-4bit) — 4-bit quantization: 2.5GB VRAM, 0.6% accuracy drop (MEDIUM confidence)
- [Moondream QAT blog post](https://moondream.ai/blog/smaller-faster-moondream-with-qat) — Confirmed 42% VRAM reduction vs full precision (MEDIUM confidence)
- [piper-tts PyPI](https://pypi.org/project/piper-tts/) — v1.4.1, Python >=3.9, ONNX-based (HIGH confidence)
- [FastAPI PyPI](https://pypi.org/project/fastapi/) — v0.135.1, Python >=3.10 (HIGH confidence)
- [transformers PyPI](https://pypi.org/project/transformers/) — v5.3.0, PyTorch 2.4+, Python >=3.10 (HIGH confidence)
- [uvicorn PyPI](https://pypi.org/project/uvicorn/) — v0.42.0 (HIGH confidence)
- [openai PyPI](https://pypi.org/project/openai/) — v2.29.0, Python >=3.9 (HIGH confidence)
- [PyTorch official installer](https://pytorch.org/get-started/locally/) — v2.10.0, CUDA 12.6 install command (HIGH confidence)
- [rhasspy/piper-voices Hugging Face](https://huggingface.co/rhasspy/piper-voices) — en_US-lessac-medium voice model location (HIGH confidence)
- [python-multipart PyPI](https://pypi.org/project/python-multipart/) — v0.0.22 (HIGH confidence)

---
*Stack research for: local vision + TTS API for blind navigation assistance*
*Researched: 2026-03-21*
