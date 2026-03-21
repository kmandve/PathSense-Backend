---
phase: 03-http-api-layer
plan: 01
subsystem: api
tags: [fastapi, piper-tts, base64, wav, openai, gpt-4o, pytest]

# Dependency graph
requires:
  - phase: 02-tts-integration
    provides: synthesize_async(voice, text) -> bytes, PiperVoice loaded at app.state.tts_voice
  - phase: 01-foundation
    provides: FastAPI app skeleton, vision service, analyze route, health endpoint

provides:
  - POST /analyze returns {"description": str, "audio": base64-WAV-string} — full pipeline response
  - GET /health returns model_loaded + vram_reserved_mb or 503 when vision_model is None
  - async_client_full fixture for full-pipeline integration tests
  - autouse mock_run_inference fixture prevents real OpenAI API calls during all tests

affects: [04-quality-fallback, smart-cane-firmware]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "base64.b64encode(wav_bytes).decode('utf-8') for audio field in JSON response"
    - "autouse pytest fixture patches run_inference_async for all tests (no real API calls)"
    - "Lazy OpenAI client via _get_client() to allow test imports without OPENAI_API_KEY"
    - "torch.cuda.memory_reserved()/1024**2 for VRAM reporting in health endpoint"

key-files:
  created: []
  modified:
    - pathsense/routes/analyze.py
    - pathsense/services/vision.py
    - tests/conftest.py
    - tests/test_analyze.py

key-decisions:
  - "app_with_model fixture updated to also set tts_voice — analyze now requires both for end-to-end flow"
  - "autouse mock_run_inference fixture patches run_inference_async globally — no real GPT-4o calls during tests"
  - "Lazy OpenAI client (_get_client) in vision.py avoids ImportError when OPENAI_API_KEY is absent"
  - "health endpoint checks app.state.vision_model for model_loaded even though GPT-4o needs no local model"

patterns-established:
  - "Full pipeline test pattern: async_client_full uses app_with_full_pipeline (vision + TTS both mocked)"
  - "TTS failure raises HTTPException(500, detail='TTS failed: ...') — no silent audio drop"

requirements-completed: [API-01, API-02, API-03]

# Metrics
duration: 5min
completed: 2026-03-21
---

# Phase 3 Plan 1: HTTP API Layer Summary

**POST /analyze now returns base64-WAV audio alongside text via Piper TTS, and GET /health reports model_loaded + VRAM usage or 503**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-21T07:27:33Z
- **Completed:** 2026-03-21T07:32:30Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Wired Piper TTS into POST /analyze: vision description -> synthesize_async -> base64 WAV -> JSON
- Updated GET /health to return `model_loaded`, `vram_reserved_mb` and 503 when model not set
- Added `app_with_full_pipeline` and `async_client_full` fixtures for end-to-end pipeline tests
- Added three new audio tests: field presence, base64 string validation, WAV structure decode
- Fixed lazy OpenAI client init to allow test imports without OPENAI_API_KEY set

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire TTS into analyze route and fix health endpoint** - `de23b94` (feat)
2. **Task 2: Update conftest and tests for full pipeline response shape** - `3444f37` (feat)

## Files Created/Modified
- `pathsense/routes/analyze.py` - Added synthesize_async call, base64 encoding, updated health endpoint
- `pathsense/services/vision.py` - Lazy OpenAI client initialization via _get_client()
- `tests/conftest.py` - Added app_with_full_pipeline, async_client_full, autouse mock_run_inference
- `tests/test_analyze.py` - Added three new audio response tests

## Decisions Made
- Updated `app_with_model` fixture to also set `tts_voice` since analyze now requires TTS for any successful response
- Added autouse `mock_run_inference` fixture that patches `run_inference_async` for all tests — prevents accidental real OpenAI API calls during testing
- Made OpenAI client lazy-initialized in vision.py (`_get_client()`) so the module can be imported without `OPENAI_API_KEY` being set in test environments
- Health endpoint checks `app.state.vision_model` for `model_loaded` even though GPT-4o path doesn't use a local model — this preserves health monitoring for the Moondream fallback path (Phase 4)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed vision.py module-level OpenAI client initialization failing on import**
- **Found during:** Task 2 (running tests)
- **Issue:** `AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))` raised `OpenAIError` at import time when env var not set — conftest couldn't load
- **Fix:** Replaced module-level client with lazy `_get_client()` function; client only created when `run_inference_async` is actually called
- **Files modified:** `pathsense/services/vision.py`
- **Verification:** `python -m pytest tests/test_analyze.py tests/test_health.py` passes without OPENAI_API_KEY
- **Committed in:** `3444f37` (Task 2 commit)

**2. [Rule 1 - Bug] Fixed app_with_model fixture missing tts_voice — analyze now requires TTS**
- **Found during:** Task 2 (existing tests returned 500)
- **Issue:** Original `app_with_model` only set `vision_model`; after Task 1 changes, analyze calls `synthesize_async(request.app.state.tts_voice, ...)` which raised AttributeError on None
- **Fix:** Updated `app_with_model` fixture to also accept and set `mock_tts_voice`
- **Files modified:** `tests/conftest.py`
- **Verification:** All 12 analyze + health tests pass
- **Committed in:** `3444f37` (Task 2 commit)

**3. [Rule 2 - Missing Critical] Added autouse mock_run_inference fixture to prevent real API calls**
- **Found during:** Task 2 (test design)
- **Issue:** Tests call `/analyze` which calls `run_inference_async` — without a mock this would hit the real OpenAI API, fail in CI, and incur API costs
- **Fix:** Added `@pytest.fixture(autouse=True)` that patches `pathsense.routes.analyze.run_inference_async` with AsyncMock returning the navigation description from the mock_model fixture
- **Files modified:** `tests/conftest.py`
- **Verification:** 12/12 tests pass without OPENAI_API_KEY
- **Committed in:** `3444f37` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (2 Rule 1 bugs, 1 Rule 2 missing critical)
**Impact on plan:** All auto-fixes essential for correctness and testability. No scope creep.

## Issues Encountered
- `tests/test_startup.py` and `tests/test_vision.py` were already broken before this plan (reference old Moondream symbols: `MODEL_ID`, `_run_inference`). Logged to `deferred-items.md`. These are out of scope for this plan.

## Known Stubs
None — all data flows are wired end-to-end. The `audio` field in the response is always populated from real TTS synthesis (or mocked TTS in tests).

## Next Phase Readiness
- Full pipeline (vision → TTS → base64 audio) is complete and tested
- Smart cane firmware can POST images and receive both text + audio in one response
- Phase 4 (GPT-4o quality fallback) can build on the existing `run_inference_async` interface

---
*Phase: 03-http-api-layer*
*Completed: 2026-03-21*
