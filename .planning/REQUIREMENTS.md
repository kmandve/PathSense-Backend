# Requirements: PathSense

**Defined:** 2026-03-21
**Core Value:** A blind user presses a button and within seconds hears a clear, actionable description of what's directly ahead

## v1 Requirements

### Image Ingestion

- [ ] **IMG-01**: API accepts image upload via HTTP POST (multipart/form-data)
- [ ] **IMG-02**: API validates uploaded file is a supported image format (JPEG, PNG)
- [ ] **IMG-03**: API resizes image to model's expected input dimensions before inference

### Vision Analysis

- [ ] **VIS-01**: Moondream2 4-bit quantized model loads on GTX 1650 within 4GB VRAM budget
- [ ] **VIS-02**: Model analyzes image and produces navigation-focused text description
- [ ] **VIS-03**: Descriptions identify obstacles, doors, steps, signs, and people
- [ ] **VIS-04**: Descriptions include distance/proximity language ("2 meters ahead", "on your left")
- [ ] **VIS-05**: Descriptions end with actionable directional framing ("clear left, obstacle right")
- [ ] **VIS-06**: Output is constrained to 1-2 short sentences (under 15 words target)
- [ ] **VIS-07**: Navigation-optimized system prompt drives description quality

### Text-to-Speech

- [ ] **TTS-01**: Piper TTS converts description text to spoken audio locally on CPU
- [ ] **TTS-02**: Audio output is in a standard format (WAV) playable by headphones
- [ ] **TTS-03**: TTS synthesis completes in under 1 second for navigation-length text

### API Response

- [ ] **API-01**: Response includes both text description and audio data
- [ ] **API-02**: Audio is returned as base64-encoded string in JSON response
- [ ] **API-03**: End-to-end response time is under 3 seconds (image in → text + audio out)

### Fallback

- [ ] **FBK-01**: GPT-4o is called when local model fails or produces low-quality output
- [ ] **FBK-02**: Quality gate detects bad Moondream output (too short, too generic, model error)
- [ ] **FBK-03**: GPT-4o fallback has a timeout to prevent hanging (5 second max)
- [ ] **FBK-04**: If both local and fallback fail, API returns a safe error message

### Infrastructure

- [ ] **INF-01**: FastAPI server with single uvicorn worker (VRAM constraint)
- [ ] **INF-02**: Models load once at startup via lifespan handler, not per-request
- [ ] **INF-03**: CUDA acceleration enabled for vision model inference
- [ ] **INF-04**: Health check endpoint confirms model is loaded and GPU is available

## v2 Requirements

### Enhanced Navigation

- **NAV-01**: Continuous video stream processing for real-time updates
- **NAV-02**: Multi-language TTS support
- **NAV-03**: Scene comparison between consecutive images (what changed)

### Platform

- **PLT-01**: Docker containerization for deployment
- **PLT-02**: API rate limiting and authentication
- **PLT-03**: Image history logging for debugging

## Out of Scope

| Feature | Reason |
|---------|--------|
| Smart cane hardware/firmware | Separate build, different timeline |
| Client-side app or UI | Cane sends HTTP requests directly |
| User accounts/authentication | Hackathon demo, single user |
| Cloud TTS (ElevenLabs, OpenAI) | Fully local audio generation; Piper is sufficient |
| Fine-tuned navigation model | Requires labeled dataset and weeks of compute; prompt engineering achieves 80% of benefit |
| Object bounding box coordinates | User receives audio only; spatial info encoded in natural language |
| Image preprocessing pipeline | Moondream handles raw images well enough |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| IMG-01 | — | Pending |
| IMG-02 | — | Pending |
| IMG-03 | — | Pending |
| VIS-01 | — | Pending |
| VIS-02 | — | Pending |
| VIS-03 | — | Pending |
| VIS-04 | — | Pending |
| VIS-05 | — | Pending |
| VIS-06 | — | Pending |
| VIS-07 | — | Pending |
| TTS-01 | — | Pending |
| TTS-02 | — | Pending |
| TTS-03 | — | Pending |
| API-01 | — | Pending |
| API-02 | — | Pending |
| API-03 | — | Pending |
| FBK-01 | — | Pending |
| FBK-02 | — | Pending |
| FBK-03 | — | Pending |
| FBK-04 | — | Pending |
| INF-01 | — | Pending |
| INF-02 | — | Pending |
| INF-03 | — | Pending |
| INF-04 | — | Pending |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 0
- Unmapped: 24 ⚠️

---
*Requirements defined: 2026-03-21*
*Last updated: 2026-03-21 after initial definition*
