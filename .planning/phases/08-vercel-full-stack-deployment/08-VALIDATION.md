---
phase: 8
slug: vercel-full-stack-deployment
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 8 — Validation Strategy

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
| 08-01-01 | 01 | 1 | PHASE8-01 | structural | `grep "Auth0Provider" frontend/src/main.jsx && grep "useAuth0" frontend/src/App.jsx` | pending |
| 08-01-02 | 01 | 1 | PHASE8-04 | structural | `grep "rules_fired" sentinel/integrations/slack_reporter.py && grep "arc" sentinel/integrations/slack_reporter.py` | pending |
| 08-02-01 | 02 | 2 | PHASE8-02 | structural | `grep "scenario1\|scenario2" frontend/src/App.jsx && grep "flowStep" frontend/src/App.jsx` | pending |
| 08-02-02 | 02 | 2 | PHASE8-03 | structural | `grep "rule-pulse\|orange" frontend/src/index.html && grep "persistedRuleNodes" frontend/src/store.js` | pending |
| 08-03-01 | 03 | 3 | PHASE8-06 | structural | `test -f frontend/vercel.json && grep "rewrites" frontend/vercel.json` | pending |
| 08-03-02 | 03 | 3 | PHASE8-05 | manual | Full arc QA — browser-based end-to-end verification | pending |
| 08-03-03 | 03 | 3 | PHASE8-07 | integration | `python -c "from sentinel.memory.aerospike_client import get_aerospike_client; import asyncio; c=get_aerospike_client(); c.connect(); print(asyncio.run(c.health_check()))"` | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `npm install @auth0/auth0-react` — Auth0 React SDK
- [ ] Auth0 free-tier account created with SPA application (domain + clientId)
- [ ] Slack Incoming Webhook URL configured for #payment-system-infosec

*Wave 0 items are external setup — no test stubs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Automated Proxy |
|----------|-------------|------------|-----------------|
| Auth0 login screen appears and authenticates | PHASE8-01 | Requires Auth0 account + browser interaction | `grep "Auth0Provider" frontend/src/main.jsx` |
| Scenario screens display before each attack | PHASE8-02 | Visual UX flow | `grep "flowStep" frontend/src/App.jsx` |
| Orange pulse animation on rule deployment | PHASE8-03 | Visual animation timing | `grep "rule-pulse" frontend/src/index.html` |
| Full arc works end-to-end (both attacks) | PHASE8-05 | Multi-step browser interaction | Backend test suite passing |
| Slack message appears in #payment-system-infosec | PHASE8-04 | Requires live webhook | `python -m pytest tests/test_airbyte_slack.py -x -q` |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or accepted manual-only coverage
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
