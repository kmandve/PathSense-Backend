# Deferred Items — Phase 03

## Pre-existing Broken Tests (Out of Scope)

Discovered during plan 03-01 execution. These test files reference symbols from the old
Moondream-based design that no longer exist in the current codebase. They were failing
before this plan began.

### tests/test_startup.py
- **Issue:** Imports `MODEL_ID, TOKENIZER_ID, TOKENIZER_REVISION` from `pathsense.config` — these constants no longer exist since the architecture switched to GPT-4o
- **Status:** Pre-existing failure, not introduced by this plan
- **Fix:** Update or remove these tests in a future plan when the GPT-4o integration is hardened

### tests/test_vision.py
- **Issue:** Imports `_run_inference` from `pathsense.services.vision` — this private function no longer exists since vision.py was rewritten for GPT-4o
- **Also:** Tests `NAVIGATION_PROMPT` content for keywords ("nearest", "D-03", etc.) that match the old Moondream prompt, not the current GPT-4o prompt
- **Status:** Pre-existing failure, not introduced by this plan
- **Fix:** Rewrite vision tests to mock the GPT-4o client and test the new GPT-4o-based `run_inference_async` in a future plan
