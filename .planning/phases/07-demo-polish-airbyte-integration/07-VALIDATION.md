---
phase: 7
slug: demo-polish-airbyte-integration
status: active
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-27
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend) + grep-based structural verify + manual browser verification (frontend) |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `python -m pytest tests/ -q --timeout=60` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `python -m pytest tests/ -q --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 07-01-01 | 01 | 1 | DEMO-POLISH-01, DEMO-POLISH-05 | structural | `grep -n "invoice_clean.png" sentinel/api/main.py && grep -n "Attack 1:" frontend/src/App.jsx && ! grep "Run Attack" frontend/src/App.jsx` | pending |
| 07-01-02 | 01 | 1 | DEMO-POLISH-03 | structural | `grep -n "setEdgeActive" frontend/src/store.js && grep -c "setEdgeActive" frontend/src/hooks/useWebSocket.js` | pending |
| 07-02-01 | 02 | 2 | DEMO-POLISH-02, DEMO-POLISH-04 | integration | `python -m pytest tests/test_airbyte_slack.py -x -q` | pending |
| 07-02-02 | 02 | 2 | DEMO-POLISH-04 | structural | `grep "AirbyteReportPanel" frontend/src/App.jsx && ! grep -i "voiceCall" frontend/src/store.js` | pending |
| 07-03-01 | 03 | 3 | DEMO-POLISH-06 | structural | `grep "ForensicIntroScreen" frontend/src/App.jsx && grep "handleAttack1()" frontend/src/App.jsx` | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [x] `tests/test_airbyte_slack.py` — created as Step 0 of Plan 02, Task 1 (test-first)
- [x] Slack webhook URL in `.env.example` — created in Plan 02, Task 1, Step 6
- [x] PyAirbyte added to requirements.txt — created in Plan 02, Task 1, Step 1

*All Wave 0 items are handled within Plan 02 Task 1 before implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Automated Proxy |
|----------|-------------|------------|-----------------|
| Attack buttons show correct labels | DEMO-POLISH-05 | UI text change | `grep "Attack 1:" frontend/src/App.jsx` (structural) |
| Edge animations light up during investigation | DEMO-POLISH-03 | Visual animation timing — inherently visual, no automated behavioral test possible | `grep "setEdgeActive" frontend/src/store.js` (structural proxy) |
| Intro screen shows forensic comparison first | DEMO-POLISH-06 | UX flow | `grep "showIntro" frontend/src/App.jsx` (structural) |
| Images render in forensic scan panel | DEMO-POLISH-01 | Visual rendering | `grep "invoice_clean.png" sentinel/api/main.py` (route exists) |

**Note:** Edge animations (DEMO-POLISH-03) are inherently visual. Manual-only coverage is accepted for this requirement — grep for `setEdgeActive` confirms the code path exists but animation timing/color can only be verified visually.

---

## Validation Sign-Off

- [x] All tasks have automated verify or accepted manual-only coverage
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (test stubs created in Plan 02 Task 1 Step 0)
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (hackathon-pragmatic — structural grep + pytest for backend, manual-only accepted for visual/animation requirements)
