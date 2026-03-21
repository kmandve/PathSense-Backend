# Pitfalls Research

**Domain:** Local vision model inference API for assistive blind navigation
**Researched:** 2026-03-21
**Confidence:** HIGH (critical VRAM/GPU pitfalls); MEDIUM (UX/audio description pitfalls)

---

## Critical Pitfalls

### Pitfall 1: Moondream2 Full-Precision VRAM Overflow on GTX 1650

**What goes wrong:**
Moondream2 at BF16 (full precision) requires approximately 4.2GB of VRAM. The GTX 1650 has 4GB. The model appears to load successfully but then crashes during the first inference with a CUDA OOM error because the PyTorch runtime, CUDA context initialization (100-200MB overhead), and activation buffers push total usage over the 4GB physical limit.

**Why it happens:**
Developers see "1.6B parameters" and estimate ~3GB — but miss that PyTorch's memory allocator reserves a contiguous pool, CUDA context init takes 200MB before a single tensor is allocated, and image encoding for a VLM creates temporary tensors that spike usage during the forward pass. The model loads fine; it's the first image inference call that explodes.

**How to avoid:**
Use the 4-bit quantized version of Moondream: `moondream/moondream-2b-2025-04-14-4bit` on Hugging Face. Peak VRAM drops to 2.4GB (42% reduction). Load the model once at server startup — never reload per-request. Set `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512` to reduce fragmentation.

```python
# Correct: load at startup, use int4 checkpoint
from transformers import AutoModelForCausalLM
model = AutoModelForCausalLM.from_pretrained(
    "moondream/moondream-2b-2025-04-14-4bit",
    device_map={"": "cuda"},
    trust_remote_code=True,
)
```

**Warning signs:**
- `torch.cuda.memory_reserved()` shows > 3.5GB before the first request
- First request succeeds, second fails with OOM (fragmentation accumulates)
- `nvidia-smi` shows 99%+ VRAM during startup

**Phase to address:** Phase 1 (model loading / GPU setup) — must be proven on-device before anything else is built.

---

### Pitfall 2: Blocking Inference Starves the FastAPI Event Loop

**What goes wrong:**
PyTorch inference is CPU/GPU-bound and synchronous. Running it inside a standard `async def` FastAPI endpoint blocks the entire uvicorn event loop. While one image is being analyzed (which may take 1-3 seconds), all other requests — including health checks and the TTS call — queue behind it. Under any concurrent load the server becomes unresponsive.

**Why it happens:**
Developers write `async def analyze(file: UploadFile)` and call `model.generate(...)` directly inside it. This looks asynchronous but is not — model inference is a blocking C++/CUDA operation. FastAPI's async support only helps with I/O-bound work.

**How to avoid:**
Run inference in a thread pool executor so the event loop is not blocked:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=1)  # 1 worker: serializes GPU access

async def analyze(file: UploadFile):
    image_bytes = await file.read()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, run_inference, image_bytes)
    return result
```

Use `max_workers=1` — the GPU can only handle one inference at a time on 4GB VRAM, and concurrent submissions will OOM.

**Warning signs:**
- Health check endpoint times out during an active inference
- Piper TTS call (triggered after inference) takes 10+ seconds even though TTS itself is fast
- `asyncio` "Task took too long to complete" warnings in logs

**Phase to address:** Phase 1 (API server setup) — architecture decision that is expensive to retrofit.

---

### Pitfall 3: VRAM Fragmentation Causes OOM on Second or Third Request

**What goes wrong:**
Even with the 4-bit model, if intermediate tensors from one inference are not explicitly released, PyTorch's caching allocator holds them in a reserved pool. After several requests the cached pool fills 4GB even though "active" tensors are small, and the next allocation fails with OOM despite most of that memory being "free" in PyTorch's internal accounting.

**Why it happens:**
PyTorch separates "reserved" from "allocated" memory. `torch.cuda.memory_reserved()` can show 3.8GB while `torch.cuda.memory_allocated()` shows 1.2GB. The reserved pool is fragmented — the needed contiguous block does not exist. Calling `torch.cuda.empty_cache()` is not enough if tensors are still referenced.

**How to avoid:**
After every inference call, explicitly delete intermediate tensors and call `torch.cuda.empty_cache()`:

```python
def run_inference(image_bytes):
    try:
        img = decode_image(image_bytes)
        answer = model.query(img, NAVIGATION_PROMPT)["answer"]
        return answer
    finally:
        torch.cuda.empty_cache()
