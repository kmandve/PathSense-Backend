# PathSense

## What This Is

A backend API that receives images from a smart cane device, analyzes them using a local vision model, and returns concise, navigation-focused descriptions optimized for blind users. The response includes both text and synthesized audio so headphones can play the guidance immediately. Built for a hackathon demo.

## Core Value

A blind user presses a button, and within seconds hears a clear, actionable description of what's directly ahead — obstacles, doors, steps, signs — so they can navigate safely.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] API endpoint accepts image upload via HTTP POST
- [ ] Local vision model (Moondream) analyzes image and produces navigation-focused text description
- [ ] GPT-4o fallback when local model quality is insufficient or unavailable
- [ ] Descriptions are concise, actionable, and navigation-oriented (obstacles, doors, signs, steps)
- [ ] Local TTS (Piper) converts description text to spoken audio
- [ ] API returns both text description and audio file in response
- [ ] Runs on NVIDIA GTX 1650 (4GB VRAM) with CUDA acceleration
- [ ] Response time is fast enough for real-time navigation use

### Out of Scope

- Smart cane hardware/firmware — separate build, tomorrow
- Client-side app or UI — cane sends HTTP requests directly
- User accounts or authentication — hackathon demo, no multi-user concerns
- Continuous video stream processing — single image per button press
- Cloud TTS — fully local audio generation
- Multi-language support — English only for demo
- Image storage or history — process and discard

## Context

- **Hackathon project** — demo is tomorrow, so speed of development is critical
- **Smart cane integration** — the cane will be built separately and will POST images to this API
- **Hardware constraint** — GTX 1650 with 4GB VRAM limits model size; Moondream (1.6B params, ~3GB VRAM) fits well
- **RTX 4070 available** as backup hardware but prefer not to use it
- **Audio playback** — headphones connected to the cane/phone will play the TTS output
- **Navigation focus** — descriptions should prioritize what matters for safe movement: obstacles, distances, terrain changes, doors, signs

## Constraints

- **Hardware**: GTX 1650 (4GB VRAM) — models must fit within this; Moondream is the target
- **Timeline**: Demo tomorrow — must be functional by then
- **Latency**: Response must be fast enough to be useful in real-time navigation (target < 3 seconds)
- **VRAM**: ~3GB for vision model + overhead for TTS, must coexist on 4GB GPU

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Moondream over LLaVA/BLIP-2 | Fits in 4GB VRAM, purpose-built for fast visual Q&A | — Pending |
| GPT-4o as fallback, not primary | Local model impresses judges more, shows deeper technical understanding | — Pending |
| Piper for TTS | Fast, local, no API dependency — keeps entire stack self-contained | — Pending |
| FastAPI over Flask | Better async support, auto-generated docs, modern Python patterns | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-21 after initialization*
