---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml or pytest.ini — Wave 0 installs |
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
| 1-01-01 | 01 | 1 | SCHEMA-01 | unit | `python -m pytest tests/test_schemas.py -x -q` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | SCHEMA-02 | unit | `python -m pytest tests/test_schemas.py -x -q` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | SCHEMA-03 | unit | `python -m pytest tests/test_schemas.py -x -q` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | SCHEMA-04 | unit | `python -m pytest tests/test_schemas.py -x -q` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | INFRA-01 | integration | `python -m pytest tests/test_infra.py::test_aerospike -x -q` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 1 | INFRA-02 | integration | `python -m pytest tests/test_infra.py::test_aerospike_health -x -q` | ❌ W0 | ⬜ pending |
| 1-02-03 | 02 | 1 | INFRA-03 | integration | `python -m pytest tests/test_infra.py::test_claude_api -x -q` | ❌ W0 | ⬜ pending |
| 1-02-04 | 02 | 1 | INFRA-04 | smoke | `python -m pytest tests/test_infra.py::test_frontend_build -x -q` | ❌ W0 | ⬜ pending |
| 1-02-05 | 02 | 1 | INFRA-05 | unit | `python -m pytest tests/test_infra.py::test_env_config -x -q` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 2 | DEMO-03 | unit | `python -m pytest tests/test_fixtures.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_schemas.py` — stubs for SCHEMA-01, SCHEMA-02, SCHEMA-03, SCHEMA-04
- [ ] `tests/test_infra.py` — stubs for INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05
- [ ] `tests/test_fixtures.py` — stubs for DEMO-03
- [ ] `tests/conftest.py` — shared fixtures (env loading, Aerospike client setup)
- [ ] `pip install pytest pytest-asyncio` — if not already present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker Desktop installed and running | INFRA-02 | Requires GUI/system install, not automatable | Open Docker Desktop; verify `docker ps` exits 0 |
| Aerospike namespace visible in logs | INFRA-02 | Log inspection required | Run `docker logs aerospike` and confirm namespace appears |
| prompt caching headers present in Claude API response | INFRA-03 | Requires live API call inspection | Call Claude API and inspect response.usage for cache_read_input_tokens > 0 on second call |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
