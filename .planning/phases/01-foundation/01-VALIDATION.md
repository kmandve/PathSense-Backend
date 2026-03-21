---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds (includes model inference) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | INF-01 | unit | `pytest tests/test_app.py -k startup` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | INF-02 | unit | `pytest tests/test_app.py -k lifespan` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | VIS-01 | integration | `pytest tests/test_vision.py -k vram` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | VIS-02, VIS-03 | integration | `pytest tests/test_vision.py -k inference` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 2 | IMG-01, IMG-02 | unit | `pytest tests/test_ingestion.py -k upload` | ❌ W0 | ⬜ pending |
| 01-03-02 | 03 | 2 | VIS-04, VIS-05, VIS-06 | integration | `pytest tests/test_vision.py -k prompt` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures (test images, mock model if needed)
- [ ] `tests/test_app.py` — app startup and lifespan stubs
- [ ] `tests/test_vision.py` — vision service inference stubs
- [ ] `tests/test_ingestion.py` — image upload validation stubs
- [ ] `pytest` — install as dev dependency

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| VRAM stays below 3GB after warmup | VIS-01 | Requires nvidia-smi on actual GPU hardware | Run `nvidia-smi` after model loads; verify VRAM < 3GB |
| 20 sequential inferences without OOM | INF-03 | Requires sustained GPU load over time | Run soak test script; monitor VRAM with nvidia-smi |
| Health check responds during inference | INF-04 | Requires concurrent requests to verify event loop | curl /health while inference is running |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
