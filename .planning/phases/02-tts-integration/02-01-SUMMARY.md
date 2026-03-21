---
phase: 02-tts-integration
plan: 01
subsystem: api
tags: [piper-tts, onnxruntime, tts, wav, audio, fastapi, lifespan]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: FastAPI app structure, lifespan pattern, config constants, vision service async pattern
provides:
  - pathsense/services/tts.py with synthesize() and synthesize_async() functions
  - PIPER_VOICE_MODEL_PATH config constant in pathsense/config.py
  - PiperVoice loaded at startup stored as app.state.tts_voice
  - 5 TTS unit tests in tests/test_tts.py (no .onnx file required)
  - mock_tts_voice and app_with_tts fixtures in tests/conftest.py
affects:
  - 03-analyze-integration  # Phase 3 calls synthesize_async(request.app.state.tts_voice, description)

# Tech tracking
tech-stack:
  added: [piper-tts==1.4.1, onnxruntime (CPU)]
  patterns:
    - run_in_executor async wrapper for CPU-bound ONNX inference (mirrors vision.py pattern)
    - FastAPI lifespan loads heavy models once at startup and stores in app.state
    - asyncio.get_running_loop() preferred over deprecated get_event_loop() for executor dispatch

key-files:
  created:
    - pathsense/services/tts.py
    - tests/test_tts.py
  modified:
    - pathsense/config.py
    - pathsense/main.py
    - requirements.txt
    - tests/conftest.py

key-decisions:
  - "Use asyncio.get_running_loop() instead of get_event_loop() for executor dispatch — avoids DeprecationWarning in Python 3.10+"
  - "Piper TTS runs on CPU via onnxruntime (not onnxruntime-gpu) to keep VRAM free for vision model"
  - "PiperVoice loaded once at lifespan startup — not per-request — same pattern as vision model"
  - "Mock voice in tests writes real WAV bytes via wave module so header assertions are meaningful"

patterns-established:
  - "Async service pattern: sync function + async wrapper using run_in_executor (same as vision.py)"
  - "Lifespan startup pattern: load model → store in app.state → yield"
  - "Test fixture pattern: mock voice with real WAV-writing side_effect so bytes checks pass without .onnx file"

requirements-completed: [TTS-01, TTS-02, TTS-03]

# Metrics
duration: 4min
completed: 2026-03-21
---

# Phase 2 Plan 1: TTS Service Summary

**Piper TTS service with CPU ONNX inference via synthesize()/synthesize_async(), voice loaded once at FastAPI lifespan startup into app.state.tts_voice**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-21T06:54:36Z
- **Completed:** 2026-03-21T06:58:30Z
- **Tasks:** 2 (with TDD RED/GREEN cycles)
- **Files modified:** 6

## Accomplishments

- Created `pathsense/services/tts.py` with `synthesize(voice, text) -> bytes` and `synthesize_async(voice, text) -> bytes` using `run_in_executor` for non-blocking event loop operation
- Wired `PiperVoice.load(PIPER_VOICE_MODEL_PATH)` into the FastAPI lifespan so the voice is loaded once at startup and stored as `app.state.tts_voice` (ready for Phase 3 routes)
- 5 tests passing in `tests/test_tts.py` covering WAV header validation, text passthrough, latency (<1s), async equivalence, and event loop safety — all without a real .onnx model file

## Task Commits

Each task was committed atomically:

1. **Task 1: TTS service RED** - `6db40a9` (test)
2. **Task 1: TTS service GREEN** - `4186035` (feat)
3. **Task 2: Lifespan wiring and fixtures** - `ef992a1` (feat)

_Note: TDD tasks have RED (failing test) and GREEN (implementation) commits_

## Files Created/Modified

- `pathsense/services/tts.py` — TTS service with `synthesize()` (sync) and `synthesize_async()` (async executor wrapper)
- `tests/test_tts.py` — 5 unit tests; mocked voice writes real WAV bytes via `wave` module
- `pathsense/config.py` — Added `PIPER_VOICE_MODEL_PATH` constant (reads from env, defaults to `models/en_US-lessac-medium.onnx`)
- `pathsense/main.py` — Extended lifespan to load PiperVoice and store as `app.state.tts_voice`
- `requirements.txt` — Added `piper-tts==1.4.1` and `onnxruntime`
- `tests/conftest.py` — Added `mock_tts_voice` and `app_with_tts` fixtures

## Decisions Made

- Used `asyncio.get_running_loop()` instead of the deprecated `asyncio.get_event_loop()` for dispatching to `run_in_executor` — avoids DeprecationWarning in Python 3.10+ and matches best practice
- `onnxruntime` (CPU) chosen over `onnxruntime-gpu` — Piper on CPU completes short navigation phrases in <100ms; using GPU would consume VRAM needed by the vision model
- Voice loaded in lifespan startup (not lazily per-request) — consistent with the vision model pattern and avoids 1-2s cold start per request

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing piper-tts and onnxruntime packages**
- **Found during:** Task 1 GREEN phase (imports failed)
- **Issue:** `piper-tts` and `onnxruntime` were listed in requirements.txt but not yet installed in the environment
- **Fix:** `pip install piper-tts==1.4.1 onnxruntime`
- **Files modified:** None (environment install only)
- **Verification:** `from pathsense.services.tts import synthesize, synthesize_async` imports cleanly
- **Committed in:** N/A (environment change, not a code change)

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking environment dependency)
**Impact on plan:** Necessary for import to succeed. No scope creep.

## Issues Encountered

Pre-existing test failures in `tests/test_health.py` and `tests/test_vision.py` were discovered but are out of scope:
- `test_health.py` patches `pathsense.routes.analyze.torch` which no longer exists (Phase 1 pivot from local Moondream to GPT-4o removed torch from the route)
- `test_vision.py` imports `_run_inference` from `pathsense.services.vision` which was renamed during Phase 1

These failures predate this plan and are logged to `deferred-items.md` for follow-up.

## User Setup Required

The Piper voice model file must be downloaded before running the production server:

```bash
# Download voice model (required for actual TTS — not needed for tests)
mkdir -p models
# From: https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/lessac/medium
# Download: en_US-lessac-medium.onnx and en_US-lessac-medium.onnx.json into models/
```

Override with `PIPER_VOICE_MODEL_PATH` env var if using a different path.

## Next Phase Readiness

Phase 3 (analyze route integration) can call TTS with:
```python
audio_bytes = await synthesize_async(request.app.state.tts_voice, description)
```

- `app.state.tts_voice` is set at lifespan startup — available on every request
- `synthesize_async` is non-blocking — safe to await inside FastAPI route handlers
- Output is raw WAV bytes (16-bit PCM, 22050Hz) — base64-encode before JSON response

---
*Phase: 02-tts-integration*
*Completed: 2026-03-21*
