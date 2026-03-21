# Roadmap: PathSense

## Overview

PathSense is a four-phase build that moves risk-first: prove the GPU model loads within VRAM budget before writing any HTTP code, prove audio synthesis works before exposing the endpoint, then wrap the proven pipeline in a thin FastAPI layer, and finally harden it with a GPT-4o fallback so the demo survives local model failure. Each phase leaves a fully testable artifact. The demo is ready when Phase 4 completes.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - GPU model loads, image ingested, navigation-focused text produced
- [ ] **Phase 2: TTS Integration** - Navigation text converted to spoken WAV audio locally
- [ ] **Phase 3: HTTP API Layer** - Full POST /analyze endpoint returns text + audio in one response
- [ ] **Phase 4: Fallback and Hardening** - GPT-4o fallback, quality gate, and safe error path protect the demo

## Phase Details

### Phase 1: Foundation
**Goal**: The vision service runs on the GTX 1650, stays within VRAM budget, and produces navigation-focused descriptions in the correct format
**Depends on**: Nothing (first phase)
**Requirements**: INF-01, INF-02, INF-03, INF-04, IMG-01, IMG-02, IMG-03, VIS-01, VIS-02, VIS-03, VIS-04, VIS-05, VIS-06, VIS-07
**Success Criteria** (what must be TRUE):
  1. Moondream 4-bit model loads at startup and nvidia-smi shows VRAM usage below 3GB after warmup
  2. A test image posted to the vision service returns a description that names at least one of: obstacle, door, step, sign, person
  3. Descriptions include distance or direction language ("ahead", "left", "right", "meters")
  4. Descriptions are under 15 words and end with a directional framing ("clear path", "obstacle right")
  5. 20 sequential inference calls complete without OOM error or VRAM growth
**Plans:** 1/3 plans executed

Plans:
- [x] 01-01-PLAN.md — Project scaffold, dependencies, FastAPI app with lifespan model loading, health check, test infrastructure
- [ ] 01-02-PLAN.md — Vision service with navigation prompt (D-01..D-06), inference function, run_in_executor wiring
- [ ] 01-03-PLAN.md — POST /analyze endpoint with image validation, integration tests, soak test (20 sequential inferences)

### Phase 2: TTS Integration
**Goal**: Navigation text produced by Phase 1 is synthesized into spoken WAV audio locally on CPU in under 1 second
**Depends on**: Phase 1
**Requirements**: TTS-01, TTS-02, TTS-03
**Success Criteria** (what must be TRUE):
  1. Piper TTS converts a 15-word navigation description to WAV bytes without blocking the event loop
  2. The output WAV file plays audibly through headphones (standard 16-bit PCM, 22050Hz)
  3. Synthesis completes in under 1 second measured from text input to WAV bytes returned
**Plans**: TBD

Plans:
- [ ] 02-01: Piper TTS service with async subprocess, WAV output, and latency measurement

### Phase 3: HTTP API Layer
**Goal**: A single POST /analyze endpoint accepts an image, runs the full local pipeline, and returns text description plus base64 audio in one JSON response under 3 seconds
**Depends on**: Phase 2
**Requirements**: API-01, API-02, API-03
**Success Criteria** (what must be TRUE):
  1. POST /analyze with a JPEG image returns {"description": "...", "audio": "<base64>"} with HTTP 200
  2. The base64 audio field decodes to a playable WAV file
  3. End-to-end response time from image upload to JSON response is under 3 seconds on GTX 1650
  4. GET /health returns a response confirming model is loaded and GPU is available, even during active inference
**Plans**: TBD

Plans:
- [ ] 03-01: Route wiring (UploadFile ingestion, lifespan model sharing, pipeline orchestration, JSON response builder)
- [ ] 03-02: Health check endpoint and event-loop non-blocking verification

### Phase 4: Fallback and Hardening
**Goal**: The API survives local model failure and demo conditions — GPT-4o takes over when Moondream output is bad, and every failure path returns a safe message instead of hanging
**Depends on**: Phase 3
**Requirements**: FBK-01, FBK-02, FBK-03, FBK-04
**Success Criteria** (what must be TRUE):
  1. When Moondream returns output shorter than 5 words or produces an error, GPT-4o is called automatically
  2. The GPT-4o fallback path produces a valid navigation description within 5 seconds
  3. If both local model and GPT-4o fail, the API returns a safe message ("Unable to analyze scene") with HTTP 200 — no hang, no crash
  4. Disabling the local model and sending a real image triggers the fallback path and returns audio
**Plans**: TBD

Plans:
- [ ] 04-01: GPT-4o fallback with quality gate, asyncio timeout, and safe default response

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 1/3 | In Progress|  |
| 2. TTS Integration | 0/1 | Not started | - |
| 3. HTTP API Layer | 0/2 | Not started | - |
| 4. Fallback and Hardening | 0/1 | Not started | - |
