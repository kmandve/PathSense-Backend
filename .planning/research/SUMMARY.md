# Project Research Summary

**Project:** PathSense
**Domain:** Assistive vision API — local image-to-audio navigation pipeline for blind users (smart cane backend)
**Researched:** 2026-03-21
**Confidence:** HIGH

## Executive Summary

PathSense is a single-endpoint HTTP API that accepts a camera image from a smart cane device, runs local vision inference to produce a navigation-focused scene description, converts that description to audio via local TTS, and returns both text and audio in one response. Experts in this domain (Seeing AI, Be My Eyes, published smart cane research) consistently follow a trigger-based capture model (one image per button press) rather than continuous video streaming, keeping the architecture tractable and latency predictable. The key technical insight is that the entire pipeline — vision inference and TTS — can run fully offline on consumer hardware, which is both a technical constraint and a compelling differentiator.

The recommended approach is: FastAPI (single worker, lifespan startup) loading Moondream2 4-bit quantized (~2.5GB VRAM) on CUDA and Piper TTS on CPU via ONNX, with a GPT-4o fallback gated by a timeout and quality check. This combination keeps the total end-to-end latency under 3 seconds on a GTX 1650 and avoids every cloud dependency on the primary inference path. Prompt engineering is as critical as the model choice — a navigation-specific prompt capping output at 15 words is required to keep audio duration under 4 seconds and descriptions actionable while the user is moving.

The dominant risk is VRAM exhaustion on the GTX 1650 (4GB). Full-precision Moondream2 (BF16) requires 4.2GB and will OOM during the first inference despite loading successfully. The 4-bit quantized checkpoint is non-negotiable. A close second risk is blocking the FastAPI event loop with synchronous GPU inference inside an async handler, which causes all requests including health checks to queue. Both pitfalls must be addressed in Phase 1 before any other component is built on top of them.

## Key Findings

### Recommended Stack

The stack is purpose-built for VRAM-constrained local inference. Python 3.11 is the runtime sweet spot: all key ML libraries support it and it is more stable than 3.12/3.13 for this ecosystem. FastAPI 0.135 + Uvicorn 0.42 provide the HTTP layer with `--workers 1` mandatory (each additional worker loads Moondream into VRAM separately). The vision model is loaded via HuggingFace Transformers 5.3 — the `moondream` PyPI package must be avoided as it wraps the cloud API, not local GPU inference.

**Core technologies:**
- **Python 3.11**: Runtime — ecosystem compatibility sweet spot for all ML dependencies
- **FastAPI 0.135 + Uvicorn 0.42**: HTTP layer — native async, `UploadFile` multipart ingestion, single-worker GPU pattern; `--workers 1` is mandatory
- **PyTorch 2.10 + CUDA 12.6**: GPU backend — GTX 1650 (sm_75/Turing) is fully supported by CUDA 12.6
- **HuggingFace Transformers 5.3**: Model loading — `AutoModelForCausalLM.from_pretrained("moondream/moondream-2b-2025-04-14-4bit")` with `device_map={"": "cuda"}` is the correct local inference pattern
- **piper-tts 1.4.1 + onnxruntime (CPU)**: Local TTS — ~20-30ms synthesis for short navigation phrases; runs on CPU, leaving all VRAM for the vision model; fully offline; Coqui is deprecated, gTTS/ElevenLabs require internet
- **openai 2.29.0**: GPT-4o fallback — base64 image encoding; must include `asyncio.wait_for(..., timeout=5.0)` wrapper
- **Pillow 12.1.1**: Image decoding — `Image.open(io.BytesIO(data))` canonical pattern; no temp files needed
- **python-multipart 0.0.22**: Required for FastAPI `UploadFile`; without it, file uploads silently fail

### Expected Features

The MVP is tightly scoped. Every feature deferred from v1 is deferred for a concrete reason — scope creep on any of them risks the demo.

**Must have (table stakes):**
- HTTP POST endpoint accepting image file — the integration surface for cane hardware
- Navigation-focused scene description (not generic captioning) — the product's core claim; requires prompt engineering, not just the model
- Obstacle classification (steps, doors, signs, people) — explicit categories in the prompt
- TTS audio output returned in the response — audio is the only usable output channel for a blind user
- Dual response: `{"description": "...", "audio_base64": "..."}` — judges inspect the payload; hardware needs both
- Sub-3-second end-to-end latency — anything slower breaks the "real-time navigation" framing
- GPT-4o fallback — demo resilience against local model failure or poor output quality

**Should have (competitive differentiators):**
- Fully local inference emphasized in the demo narrative — "runs on hardware a blind user can afford" is a winning frame
- Distance/proximity language in output: "2 meters ahead," "on your left" — separates navigation assistance from generic scene captioning
- Actionable framing: end descriptions with a directional nudge — prompt engineering only, no extra model cost
- Navigation-optimized prompt: constrained to 15 words max, specific hazard categories

