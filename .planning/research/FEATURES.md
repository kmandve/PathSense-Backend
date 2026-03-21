# Feature Research

**Domain:** Assistive vision API for blind navigation (smart cane backend)
**Researched:** 2026-03-21
**Confidence:** MEDIUM — ecosystem surveyed via WebSearch; latency data from published research; Moondream capabilities from official docs

---

## Feature Landscape

### Table Stakes (Judges Expect These)

These are the features without which the demo fails to convince anyone. Missing even one makes the system feel unfinished.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Image ingestion via HTTP POST | Cane hardware must have a dead-simple integration surface; any other interface adds unnecessary coupling | LOW | FastAPI multipart/form-data upload; synchronous POST |
| Navigation-focused scene description | The core product promise — not "there is a dog" but "medium-sized dog blocking the center of the path, roughly 2 meters ahead" | MEDIUM | Requires careful prompt engineering on top of vision model; Moondream supports natural language prompts for spatial reasoning |
| Obstacle classification (steps, doors, signs, people) | These are the exact hazards users care about; generic scene description is insufficient | MEDIUM | Prompt Moondream with explicit category list; it supports object detection and spatial descriptions |
| Text-to-speech audio output returned in response | Blind users cannot read text; the API must return ready-to-play audio so the cane can pass it directly to headphones | MEDIUM | Piper TTS processes short navigation strings in under 1 second on CPU; keep generated text short (1-3 sentences) to keep synthesis fast |
| Sub-3-second end-to-end latency | Published research shows >500ms audio latency causes dangerous reaction-time gaps while walking; anything over 3s breaks the demo illusion of "real-time" | HIGH | Vision inference + TTS must complete together under target; Moondream on GTX 1650 with CUDA is the critical path |
| Both text and audio in API response | Judges will inspect the JSON — text lets them verify correctness; audio proves the full stack works | LOW | Return `{"description": "...", "audio_base64": "..."}` or multipart response |
| Graceful fallback behavior | If local model fails or produces garbage, the system must still work — GPT-4o as fallback prevents silent failures during the demo | MEDIUM | Implement quality gate: if Moondream confidence is low or response is < N tokens, escalate to GPT-4o |

### Differentiators (Competitive Advantage at Hackathon)

These push the project from "API that works" to "project that wins." Each is achievable in a day given the tech stack.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Fully local inference (no cloud dependency) | Demonstrates deeper technical understanding than cloud-API wrappers; judges at assistive tech hackathons value privacy and offline capability explicitly | MEDIUM | Moondream + Piper = fully local; GPT-4o fallback is the only cloud touch; emphasize this in the demo narrative |
| Navigation-optimized prompt system | Generic captioning describes what's there; navigation prompting describes what matters (proximity, direction, action) — this is the actual hard problem | MEDIUM | "You are a navigation guide. Describe what is directly ahead in one to two sentences. Focus on: obstacles within 3 meters, steps, doors, signs. Be concise. Avoid generic descriptions." |
| Distance / proximity language in descriptions | "Step 2 meters ahead" vs "there is a step" — the former enables the user to act; this is what separates a navigation assistant from a scene captioner | MEDIUM | Moondream's grounded reasoning (2025-06 release) supports spatial relationship reasoning; prompt explicitly for distance estimation |
| Actionable output framing | End descriptions with a directional nudge: "clear on the left, obstacle right" — gives user a decision, not just information | LOW | Prompt engineering only; no additional model work needed |
| Dual output (text + audio) with minimal overhead | Returning both lets the cane hardware choose what to use; text can also be displayed on a companion phone; shows system design thinking | LOW | Already in table stakes; the differentiator is architectural: make it one clean response object, not two calls |
| CUDA-accelerated inference on consumer GPU | Showing VRAM-constrained local inference (4GB GTX 1650) is more technically impressive than using a large cloud model | HIGH | Already required by hardware constraint; frame this in the demo — "runs on hardware a blind user can afford" |

### Anti-Features (Things to Deliberately NOT Build Given Time Constraints)

These sound good, are commonly suggested, and will burn hours without improving the demo.

