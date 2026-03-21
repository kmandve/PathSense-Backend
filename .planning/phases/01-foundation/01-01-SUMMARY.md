---
phase: 01-foundation
plan: 01
subsystem: infra
tags: [fastapi, uvicorn, transformers, moondream, pytorch, pytest, httpx]

# Dependency graph
requires: []
provides:
  - FastAPI app with lifespan-based Moondream 4-bit model loading
  - GET /health endpoint with CUDA and VRAM status reporting
  - pathsense/ Python package structure (main, config, routes, models, services)
  - AppState dataclass for typed app.state model container
  - Pinned requirements.txt for all dependencies
  - pytest + httpx test infrastructure with async_client fixture
  - Mock-based health and startup tests (8 tests, all green)
affects: [02-tts, 03-api, 04-fallback]

# Tech tracking
tech-stack:
  added:
    - fastapi==0.135.1
    - uvicorn[standard]==0.42.0
    - transformers[torch]==5.3.0
    - Pillow==12.1.1
    - python-multipart==0.0.22
    - python-dotenv
    - pytest + pytest-asyncio
    - httpx (AsyncClient + ASGITransport for in-process testing)
    - torch (production: CUDA 12.6 build; dev: CPU)
  patterns:
    - Lifespan singleton for model loading (load once at startup, store in app.state)
    - ASGITransport for in-process test client (no live server needed)
    - Mock-based tests that avoid GPU dependency in dev environments
    - CUDA mock patching (patch torch.cuda.is_available) for dev-environment tests

key-files:
  created:
    - pathsense/main.py
    - pathsense/config.py
    - pathsense/models/state.py
    - pathsense/routes/analyze.py
    - pathsense/__init__.py
    - pathsense/models/__init__.py
    - pathsense/services/__init__.py
    - pathsense/routes/__init__.py
    - requirements.txt
    - .env.example
    - pytest.ini
    - tests/conftest.py
    - tests/test_health.py
    - tests/test_startup.py
    - tests/fixtures/test_image.jpg
    - .gitignore
  modified: []

key-decisions:
  - "Moondream 4-bit checkpoint moondream/moondream-2b-2025-04-14-4bit via device_map={'': 'cuda'} (VRAM constraint: 4GB GTX 1650)"
  - "Tokenizer from vikhyatk/moondream2 revision 2025-06-21 (separate org, pinned revision for reproducibility)"
  - "Health endpoint returns 503 if model_loaded=False OR cuda_ok=False (both required for production)"
  - "Tests mock torch.cuda.is_available() to run on dev machines without CUDA"

patterns-established:
  - "Pattern: lifespan context manager loads model once at startup, cleans up on shutdown with torch.cuda.empty_cache()"
  - "Pattern: app.state holds vision_model and tokenizer for request handler access"
  - "Pattern: ASGITransport + AsyncClient for async endpoint tests without live server"
  - "Pattern: mock_model + mock_tokenizer fixtures injected into app.state to bypass GPU dependency in tests"

requirements-completed: [INF-01, INF-02, INF-03, INF-04, VIS-01]

# Metrics
duration: 3min
completed: 2026-03-21
---

# Phase 1 Plan 01: Foundation Scaffold Summary

**FastAPI app with lifespan-based Moondream 4-bit loading on CUDA, GET /health endpoint, and mock-based pytest test infrastructure — all 8 tests green**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-21T05:45:44Z
- **Completed:** 2026-03-21T05:48:51Z
- **Tasks:** 2
- **Files modified:** 16

## Accomplishments

- Created the full pathsense/ Python package with FastAPI app, lifespan model loading, and config constants
- Implemented GET /health returning model_loaded, CUDA status, and VRAM usage — raises 503 if model or GPU unavailable
- Set up pytest test infrastructure with async_client fixture, mocked model/tokenizer, CUDA patching — 8 tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Project scaffold, FastAPI app with lifespan model loading** - `f9cb526` (feat)
2. **Task 2: Test infrastructure and health check tests** - `998cd63` (feat)

**Plan metadata:** _(docs commit hash after SUMMARY creation)_