**Defer (v2+):**
- Continuous video stream / WebSocket processing — requires frame diffing, VRAM budget exceeds GTX 1650 capacity
- User accounts, session history, GPS/landmark integration — out of scope for hackathon
- Multi-language TTS — English Piper voices work; add after English is validated
- Fine-tuned navigation VLM — needs labeled dataset collection first; prompt engineering achieves 80% of the benefit

### Architecture Approach

The architecture is a linear, stateless pipeline: one HTTP POST triggers image decode → GPU vision inference → CPU TTS synthesis → JSON response with text + base64 audio. All state is held in `app.state` loaded once at startup via FastAPI's `lifespan` context manager. There is no database, no session, no background queue. Single Uvicorn worker serializes GPU access naturally. The only external dependency is GPT-4o (fallback only, gated by timeout and quality check).

**Major components:**
1. **API Layer** (`routes/analyze.py`) — accepts `UploadFile`, validates content-type, orchestrates pipeline, returns `{text, audio_b64}`
2. **Vision Service** (`services/vision.py`) — Moondream2 local inference (CUDA) with GPT-4o fallback; returns navigation text string
3. **TTS Service** (`services/tts.py`) — Piper ONNX on CPU; converts text string to WAV bytes
4. **App State / Lifespan** (`main.py`) — loads both models once at startup; shares as singletons via `app.state`
5. **Response Builder** (inline in route) — base64-encodes WAV, packages `{text, audio}` JSON

**Key patterns:**
- Lifespan singleton for models: load once, reuse across all requests; never load inside request handlers
- Sequential pipeline (not parallel): vision → TTS; parallelization is impossible since TTS depends on vision output
- `run_in_executor(executor, ...)` with `ThreadPoolExecutor(max_workers=1)` for GPU inference to avoid blocking the event loop
- `asyncio.create_subprocess_exec` for Piper to avoid subprocess blocking
- `torch.cuda.empty_cache()` in a `finally` block after every inference to prevent VRAM fragmentation

### Critical Pitfalls

1. **Moondream2 full-precision VRAM overflow** — Use `moondream/moondream-2b-2025-04-14-4bit` (2.4GB VRAM) not `vikhyatk/moondream2` BF16 (4.2GB, exceeds 4GB budget). Set `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512`. Verify with `nvidia-smi` that VRAM stays below 3GB after warmup.

2. **Blocking GPU inference in async handler** — PyTorch inference is synchronous C++/CUDA. Calling it directly inside `async def` blocks the event loop. Wrap in `loop.run_in_executor(ThreadPoolExecutor(max_workers=1), run_inference, image_bytes)`. Verify by checking that the health endpoint responds in <200ms during active inference.

3. **VRAM fragmentation across requests** — PyTorch's caching allocator holds reserved memory even when active tensors are freed. Call `torch.cuda.empty_cache()` in a `finally` block after every inference. Validate with a soak test of 20+ sequential requests before declaring the inference loop stable.

4. **Verbose navigation descriptions** — Moondream without a constrained prompt produces generic scene captions that take 5+ seconds to speak. Use a tightly constrained prompt: "In one short sentence (under 15 words), describe any immediate obstacles directly ahead." Set `max_new_tokens=60`. Validate that audio duration stays under 4 seconds.

5. **GPT-4o fallback without timeout** — GPT-4o vision API can take 8-16 seconds under load; without a hard timeout the demo hangs silently. Wrap with `asyncio.wait_for(call_gpt4o(image), timeout=5.0)`. Return a safe default string on timeout. Test the fallback path explicitly with the local model disabled.

## Implications for Roadmap

Based on research, the build order is dictated by risk and dependency: GPU model loading is the highest-risk component and must be proven before anything else is built on top of it. TTS is the second step in the pipeline. The HTTP layer is the thinnest layer and comes last.

### Phase 1: Foundation — GPU Model Loading and Prompt Engineering

**Rationale:** VRAM fit is the highest-risk unknown. If Moondream4bit does not fit on the GTX 1650 with appropriate headroom, everything else changes. Proving the model loads, produces correct output, and handles 20+ sequential requests without OOM fragmentation is the prerequisite for all subsequent work. Prompt engineering belongs here too — the navigation prompt is a dependency of every downstream test.
**Delivers:** Standalone vision service that accepts a PIL image and returns a navigation-focused text description. Verified VRAM budget. Verified prompt output format (under 15 words, correct hazard categories, under 80 characters).
**Addresses:** "Moondream CUDA inference" (P1 feature), "Navigation-optimized prompt" (P1 feature), "Distance/proximity language" (P1 feature)
**Avoids:** Pitfall 1 (VRAM overflow), Pitfall 3 (VRAM fragmentation), Pitfall 5 (verbose output)
**Research flag:** Standard patterns — model loading via transformers `from_pretrained` with `device_map={"": "cuda"}` is well-documented. Prompt iteration is empirical, not research-dependent.