| Feature | Why Requested | Why Problematic for Hackathon | What to Do Instead |
|---------|---------------|-------------------------------|-------------------|
| Continuous video stream processing | Seems more "real-time" than button-triggered capture | WebSocket streaming + continuous inference exceeds VRAM budget on a 4GB card; adds networking complexity; button-trigger is actually safer for users (no cognitive overload) | Single image per button press — same UX pattern as Seeing AI, Be My Eyes |
| User accounts and session history | "Users might want to replay what the cane saw" | Out of scope, no multi-user concern in demo; adds database, auth, and storage complexity | Process and discard; stateless API |
| Multi-language TTS | Seems inclusive | English Piper voices are tested and fast; adding language detection + multi-voice routing risks latency regressions; not needed for demo | English only; note multilingual as future work in the presentation |
| Object bounding box coordinates in response | API feels more "powerful" with structured spatial data | Cane hardware does nothing with raw coordinates; audio description is the only output channel available to the user | Encode spatial information in natural language: "on your left", "directly ahead", "2 meters" |
| Cloud TTS fallback | "What if Piper sounds bad?" | Piper neural voices are good enough; adding an ElevenLabs or OpenAI TTS call adds a second potential failure point and network latency | Commit to Piper; choose a good English voice (en_US-lessac-medium or en_US-ryan-medium) upfront |
| Fine-tuned model for navigation | "Custom model would be more accurate" | Fine-tuning requires a labeled navigation dataset that doesn't exist and weeks of compute; Moondream + prompt engineering achieves 80% of the benefit in hours | Invest in prompt engineering, not model training |
| Image preprocessing pipeline | Edge detection, depth estimation, semantic segmentation layered before VLM | Adds latency and complexity; modern VLMs like Moondream handle raw images well enough for the demo | Send raw compressed JPEG directly; resize to model's expected input size only |

---

## Feature Dependencies

```
[Image Ingestion via HTTP POST]
    └──requires──> [Vision Model Inference (Moondream)]
                       └──requires──> [Navigation-Optimized Prompt System]
                       └──requires──> [CUDA Acceleration on GTX 1650]
                       └──requires──> [GPT-4o Fallback]
                                          └──requires──> [Quality Gate / Confidence Check]

[Vision Model Inference] ──produces──> [Navigation Scene Description (text)]
    └──feeds──> [Piper TTS Synthesis]
                    └──produces──> [Audio Output (WAV/MP3)]

[Navigation Scene Description] + [Audio Output]
    └──combine into──> [Dual-Output API Response]

[Distance / Proximity Language] ──enhances──> [Navigation-Optimized Prompt System]
[Actionable Output Framing] ──enhances──> [Navigation-Optimized Prompt System]
```

### Dependency Notes

- **Image Ingestion requires Vision Model**: The API endpoint has no value without inference behind it; these ship together.
- **Vision Model requires Navigation Prompt**: Raw Moondream output without a navigation-tuned prompt produces generic scene captions, not navigation guidance. Prompt is not optional.
- **Fallback requires Quality Gate**: Without a heuristic to detect bad Moondream output (too short, generic, or model error), the fallback never triggers correctly. Gate on response token count and/or keyword absence.
- **TTS requires short text input**: Piper stays under 1 second for sentences up to ~25 words. Longer descriptions degrade latency. The prompt system must enforce brevity — this is a dependency in practice.
- **CUDA requires model loaded at startup**: Moondream must be loaded once at server start, not per-request. Cold load on 4GB VRAM takes ~10 seconds. This affects server startup time, not per-request latency.

---

## MVP Definition

### Launch With (v1 — demo tomorrow)

- [ ] HTTP POST endpoint that accepts an image file — why essential: nothing works without this
- [ ] Moondream inference with navigation-focused system prompt — why essential: this is the product's core claim
- [ ] Piper TTS converting description to audio — why essential: audio output is what makes this a navigation tool, not just a captioning tool
- [ ] Dual response: text description + audio (base64 or binary) — why essential: judges will inspect the payload; cane hardware needs both
- [ ] GPT-4o fallback when Moondream fails or underperforms — why essential: demo resilience; cannot afford a live failure
- [ ] End-to-end latency under 3 seconds — why essential: anything slower breaks the "real-time navigation" framing

### Add After Validation (v1.x — post-hackathon)

