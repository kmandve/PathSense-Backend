# Phase 3: HTTP API Layer - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire POST /analyze to run the full pipeline: image upload → GPT-4o vision → Piper TTS → return JSON with text description + base64 audio. Add health check verification that responds during active inference. Does NOT include GPT-4o fallback logic or error hardening (Phase 4).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- All implementation details — this is straightforward integration plumbing
- Response format: `{"description": "...", "audio": "<base64 WAV>"}`
- Pipeline order: vision inference → TTS synthesis → base64 encode → JSON response
- Health check should confirm services are ready, respond during active inference
- Base64 encoding of WAV bytes for JSON transport
- End-to-end latency target: under 3 seconds

</decisions>

<specifics>
## Specific Ideas

No specific requirements — standard integration of existing services.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Current Implementation
- `pathsense/routes/analyze.py` — Existing POST /analyze (returns text only, needs audio field added)
- `pathsense/services/vision.py` — GPT-4o vision service (`run_inference_async`)
- `pathsense/services/tts.py` — Piper TTS service (`synthesize_async`)
- `pathsense/main.py` — Lifespan loads TTS voice into app.state

### Requirements
- `.planning/REQUIREMENTS.md` — API-01 (text + audio response), API-02 (base64 audio), API-03 (under 3 seconds)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pathsense/routes/analyze.py` — Already has image upload, validation, vision inference. Just needs TTS + audio in response.
- `pathsense/services/tts.py` — `synthesize_async(voice, text) -> bytes` ready to use
- `pathsense/services/vision.py` — `run_inference_async(image) -> str` ready to use

### Established Patterns
- Async services with `run_in_executor` for CPU/GPU-bound work
- `app.state` for sharing loaded models across requests

### Integration Points
- Route calls `run_inference_async(img)` → gets description text
- Route calls `synthesize_async(app.state.tts_voice, description)` → gets WAV bytes
- Route base64-encodes WAV bytes → returns `{"description": text, "audio": b64}`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-http-api-layer*
*Context gathered: 2026-03-21*