### Phase 2: TTS Integration and End-to-End Pipeline

**Rationale:** With the vision service verified, Piper TTS is the second pipeline step. It must be integrated correctly (async subprocess, not blocking `subprocess.run`) before the HTTP layer is added, so latency is measured on the actual pipeline, not a mock.
**Delivers:** Full local pipeline: PIL image → navigation text → WAV audio bytes. Measured end-to-end latency on GTX 1650. Verified audio duration under 4 seconds.
**Uses:** piper-tts 1.4.1, onnxruntime (CPU), `asyncio.create_subprocess_exec`
**Implements:** TTS Service component
**Avoids:** Pitfall 4 (Piper subprocess blocking)
**Research flag:** Standard patterns — Piper's Python API is well-documented; async subprocess pattern is standard Python.

### Phase 3: HTTP API Layer

**Rationale:** FastAPI wraps the already-proven pipeline. The API layer is thin — `UploadFile` ingestion, lifespan model loading, JSON response packaging. The main risk (blocking inference) is addressed by `run_in_executor` which must be wired up here.
**Delivers:** Working `POST /analyze` endpoint returning `{"description": "...", "audio": "<base64>"}`. Verified that health endpoint stays responsive during active inference.
**Uses:** FastAPI 0.135, Uvicorn 0.42, python-multipart 0.0.22, Pillow 12.1.1, `lifespan` context manager
**Implements:** API Layer, App State / Lifespan components
**Avoids:** Pitfall 2 (blocking event loop), Anti-Pattern 1 (per-request model loading), Anti-Pattern 2 (temp file I/O)
**Research flag:** Standard patterns — FastAPI lifespan singleton and `run_in_executor` are well-documented; no deeper research needed.

### Phase 4: GPT-4o Fallback and Demo Hardening

**Rationale:** Fallback is the reliability layer that prevents demo failure. It must be the last phase because it is triggered by local model failure — a condition that can only be tested realistically once the full pipeline exists. The timeout logic and quality gate design require the full pipeline as context.
**Delivers:** GPT-4o fallback path with explicit quality gate (empty or short output triggers fallback), 5-second hard timeout, and safe default message on total failure. Complete "looks done but isn't" checklist verified (VRAM, latency, audio duration, sequential requests, fallback path).
**Uses:** openai 2.29.0, python-dotenv, `asyncio.wait_for`
**Implements:** Vision Service fallback path
**Avoids:** Pitfall 6 (GPT-4o fallback hanging indefinitely)
**Research flag:** Standard patterns — OpenAI SDK base64 vision pattern is well-documented.

### Phase Ordering Rationale

- **GPU model first:** VRAM fit is a hard constraint that cannot be worked around after the fact. Discovering an OOM in Phase 3 would require rearchitecting Phase 1 and 2.
- **TTS before HTTP:** Latency must be measured on the real pipeline. Building the HTTP layer before TTS risks optimizing for mock latency numbers.
- **HTTP before fallback:** Fallback behavior (quality gate thresholds, timeout values) depends on observing real local model behavior under real HTTP conditions.
- **Prompt engineering in Phase 1:** Output format is a dependency of TTS (text length drives audio duration), which is a dependency of latency measurement. It cannot be deferred.
- **No streaming, no database, no multi-user:** Research consistently supports deferring all of these; they add architectural complexity for zero demo value.

### Research Flags

Phases with standard patterns (skip research-phase):
- **Phase 1:** Model loading via transformers is well-documented; prompt iteration is empirical
- **Phase 2:** Piper Python API and async subprocess are well-documented
- **Phase 3:** FastAPI lifespan singleton pattern is well-documented with official examples
- **Phase 4:** OpenAI SDK vision pattern is well-documented

No phase requires deeper pre-planning research. All unknowns are empirical (VRAM fit, actual latency numbers, prompt quality) and are resolved during implementation with `nvidia-smi` and measured timing.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All package versions verified against PyPI and official docs; CUDA compatibility verified for GTX 1650 (sm_75) against PyTorch installer |
| Features | MEDIUM | Feature priorities from published research and competitor analysis; latency targets from arXiv papers; Moondream spatial reasoning capabilities from 2025-06 release notes (post-cutoff, medium confidence) |
| Architecture | HIGH | Pipeline patterns verified against FastAPI official docs, Piper GitHub, Moondream Hugging Face card, and reference implementations |
| Pitfalls | HIGH (VRAM/GPU), MEDIUM (UX) | VRAM pitfalls verified against PyTorch memory docs, Hugging Face model cards, and community bug reports; UX pitfalls (output verbosity) from assistive technology research, medium confidence |