- [ ] Structured confidence scoring on descriptions — trigger: if fallback fires unexpectedly during demo review
- [ ] Streaming TTS (start playing before full synthesis) — trigger: if latency exceeds 3s under real load
- [ ] Configurable verbosity levels (brief vs detailed) — trigger: user feedback that output length is wrong for walking pace

### Future Consideration (v2+)

- [ ] Continuous capture mode with smart deduplication — why defer: requires WebSocket + frame diffing; way out of scope for hackathon
- [ ] GPS + landmark database integration — why defer: requires map data pipeline and outdoor field testing
- [ ] Fine-tuned navigation VLM — why defer: needs labeled dataset collection first
- [ ] Multi-language support — why defer: Piper multilingual voices work but need testing; English first

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| HTTP POST image ingestion | HIGH | LOW | P1 |
| Navigation-optimized prompt | HIGH | LOW | P1 |
| Moondream CUDA inference | HIGH | MEDIUM | P1 |
| Piper TTS synthesis | HIGH | MEDIUM | P1 |
| Dual text+audio response | HIGH | LOW | P1 |
| GPT-4o fallback | MEDIUM | MEDIUM | P1 |
| Distance/proximity language | HIGH | LOW | P1 |
| Actionable output framing | HIGH | LOW | P1 |
| Quality gate / confidence check | MEDIUM | LOW | P2 |
| Sub-3s latency tuning | HIGH | MEDIUM | P2 |
| Streaming TTS | MEDIUM | HIGH | P3 |
| Continuous video processing | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for demo — ships tomorrow
- P2: Should have — add if time permits after P1 is working
- P3: Nice to have — post-hackathon only

---

## Competitor Feature Analysis

These are the closest reference points in the ecosystem. PathSense differs in being a backend API (not a consumer app) and running fully locally.

| Feature | Microsoft Seeing AI | Be My Eyes (Be My AI) | PathSense (our approach) |
|---------|--------------------|-----------------------|--------------------------|
| Scene description | Yes — "Scenes" channel | Yes — conversational AI descriptions | Yes — navigation-framed, concise |
| Navigation-specific framing | Partial — "World" channel uses spatial audio | No — general purpose description | Yes — explicit prompt: obstacles, steps, doors, signs |
| Proximity / distance language | No — qualitative only | No | Yes — target of prompt engineering |
| Audio output | Yes — TTS built into app | Yes — TTS built into app | Yes — Piper local TTS, returned in response |
| Fully local / offline | No — cloud inference | No — cloud inference | Yes — Moondream + Piper, no cloud required for core path |
| API surface for hardware clients | No — consumer app only | No — consumer app only | Yes — HTTP POST, designed for cane hardware integration |
| Latency target | Unknown — cloud-dependent | Unknown — cloud-dependent | <3s end-to-end on GTX 1650 |
| Fallback / reliability layer | Unknown | Unknown | Yes — GPT-4o when local model underperforms |

---

## Sources

- [Microsoft Seeing AI overview — Microsoft Garage](https://www.microsoft.com/en-us/garage/wall-of-fame/seeing-ai/)
- [Seeing AI Indoor Navigation — AbilityNet](https://abilitynet.org.uk/news-blogs/microsoft-seeing-ai-best-ever-app-blind-people-just-got-even-better)
- [Be My Eyes — OpenAI partnership announcement](https://openai.com/index/be-my-eyes/)
- [Moondream docs — capabilities overview](https://docs.moondream.ai/)
- [Moondream grounded reasoning release (2025-06)](https://moondream.ai/blog/moondream-2025-06-21-release)
- [Real-Time Assistive Navigation for Visually Impaired — arXiv 2025](https://arxiv.org/html/2504.20976v2)
- [AI smart cane technology review — Springer 2025](https://link.springer.com/article/10.1007/s44443-025-00234-9)
- [VisionGPT: LLM-Assisted Real-Time Anomaly Detection for Safe Visual Navigation — arXiv](https://arxiv.org/html/2403.12415v1)
- [Open-source TTS comparison 2025 — Inferless](https://www.inferless.com/learn/comparing-different-text-to-speech---tts--models-part-2)
- [Piper TTS — GitHub](https://github.com/rhasspy/piper)
- [Smart cane hackathon project — GitHub](https://github.com/gd03champ/smart-whitecane-proj-public)

---

*Feature research for: Assistive vision API — blind navigation backend*
*Researched: 2026-03-21*
