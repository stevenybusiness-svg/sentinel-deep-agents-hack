---
phase: 05
slug: voice-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | pytest.ini (existing) |
| **Quick run command** | `pytest tests/test_bland_webhook.py tests/test_bland_call.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_bland_webhook.py tests/test_bland_call.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-T1 | 01 | 1 | API-04, VOICE-03 | unit | `pytest tests/test_bland_webhook.py -x` | ❌ Wave 0 | ⬜ pending |
| 05-01-T2 | 01 | 1 | VOICE-01, VOICE-02 | unit | `pytest tests/test_bland_call.py -x` | ❌ Wave 0 | ⬜ pending |
| 05-02-T1 | 02 | 2 | VOICE-04 | visual | `npm run build` (0 errors) | ✅ exists | ⬜ pending |
| 05-02-T2 | 02 | 2 | VOICE-01 | manual | Live Bland AI call end-to-end | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_bland_webhook.py` — stubs for API-04, VOICE-03 (test_webhook_returns_context, test_webhook_fallback, test_webhook_no_aerospike_call, test_context_fields_complete)
- [ ] `tests/test_bland_call.py` — stubs for VOICE-01, VOICE-02 (test_call_payload_structure, test_barge_in_params)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live voice call answers "Why did you block that?" grounded in actual scores | VOICE-01 | Requires real Bland AI API key + public URL + phone number | Run POST /bland-call with valid credentials, verify call connects and Supervisor narrates anomaly scores |
| Barge-in interrupts Supervisor mid-sentence | VOICE-02 | Requires live call | During active call, speak while Supervisor is talking; verify it stops and processes new input |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
