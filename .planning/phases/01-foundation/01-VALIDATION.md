---
phase: 1
slug: foundation
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-24
updated: 2026-03-24
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml or pytest.ini — Plan 01 installs |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | INFRA-01, INFRA-05 | smoke | `python -c "import sentinel, aerospike, fastapi"` | N/A (import check) | pending |
| 1-02-01 | 02 | 1 | INFRA-02 | config | `grep "namespace sentinel" aerospike.conf` | N/A | pending |
| 1-02-02 | 02 | 1 | INFRA-02 | integration | `python -m pytest tests/test_infra.py::test_aerospike -x -q` | tests/test_infra.py | pending |
| 1-03-01 | 03 | 1 | INFRA-04 | smoke | `cd frontend && npx vite build` | N/A | pending |
| 1-03-02 | 03 | 1 | INFRA-04 | unit | `python -m pytest tests/test_infra.py::test_frontend_build -x -q` | tests/test_infra.py | pending |
| 1-04-01 | 04 | 2 | DEMO-03 | unit | `python -m pytest tests/test_fixtures.py -x -q` | tests/test_fixtures.py | pending |
| 1-04-02 | 04 | 2 | INFRA-03 | integration | `python -m pytest tests/test_claude_api.py -x -q` | tests/test_claude_api.py | pending |
| 1-05-01 | 05 | 2 | SCHEMA-01..04 | unit | `python -m pytest tests/test_schemas.py -x -q` | tests/test_schemas.py (Wave 0: created as Task 1 before implementation) | pending |
| 1-05-02 | 05 | 2 | SCHEMA-01..04 | unit | `python -m pytest tests/test_schemas.py -v` | tests/test_schemas.py | pending |

*Status: pending | green | red | flaky*

---

## Wave 0 Requirements

Wave 0 test stubs are created BEFORE implementation in TDD plans:

- [x] `tests/test_schemas.py` — Created as Plan 05, Task 1 (before schema implementation in Task 2)
- [x] `tests/test_infra.py` — Created by Plan 02 (Aerospike tests) and Plan 03 (frontend build test)
- [x] `tests/test_fixtures.py` — Created as part of Plan 04, Task 1
- [x] `tests/test_claude_api.py` — Created as Plan 04, Task 2
- [x] `tests/conftest.py` — Created by Plan 01, Task 1
- [x] `pip install pytest pytest-asyncio` — Installed via pyproject.toml dev deps in Plan 01

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker Desktop installed and running | INFRA-02 | Requires GUI/system install, not automatable | Open Docker Desktop; verify `docker ps` exits 0 |
| Aerospike namespace visible in logs | INFRA-02 | Log inspection required | Run `docker logs aerospike` and confirm namespace appears |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter
- [x] INFRA-03 test_anthropic_api_key_present is non-skippable (fails hard if key missing)
- [x] INFRA-04 has pytest test (test_frontend_build via subprocess)
- [x] TDD order correct: Plan 05 Task 1 creates tests, Task 2 implements schemas

**Approval:** pending
