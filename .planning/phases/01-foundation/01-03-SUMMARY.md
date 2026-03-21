---
phase: 01-foundation
plan: 03
subsystem: api
tags: [fastapi, image-upload, validation, integration-tests, soak-test]
dependency_graph:
  requires: ["01-01", "01-02"]
  provides: ["POST /analyze endpoint", "image upload validation", "inference integration"]
  affects: ["pathsense/routes/analyze.py", "tests/"]
tech_stack:
  added: ["python-multipart (UploadFile multipart parsing)"]
  patterns: ["fail-fast content-type validation before byte read", "PIL decode validates actual image data", "single read() call avoids UploadFile double-read pitfall"]
key_files:
  created:
    - tests/test_analyze.py
    - tests/test_soak.py
  modified:
    - pathsense/routes/analyze.py
    - tests/conftest.py
decisions:
  - "Content-type validated before reading bytes to fail fast and avoid unnecessary I/O"
  - "PIL Image.open catches corrupt data regardless of content-type header"
  - "Model None check returns 503 consistent with /health endpoint behavior"
  - "Inference exceptions return 500 with detail; fallback strategy deferred to Phase 4"
metrics:
  duration: "85 seconds"
  completed_date: "2026-03-21"
  tasks_completed: 2
  files_created: 2
  files_modified: 2
requirements_covered: [IMG-01, IMG-02, IMG-03, VIS-03]
---

# Phase 01 Plan 03: POST /analyze Endpoint and Tests Summary

## One-liner

Wired POST /analyze to accept JPEG/PNG multipart uploads, validate format, PIL-decode, run Moondream inference via run_inference_async, and return {"description": "..."}; 28-test suite including 20-call soak test all green.

## What Was Built

The POST /analyze endpoint completes Phase 1's HTTP surface. Images are validated at two layers: content-type header (415 for unsupported types) and PIL decode (400 for corrupt data). Valid images are passed to the vision service which handles resizing and GPU inference. The endpoint accesses the model via `request.app.state.vision_model` — the same lifecycle pattern established in Plan 01-01.

Integration tests cover all error paths (415, 400, 500, 503) and the happy paths (JPEG and PNG). The soak test runs 20 sequential POST /analyze calls with a mock model to verify no state leaks or async issues.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | POST /analyze endpoint with image validation | cd29e33 | pathsense/routes/analyze.py, tests/conftest.py |
| 2 | Integration tests and soak test | 4ecaa0f | tests/test_analyze.py, tests/test_soak.py |

## Verification Results

- `python -m pytest tests/ -x -q` → 28 passed (health, startup, vision, analyze, soak)
- POST /analyze with valid JPEG → 200 + {"description": "Doorway close ahead, clear path through."}
- POST /analyze with text/plain → 415
- POST /analyze with corrupt JPEG → 400
- 20 sequential POST /analyze calls → all 200, no errors

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] python-multipart not installed in dev environment**
- **Found during:** Task 1 verification
- **Issue:** FastAPI raises RuntimeError when defining UploadFile routes without python-multipart installed
- **Fix:** Ran `pip install python-multipart`; package was already in requirements.txt
- **Files modified:** None (environment-only fix)
- **Commit:** N/A

## Known Stubs

None. The endpoint is fully wired: multipart upload → PIL decode → ThreadPoolExecutor inference → JSON response. The mock model in tests returns a real string, not a placeholder.

## Key Decisions

1. Content-type validated before `await file.read()` — fail fast, avoid unnecessary byte I/O
2. Single `await file.read()` call — UploadFile double-read returns empty bytes (Pitfall 4 from RESEARCH.md)
3. PIL `Image.open(io.BytesIO(...)).convert("RGB")` — catches corrupt data and normalizes color mode for Moondream
4. Model None → 503 — consistent with /health endpoint; model lifecycle managed by main.py lifespan
5. Inference exceptions → 500 with detail — GPT-4o fallback deferred to Phase 4 per plan

## Self-Check: PASSED
