---
status: partial
phase: 01-foundation
source: [01-VERIFICATION.md]
started: 2026-03-21T00:00:00Z
updated: 2026-03-21T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. VRAM budget stays below 3GB on GTX 1650
expected: Run `uvicorn pathsense.main:app --host 0.0.0.0 --port 8000 --workers 1` on GTX 1650, then check `nvidia-smi`. VRAM should be below 3GB. GET /health should report `vram_reserved_mb` under 3000.
result: [pending]

### 2. Real inference produces navigation-focused output
expected: POST an actual photograph to /analyze. Moondream output should be under 15 words, use relative distance words (not numeric), and end with directional framing.
result: [pending]

### 3. VRAM stability over 20 sequential requests
expected: Run 20 real inferences with `watch -n1 nvidia-smi` monitoring. VRAM should not grow across requests thanks to `torch.cuda.empty_cache()`.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