```

Also: never accumulate image tensors or outputs in a list (e.g. for logging) without immediately releasing them.

**Warning signs:**
- `torch.cuda.memory_reserved()` grows monotonically across requests
- OOM errors appear on request 5-10 but not request 1
- `nvidia-smi` VRAM usage climbs steadily and never drops

**Phase to address:** Phase 1 (inference loop), verified with a soak test of 20+ sequential requests.

---

### Pitfall 4: Piper TTS Subprocess Blocking on Audio Generation

**What goes wrong:**
Piper is commonly invoked via `subprocess.run(["piper", ...])`, which is a blocking call. If called from within the FastAPI request handler (even via `run_in_executor`), and the executor thread is also handling inference, the TTS generation serializes on the same single-worker executor. This adds 0.5-1.5 seconds of audio generation time on top of the already-slow inference, pushing total response time past the 3-second target.

**Why it happens:**
Developers call Piper after inference in the same executor thread to "keep it simple." The subprocess blocks that thread until audio is complete. With a single-worker executor this means inference and TTS are strictly sequential.

**How to avoid:**
Run Piper in a separate executor or as an `asyncio.create_subprocess_exec` call:

```python
async def synthesize_audio(text: str) -> bytes:
    proc = await asyncio.create_subprocess_exec(
        "piper", "--model", MODEL_PATH, "--output_raw",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )
    raw_audio, _ = await proc.communicate(text.encode())
    return raw_audio
```

This keeps audio synthesis non-blocking and independent from the GPU inference thread.

**Warning signs:**
- Total response time = inference time + TTS time with no overlap
- Executor thread shows 100% utilization even during the audio phase
- Profiling shows Piper subprocess consumes 40%+ of total request latency

**Phase to address:** Phase 2 (TTS integration) — design the async pipeline correctly from the start.

---

### Pitfall 5: Navigation Descriptions Are Too Long to Be Actionable

**What goes wrong:**
The vision model returns verbose scene descriptions — "There is a wooden table with a chair on the left side, a potted plant, and a window in the background behind a person" — that take 5+ seconds to speak and overload the user cognitively while they are actively moving. By the time audio finishes, the scene has changed and the description is stale.

**Why it happens:**
Moondream's default output is designed for general Q&A. Without a tightly constrained prompt, it describes everything it sees rather than the safety-critical subset a cane user needs. The prompt "describe this scene" produces an encyclopedia; blind navigation requires a telegram.

**How to avoid:**
Use a highly constrained, navigation-specific prompt with explicit token limits:

```python
NAVIGATION_PROMPT = (
    "In one short sentence (under 15 words), describe any immediate obstacles "
    "or navigation hazards directly ahead: doors, steps, people, barriers. "
    "If path is clear, say 'Path is clear'."
)
```

Also set `max_new_tokens=60` to hard-cap output length. Validate at integration time that TTS output stays under 4 seconds.

**Warning signs:**
- TTS audio file is > 3MB (WAV, 16kHz) or > 6 seconds duration
- Moondream output regularly exceeds 100 characters
- User study (even informal) shows confusion from information overload

**Phase to address:** Phase 1 (prompt engineering) and Phase 2 (end-to-end latency validation).

---

### Pitfall 6: GPT-4o Fallback Adds 8-16 Seconds of Latency Without a Timeout

**What goes wrong:**
The GPT-4o fallback is triggered when local inference quality is "insufficient." Without an explicit timeout and quality gate, the fallback path adds 8-16 seconds of network latency (GPT-4o vision API averages ~8 seconds; can degrade to 16s+). The user experiences a silent pause that feels like a crash.

**Why it happens:**
Fallback logic is added as an afterthought — "if local model fails, call GPT-4o." No timeout is set, no user-facing feedback is given during the wait, and the condition triggering fallback is vague. During the hackathon demo, the network may be congested or the OpenAI API rate-limited.

**How to avoid:**
- Define an explicit fallback trigger: only call GPT-4o if local inference returns an empty string or takes > 2.5 seconds
- Set a hard timeout on the GPT-4o call (5 seconds max for demo use)
- Return a safe default message if both fail: "Unable to analyze. Please try again."
- Never make the fallback call synchronous in the request path without timeout:

```python
try:
    result = await asyncio.wait_for(call_gpt4o(image_bytes), timeout=5.0)
