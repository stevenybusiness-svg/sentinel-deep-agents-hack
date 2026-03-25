---
phase: 3
slug: self-improvement-loop
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio |
| **Config file** | `pytest.ini` (existing) |
| **Quick run command** | `pytest tests/test_rule_generator.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_rule_generator.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | LEARN-02 | unit | `pytest tests/test_rule_generator.py::test_validation_harness -x -q` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | LEARN-01 | unit | `pytest tests/test_rule_generator.py::test_rule_generation_prompt -x -q` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | LEARN-03 | unit | `pytest tests/test_rule_generator.py::test_retry_with_error_context -x -q` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | MEM-02 | unit | `pytest tests/test_rule_store.py -x -q` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | LEARN-03 | unit | `pytest tests/test_rule_generator.py::test_deploy_writes_py_file -x -q` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 2 | API-03 | unit | `pytest tests/test_confirm_route.py -x -q` | ❌ W0 | ⬜ pending |
| 03-04-01 | 04 | 3 | LEARN-04 | unit | `pytest tests/test_rule_generator.py::test_generated_rule_fires_on_attack2 -x -q` | ❌ W0 | ⬜ pending |
| 03-05-01 | 05 | 3 | LEARN-05 | unit | `pytest tests/test_rule_generator.py::test_rule_evolution -x -q` | ❌ W0 | ⬜ pending |
| 03-05-02 | 05 | 3 | LEARN-06 | unit | `pytest tests/test_rule_generator.py::test_evolved_rule_replaces_v1 -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_rule_generator.py` — stubs for LEARN-01 through LEARN-06
- [ ] `tests/test_rule_store.py` — stubs for MEM-02 (Aerospike rule storage)
- [ ] `tests/test_confirm_route.py` — stubs for API-03 (confirm endpoint + latency)

*Existing `tests/conftest.py` has fixtures for Aerospike mocks and VerdictBoard fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| WebSocket streaming shows rule tokens in real time | LEARN-03 | Requires live WebSocket client and dashboard UI | Run `POST /investigate` (phase1 scenario), then `POST /confirm`, observe dashboard rule panel for streaming Python code |
| Generated rule attribution string exact match | LEARN-04 | Attribution string assembly requires live composite scoring | Trigger phase2 scenario after rule deployed, verify gate rationale contains `"Blocked by Generated Rule #001"` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
