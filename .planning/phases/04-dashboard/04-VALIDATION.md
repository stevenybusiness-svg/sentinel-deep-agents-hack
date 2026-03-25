---
phase: 4
slug: dashboard
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend) |
| **Config file** | frontend/vite.config.js |
| **Quick run command** | `cd frontend && npm run build` |
| **Full suite command** | `cd frontend && npm run build && npm run lint` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm run build`
- **After every plan wave:** Run `cd frontend && npm run build && npm run lint`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 0 | DASH-01 | build | `cd frontend && npm run build` | ✅ | ⬜ pending |
| 4-01-02 | 01 | 1 | DASH-02 | build | `cd frontend && npm run build` | ✅ | ⬜ pending |
| 4-01-03 | 01 | 1 | DASH-03 | build | `cd frontend && npm run build` | ✅ | ⬜ pending |
| 4-01-04 | 01 | 2 | DASH-04 | build | `cd frontend && npm run build` | ✅ | ⬜ pending |
| 4-01-05 | 01 | 2 | DASH-05 | build | `cd frontend && npm run build` | ✅ | ⬜ pending |
| 4-02-01 | 02 | 2 | DASH-06 | build | `cd frontend && npm run build` | ✅ | ⬜ pending |
| 4-02-02 | 02 | 2 | DASH-07 | build | `cd frontend && npm run build` | ✅ | ⬜ pending |
| 4-02-03 | 02 | 3 | DASH-08 | build | `cd frontend && npm run build` | ✅ | ⬜ pending |
| 4-02-04 | 02 | 3 | DASH-09 | build | `cd frontend && npm run build` | ✅ | ⬜ pending |
| 4-03-01 | 03 | 3 | DASH-10 | build | `cd frontend && npm run build` | ✅ | ⬜ pending |
| 4-03-02 | 03 | 3 | DASH-11 | build | `cd frontend && npm run build` | ✅ | ⬜ pending |
| 4-03-03 | 03 | 3 | VOICE-04 | build | `cd frontend && npm run build` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Override `#root` width constraint in `frontend/src/index.css` (1126px → full width)
- [ ] Copy `sentinel/fixtures/invoice_clean.png` and `invoice_forensic.png` to `frontend/public/`
- [ ] Verify `@xyflow/react`, Zustand, Tailwind CDN already installed (no new packages needed)

*Wave 0 addresses layout blocker and static asset availability before component work begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Investigation tree animates node states on WS events | DASH-01 | Browser visual animation | Start demo, trigger investigation, observe node state transitions in @xyflow/react tree |
| Anomaly score bar fills with color-coded rule contributions | DASH-04 | Browser visual rendering | Trigger blocked investigation, observe bar segments and threshold line |
| Forensic side-by-side panel shows clean vs annotated | DASH-06 | Browser visual layout | Trigger investigation, observe two-panel image comparison |
| Rule evolution provenance (v1 → v2) visible | DASH-07 | Requires two incidents | Run second incident after rule generation, observe version history in rule panel |
| Aerospike latency updates live | DASH-10 | Real-time metric | Observe ms counter updating during investigation |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