## Files Created/Modified

- `pathsense/main.py` - FastAPI app with asynccontextmanager lifespan, loads Moondream 4-bit at startup via device_map={"": "cuda"}
- `pathsense/config.py` - Centralized constants: MODEL_ID, TOKENIZER_ID, TOKENIZER_REVISION, MAX_IMAGE_DIM, SUPPORTED_CONTENT_TYPES
- `pathsense/models/state.py` - AppState dataclass with vision_model and tokenizer Any fields
- `pathsense/routes/analyze.py` - GET /health endpoint with model_loaded check, CUDA check, VRAM reporting, 503 on failure
- `pathsense/routes/__init__.py` - Empty package marker
- `pathsense/models/__init__.py` - Empty package marker
- `pathsense/services/__init__.py` - Empty package marker (vision.py is Plan 02)
- `pathsense/__init__.py` - Empty package marker
- `requirements.txt` - Pinned dependencies: fastapi==0.135.1, uvicorn==0.42.0, transformers==5.3.0, Pillow==12.1.1, python-multipart==0.0.22
- `.env.example` - Documents PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
- `pytest.ini` - asyncio_mode=auto, testpaths=tests
- `tests/conftest.py` - Shared fixtures: mock_model, mock_tokenizer, app_with_model, async_client (ASGITransport)
- `tests/test_health.py` - test_health_returns_200_with_model (mocks CUDA), test_health_returns_503_without_model
- `tests/test_startup.py` - app title, model_id 4bit check, tokenizer constants, lifespan callable, router mount
- `tests/fixtures/test_image.jpg` - 100x100 red JPEG for integration tests
- `.gitignore` - Excludes __pycache__, .venv, .env, .pytest_cache

## Decisions Made

- Used `device_map={"": "cuda"}` (not `torch_dtype=torch.float16`) per plan spec — the 4-bit checkpoint manages dtype internally
- Tokenizer and model cleaned up separately at shutdown: `del app.state.vision_model; del app.state.tokenizer; torch.cuda.empty_cache()`
- AppState uses `Any` type for vision_model/tokenizer (transformers types are dynamic via trust_remote_code)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added torch.cuda.is_available() and torch.cuda.memory_reserved() mocks to health tests**
- **Found during:** Task 2 (test infrastructure)
- **Issue:** test_health_returns_200_with_model would always fail on macOS dev machine because torch.cuda.is_available() returns False without NVIDIA GPU. The health endpoint correctly requires both model_loaded AND cuda_ok — tests must mock CUDA on non-CUDA machines.
- **Fix:** Added `patch("pathsense.routes.analyze.torch.cuda.is_available", return_value=True)` and `patch("pathsense.routes.analyze.torch.cuda.memory_reserved", return_value=...)` around the 200 test.
- **Files modified:** tests/test_health.py
- **Verification:** All 8 tests passing
- **Committed in:** 998cd63 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 bug fix)
**Impact on plan:** Fix required for tests to pass on any machine without CUDA. Production behavior unchanged.

## Issues Encountered

- `transformers` and `torch` not installed in the macOS dev environment — installed CPU versions to enable import verification. Production machine uses PyTorch with CUDA 12.6 installed separately via `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126`.

## Known Stubs

None — all files contain complete, production-ready code. The services/__init__.py and other empty __init__.py files are intentionally empty package markers, not stubs.

## User Setup Required

None — no external service configuration required. The Moondream model downloads automatically from HuggingFace on first `uvicorn` run.

**Production startup requires:**
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements.txt
uvicorn pathsense.main:app --host 0.0.0.0 --port 8000 --workers 1
```

## Next Phase Readiness

- FastAPI skeleton complete, ready for Plan 02 (TTS integration via services/tts.py)
- Plan 03 (POST /analyze image inference endpoint) can now reference app.state.vision_model
- VRAM verification on actual GTX 1650 hardware should happen before Plan 03

## Self-Check: PASSED

- All 16 created files confirmed present on disk
- Task commits f9cb526 and 998cd63 confirmed in git log
- All 8 pytest tests confirmed passing
