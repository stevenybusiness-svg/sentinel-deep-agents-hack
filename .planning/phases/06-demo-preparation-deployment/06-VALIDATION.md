---
phase: 6
slug: demo-preparation-deployment
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `.venv312/bin/pytest tests/ -x -q` |
| **Full suite command** | `.venv312/bin/pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv312/bin/pytest tests/ -x -q`
- **After every plan wave:** Run `.venv312/bin/pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | INFRA-06 | integration | `docker compose config --quiet` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 1 | DEMO-01 | script | `.venv312/bin/python scripts/demo_check.py` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 2 | DEMO-04 | integration | `curl -s https://{host}/health` | ❌ W0 | ⬜ pending |
| 06-04-01 | 04 | 3 | DEMO-02 | manual | Timed dry run | N/A | ⬜ pending |
| 06-05-01 | 05 | 3 | DEMO-05 | manual | Screen recording exists | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `Dockerfile` — Multi-stage build for FastAPI + Aerospike client
- [ ] `docker-compose.yml` — Local dev stack (FastAPI + Aerospike)
- [ ] `scripts/demo_check.py` — Validation script for all integrations

*Existing test infrastructure covers backend unit tests.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full demo arc < 3 min | DEMO-02 | Requires live LLM calls + timing | Run Attack 1 → Confirm → Attack 2 → Confirm, time it |
| Screen recording quality | DEMO-05 | Visual inspection | Play recording, verify all panels visible |
| Voice Q&A works | VOICE-01 | Requires Bland AI live | Start voice call during investigation |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
