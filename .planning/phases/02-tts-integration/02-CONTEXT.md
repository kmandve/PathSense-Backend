# Phase 2: TTS Integration - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Navigation text from the vision service is synthesized into spoken WAV audio locally using Piper TTS on CPU. The TTS service takes a text string and returns WAV bytes. Does NOT include wiring into the HTTP response (Phase 3) or fallback handling (Phase 4).

</domain>

<decisions>
## Implementation Decisions

### TTS Engine
- **D-01:** Use Piper TTS — fully local, no cloud dependency, no API costs. Speed is the top priority.
- **D-02:** Use the `tts-1` speed-optimized approach — pick the fastest Piper voice model available.

### Voice Selection
- **D-03:** Claude's discretion — pick a clear, natural English voice optimized for short navigation phrases. `en_US-lessac-medium` is the research recommendation.

### Audio Format
- **D-04:** Claude's discretion — standard WAV format (16-bit PCM, 22050Hz) for maximum compatibility with headphone playback.

### Integration Pattern
- **D-05:** TTS must not block the FastAPI event loop — use async subprocess or async wrapper.
- **D-06:** Synthesis must complete in under 1 second for navigation-length text (under 15 words).

### Claude's Discretion
- Piper installation method (pip package vs binary)
- Voice model download and caching strategy
- Async subprocess vs thread pool approach
- Error handling for TTS failures
- Temporary file handling vs in-memory WAV generation

</decisions>

<specifics>
## Specific Ideas

- Speed is the absolute top priority — the user emphasized "whatever is fastest, even faster than piper"
- Keep it simple — hackathon demo is today, no time for complex setups

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Stack and Architecture
- `.planning/research/STACK.md` — Piper TTS version, ONNX runtime config, voice model recommendations
- `.planning/research/ARCHITECTURE.md` — TTS service component boundary, async subprocess pattern
- `.planning/research/PITFALLS.md` — Piper subprocess blocking pitfall, WAV format requirements

### Requirements
- `.planning/REQUIREMENTS.md` — TTS-01 (local TTS), TTS-02 (WAV format), TTS-03 (under 1 second)

### Prior Phase
- `.planning/phases/01-foundation/01-CONTEXT.md` — Phase 1 decisions, integration points

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pathsense/services/vision.py` — Pattern for async service wrapper (run_inference_async)
- `pathsense/config.py` — Central config constants

### Established Patterns
- Async service pattern: function does work, async wrapper keeps event loop free
- Services live in `pathsense/services/`

### Integration Points
- Phase 3 will call the TTS service after vision inference, passing the description text
- TTS service returns WAV bytes that Phase 3 will base64-encode into the JSON response

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-tts-integration*
*Context gathered: 2026-03-21*