**Overall confidence:** HIGH

### Gaps to Address

- **Moondream 2025-06-21 revision availability:** STACK.md references the `2025-06-21` revision for `vikhyatk/moondream2` but PITFALLS.md recommends `moondream/moondream-2b-2025-04-14-4bit`. Confirm during Phase 1 which checkpoint to use — the 4-bit model is the safe default given the VRAM constraint.
- **Actual inference latency on GTX 1650:** Research estimates 1-2 seconds for Moondream on GTX 1650 with INT4; this must be measured empirically in Phase 1. If it exceeds 2 seconds, image resizing to 384px before inference is the fallback mitigation.
- **Piper audio format compatibility with cane hardware:** ARCHITECTURE.md assumes WAV 16-bit PCM at 22050Hz; the smart cane's audio playback requirements are not specified in the research. Verify the WAV format matches client expectations before Phase 4.
- **GPT-4o vision API availability at hackathon venue:** Network access and OpenAI API rate limits during the demo are unknowns. Have the safe default message ready; consider testing fallback in airplane mode.

## Sources

### Primary (HIGH confidence)
- [FastAPI official docs — lifespan events](https://fastapi.tiangolo.com/advanced/events/)
- [PyTorch official installer — v2.10.0, CUDA 12.6](https://pytorch.org/get-started/locally/)
- [piper-tts PyPI — v1.4.1](https://pypi.org/project/piper-tts/)
- [transformers PyPI — v5.3.0](https://pypi.org/project/transformers/)
- [FastAPI PyPI — v0.135.1](https://pypi.org/project/fastapi/)
- [uvicorn PyPI — v0.42.0](https://pypi.org/project/uvicorn/)
- [openai PyPI — v2.29.0](https://pypi.org/project/openai/)
- [python-multipart PyPI — v0.0.22](https://pypi.org/project/python-multipart/)
- [rhasspy/piper-voices Hugging Face — voice model location](https://huggingface.co/rhasspy/piper-voices)
- [OpenAI Vision API — base64 pattern](https://platform.openai.com/docs/guides/vision)
- [PyTorch CUDA Memory docs](https://docs.pytorch.org/docs/stable/torch_cuda_memory.html)
- [Piper TTS GitHub — rhasspy/piper](https://github.com/rhasspy/piper)

### Secondary (MEDIUM confidence)
- [vikhyatk/moondream2 Hugging Face](https://huggingface.co/vikhyatk/moondream2) — VRAM requirements, revision pinning, query API
- [moondream/moondream-2b-2025-04-14-4bit Hugging Face](https://huggingface.co/moondream/moondream-2b-2025-04-14-4bit) — 4-bit quantization, 2.4GB VRAM
- [Moondream QAT blog](https://moondream.ai/blog/smaller-faster-moondream-with-qat) — 42% VRAM reduction vs full precision
- [Moondream grounded reasoning release (2025-06)](https://moondream.ai/blog/moondream-2025-06-21-release) — spatial reasoning support
- [Moondream2 VRAM by quantization](https://localai.computer/models/vikhyatk-moondream2) — Q4/Q8/FP16 comparison
- [Real-Time Assistive Navigation for Visually Impaired — arXiv 2025](https://arxiv.org/html/2504.20976v2) — latency targets
- [AI smart cane technology review — Springer 2025](https://link.springer.com/article/10.1007/s44443-025-00234-9) — feature expectations
- [Describe Now: User-Driven Audio Description — arXiv/ACM 2025](https://arxiv.org/html/2411.11835v2) — UX pitfall validation
- [Piper TTS Python interface — DeepWiki](https://deepwiki.com/rhasspy/piper/5-python-interface) — synthesis API
- [FastAPI singleton patterns — Medium](https://medium.com/@hieutrantrung.it/using-fastapi-like-a-pro-with-singleton-and-dependency-injection-patterns-28de0a833a52)

### Tertiary (LOW confidence)
- [GPT-4o vision API latency — OpenAI Community](https://community.openai.com/t/ongoing-latency-in-gpt-4o-this-week/1315927) — 8-16s estimate; may vary significantly by date and load
- [Run vLLM on 4GB VRAM — Medium](https://kumarshivam-66534.medium.com/run-vllm-locally-on-low-vram-budget-laptop-4gb-gpu-in-2025-full-docker-guide-errors-ollama-bf8c498e7dec) — VRAM fragmentation strategies; vLLM-specific but principles apply

---
*Research completed: 2026-03-21*
*Ready for roadmap: yes*
