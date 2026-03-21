# Phase 1: Foundation - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

The vision service runs on the GTX 1650, stays within VRAM budget, and produces navigation-focused descriptions in the correct format. Delivers: FastAPI app skeleton with lifespan model loading, Moondream 4-bit inference on CUDA, image ingestion with validation, and a navigation-optimized prompt. Does NOT include TTS, audio output, or GPT-4o fallback — those are later phases.

</domain>

<decisions>
## Implementation Decisions

### Navigation Prompt Design
- **D-01:** Tone is calm guidance — informative but not alarming. Example: "There's a step down nearby, clear on the left." NOT urgent commands like "Stop. Step down."
- **D-02:** When multiple objects are present, always lead with the nearest hazard first. Closest danger gets mentioned before anything further away.
- **D-03:** Distance uses relative words only: "close", "nearby", "far ahead". No numeric estimates (no "2 meters") — avoids false precision from a vision model that can't measure distance.
- **D-04:** When the path is clear, still describe the scene with spatial context: "Open hallway, clear path ahead" or "Wide sidewalk, no obstacles nearby." Don't just say "Clear."
- **D-05:** Output must be 1-2 short sentences, under 15 words total. Prioritize: obstacles, doors, steps, signs, people.
- **D-06:** End descriptions with directional framing when relevant: "clear on the left", "obstacle on the right."

### Project Structure
- **D-07:** Claude's discretion — standard Python project layout with `services/`, `routes/`, `main.py` entry point as suggested by research architecture.

### Image Handling
- **D-08:** Claude's discretion — accept JPEG/PNG, validate content type, resize to model input dimensions. Reject anything else with a clear error.

### Error Behavior
- **D-09:** Claude's discretion — return meaningful HTTP error responses for bad uploads. For inference failures in this phase, return a 500 with a message (fallback handling is Phase 4).

### Claude's Discretion
- Project scaffold and dependency pinning (versions from research STACK.md)
- FastAPI lifespan handler and model loading pattern
- `run_in_executor` wiring for non-blocking inference
- `torch.cuda.empty_cache()` placement for VRAM management
- Health check endpoint implementation
- Image resize dimensions and preprocessing

</decisions>

<specifics>
## Specific Ideas

- The prompt should produce output that sounds natural when read aloud by TTS — conversational English, not terse labels
- Example good output: "Doorway close ahead, slightly to the left. Clear path through."
- Example bad output: "DOOR. LEFT. OBSTACLE: NONE."
- The "calm guidance" tone is important for user trust — the cane should feel like a helpful companion, not an alarm system

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Stack and Architecture
- `.planning/research/STACK.md` — Specific library versions, install commands, and compatibility notes for GTX 1650
- `.planning/research/ARCHITECTURE.md` — Component boundaries, data flow, GPU memory budget, lifespan singleton pattern
- `.planning/research/PITFALLS.md` — VRAM overflow prevention, event loop blocking, VRAM fragmentation mitigation

### Requirements
- `.planning/REQUIREMENTS.md` — INF-01..04 (infrastructure), IMG-01..03 (image ingestion), VIS-01..07 (vision analysis)

### Project Context
- `.planning/PROJECT.md` — Core value, constraints, key decisions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, Phase 1 creates the initial codebase

### Established Patterns
- None yet — this phase establishes the patterns all subsequent phases follow

### Integration Points
- Phase 2 (TTS) will consume the text string returned by the vision service
- Phase 3 (HTTP API) will wrap the vision service in the FastAPI route
- Phase 4 (Fallback) will add GPT-4o as an alternative path in the vision service

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-03-21*
