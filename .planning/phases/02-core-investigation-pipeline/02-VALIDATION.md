---
phase: 02
slug: core-investigation-pipeline
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-24
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.24 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (asyncio_mode = "auto") |
| **Quick run command** | `.venv/bin/pytest tests/ -x -q --tb=short -m "not integration"` |
| **Full suite command** | `.venv/bin/pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds (unit), ~15 seconds (full with integration) |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/pytest tests/ -x -q --tb=short -m "not integration"`
- **After every plan wave:** Run `.venv/bin/pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Test File | Status |
|---------|------|------|-------------|-----------|-------------------|-----------|--------|
| 02-01-01 | 01 | 1 | ENGN-07 | unit | `.venv/bin/pytest tests/test_prediction.py -x` | tests/test_prediction.py | ⬜ pending |
| 02-02-01 | 02 | 2 | PIPE-01, PIPE-07 | unit | `.venv/bin/pytest tests/test_payment_agent.py -x` | tests/test_payment_agent.py | ⬜ pending |
| 02-03-01 | 03 | 2 | PIPE-03, PIPE-04, PIPE-05, PIPE-06 | unit | `.venv/bin/pytest tests/test_sub_agents.py -x` | tests/test_sub_agents.py | ⬜ pending |
| 02-04-01 | 04 | 2 | ENGN-01..06 | unit | `.venv/bin/pytest tests/test_safety_gate.py -x` | tests/test_safety_gate.py | ⬜ pending |
| 02-05-01 | 05 | 2 | MEM-01, MEM-03, MEM-04 | unit | `.venv/bin/pytest tests/test_memory_stores.py -x` | tests/test_memory_stores.py | ⬜ pending |
| 02-06-01 | 06 | 3 | PIPE-02, API-01, API-02 | unit | `.venv/bin/pytest tests/test_api.py tests/test_supervisor.py -x` | tests/test_api.py, tests/test_supervisor.py | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_prediction.py` — created by Plan 02-01, Task 2 (TDD)
- [ ] `tests/test_payment_agent.py` — created by Plan 02-02, Task 2
- [ ] `tests/test_sub_agents.py` — created by Plan 02-03, Task 2 (covers risk, compliance, forensics)
- [ ] `tests/test_safety_gate.py` — created by Plan 02-04, Task 2 (TDD)
- [ ] `tests/test_memory_stores.py` — created by Plan 02-05, Task 2 (covers episode and trust stores)
- [ ] `tests/test_api.py` — created by Plan 02-06, Task 3
- [ ] `tests/test_supervisor.py` — created by Plan 02-06, Task 3 (supervisor behavioral tests)

*Existing infrastructure covers framework install: pytest 8.x, pytest-asyncio 0.24, asyncio_mode=auto.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Payment Agent genuinely manipulated by hidden text | PIPE-07 | Requires live LLM call; output varies | Send attack fixture, verify agent claims differ from ground truth |
| Forensics vision detects hidden text in PNG | PIPE-05 | Requires live Claude vision API | Send invoice_forensic.png, verify hidden_text_detected in response |
| WebSocket events received in browser | API-01 | Requires browser or ws client | Connect to /ws, trigger investigation, verify event sequence |
| Supervisor Opus 4.6 reasoning quality | D-03 | Requires live LLM call | Trigger investigation, verify supervisor makes meaningful decisions |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Test file names match actual plan outputs
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