except asyncio.TimeoutError:
    result = "Unable to analyze scene. Please proceed carefully."
```

**Warning signs:**
- Any code path with `openai.chat.completions.create(...)` that lacks a timeout parameter
- Fallback triggered on every request in demo conditions (indicates local model failure)
- Response time histogram shows bimodal distribution (fast local path + slow fallback path)

**Phase to address:** Phase 3 (fallback integration) — requires explicit timeout design from the start.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Load model per-request instead of at startup | Simpler code | 3-5 second load time per request, VRAM churn | Never — always load once |
| Use `subprocess.run` (blocking) for Piper | Easy to implement | Blocks event loop, adds latency | Acceptable only for single-request CLI scripts, not API servers |
| Skip `torch.cuda.empty_cache()` after inference | Fewer lines of code | VRAM fragmentation causes OOM after 5-10 requests | Never in a long-running server |
| Return raw Moondream output without prompt constraints | No prompt engineering effort | Verbose, non-navigational output that takes 6+ seconds to speak | Never for navigation use case |
| Hardcode Moondream full-precision (BF16) weights | Uses default model | OOM on GTX 1650 on first inference | Never on 4GB VRAM hardware |
| No fallback timeout | Simpler control flow | Demo hangs indefinitely if GPT-4o is slow/unavailable | Never in demo conditions |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Moondream via HuggingFace | Using `vikhyatk/moondream2` (BF16, 4.2GB) | Use `moondream/moondream-2b-2025-04-14-4bit` (int4, 2.4GB) |
| Moondream `trust_remote_code=True` | Omitting this flag causes silent model load failure | Always pass `trust_remote_code=True` in `from_pretrained` |
| Piper model file | Assuming Piper is pre-installed; it needs a `.onnx` model file downloaded separately | Download the voice model file explicitly: `en_US-lessac-medium.onnx` |
| FastAPI UploadFile | Calling `file.read()` twice (once for validation, once for inference) — second read returns empty bytes | Read once, store result in variable |
| OpenAI vision API | Sending raw image bytes; API requires base64-encoded string in a specific JSON schema | Encode: `base64.b64encode(image_bytes).decode('utf-8')` before sending |
| CUDA + FastAPI startup | Model loading during module import instead of `@app.on_event("startup")` — causes issues in worker forks | Load model inside startup event handler |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Model reload per-request | Response time = 4+ seconds even for simple images | Load once at startup, hold in module-level variable | From the very first request |
| Synchronous inference in async handler | Health endpoint times out during active inference | Use `run_in_executor` with dedicated thread pool | Under any concurrency (>1 request) |
| WAV file written to disk then read back | Extra disk I/O adds 50-200ms to audio path | Stream Piper stdout directly to response bytes in memory | At any throughput |
| Full-resolution images from camera | Image decode + resize adds 200-500ms; VLMs don't benefit from > 384px inputs | Resize to 384px max on the server before inference | With high-res camera inputs |
| Returning raw WAV bytes in JSON body | Base64 encoding inflates audio by 33%; JSON parse overhead on client | Return `Content-Type: audio/wav` as binary, or multipart response | With any meaningful audio length |

---

## "Looks Done But Isn't" Checklist

- [ ] **Model loading:** Model loads without error — but verify first inference succeeds without OOM. `torch.cuda.memory_reserved()` should be < 3GB after warmup.
- [ ] **Response latency:** API returns 200 OK — but measure end-to-end: image upload + inference + TTS synthesis + audio bytes in response. All must be < 3 seconds.
- [ ] **Piper audio quality:** Piper produces audio output — but verify it plays correctly on the target device (WAV headers, sample rate 16kHz or 22050Hz match client expectations).
- [ ] **Fallback path:** GPT-4o fallback code exists — but test it explicitly with local model disabled. Verify it does not hang and returns within 5 seconds.
- [ ] **Sequential requests:** First request works — but run 20 sequential requests to verify no VRAM leak causes OOM on request 10+.
- [ ] **Navigation prompt quality:** Model returns text — but verify output is under 15 words and mentions the correct hazard category, not irrelevant scene details.
- [ ] **Audio duration:** TTS produces audio — but measure duration. Must be < 4 seconds for a useful navigation update frequency.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| BF16 model OOM on GTX 1650 | LOW | Switch to `moondream-2b-2025-04-14-4bit`; no code changes needed beyond model path |
| Blocking inference in async handler | MEDIUM | Wrap inference call in `run_in_executor`; requires adding executor to app state |
| VRAM fragmentation after N requests | LOW | Add `torch.cuda.empty_cache()` in finally block; 5-minute fix |
| Piper blocking on subprocess | LOW | Switch to `asyncio.create_subprocess_exec`; isolated change |
| Verbose navigation descriptions | LOW | Tighten prompt and add `max_new_tokens` cap; 10-minute fix |
| GPT-4o fallback hanging | LOW | Wrap with `asyncio.wait_for(..., timeout=5.0)`; isolated change |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Moondream2 VRAM overflow (full precision) | Phase 1: Model loading | `nvidia-smi` shows < 3GB VRAM after startup; first 5 inferences succeed |
| Blocking inference in async handler | Phase 1: API server setup | Health endpoint responds < 200ms during active inference |
| VRAM fragmentation across requests | Phase 1: Inference loop | 20 sequential requests complete without OOM |
| Piper TTS subprocess blocking | Phase 2: TTS integration | Total latency < 3s measured end-to-end with profiling |
| Verbose non-navigational output | Phase 1: Prompt engineering | Output length < 80 characters; audio duration < 4 seconds |
| GPT-4o fallback without timeout | Phase 3: Fallback integration | Fallback path with network disabled returns within 5 seconds |

---

## Sources

- [Moondream 4-bit quantization blog (42% VRAM reduction, 2.4GB peak)](https://moondream.ai/blog/smaller-faster-moondream-with-qat)
- [moondream-2b-2025-04-14-4bit on Hugging Face](https://huggingface.co/moondream/moondream-2b-2025-04-14-4bit)
- [Avoid CUDA OOM: LLM Memory Optimization Guide — Lyceum Technology](https://lyceum.technology/magazine/avoid-cuda-oom-large-language-model/)
- [GPU Survival Guide: Avoid OOM Crashes — RunPod](https://www.runpod.io/articles/guides/avoid-oom-crashes-for-large-models)
- [PyTorch CUDA Memory Documentation](https://docs.pytorch.org/docs/stable/torch_cuda_memory.html)
- [torch.cuda.empty_cache does not clear all memory — PyTorch GitHub Issue #46602](https://github.com/pytorch/pytorch/issues/46602)
- [Run vLLM on 4GB VRAM — Kumar Shivam / Medium](https://kumarshivam-66534.medium.com/run-vllm-locally-on-low-vram-budget-laptop-4gb-gpu-in-2025-full-docker-guide-errors-ollama-bf8c498e7dec)
- [Describe Now: User-Driven Audio Description for Blind and Low Vision — arXiv/ACM 2025](https://arxiv.org/html/2411.11835v2)
- [Piper TTS GitHub — rhasspy/piper](https://github.com/rhasspy/piper)
- [Optimizing FastAPI File Uploads — sqlpey](https://sqlpey.com/python/optimizing-fastapi-file-uploads/)
- [GPT-4o Vision API latency degradation — OpenAI Community](https://community.openai.com/t/ongoing-latency-in-gpt-4o-this-week/1315927)
- [Assistive Systems for Visually Impaired Persons — PMC/MDPI 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11175312/)

---

*Pitfalls research for: local vision model + TTS API for assistive blind navigation (PathSense)*
*Researched: 2026-03-21*
