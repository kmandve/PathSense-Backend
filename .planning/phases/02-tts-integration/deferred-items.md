# Deferred Items — Phase 02-tts-integration

## Pre-existing test failures (out of scope for Plan 02-01)

### test_health.py failures
- `test_health_returns_200_with_model` patches `pathsense.routes.analyze.torch` which no longer exists
- `test_health_returns_503_without_model` expects 503 when model missing, but health route now returns 200 unconditionally
- Root cause: Phase 1 pivoted from local Moondream (requires torch + GPU model) to GPT-4o API
- Fix needed: Update test_health.py to match current GPT-4o-based architecture

### test_vision.py failures
- Imports `_run_inference` from `pathsense.services.vision` which was renamed/removed during Phase 1 refactor
- Fix needed: Update test_vision.py to match current vision service API (run_inference_async)

Both issues predated Plan 02-01 and are not caused by TTS changes.
