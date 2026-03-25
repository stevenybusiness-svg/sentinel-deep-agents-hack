---
phase: 4
slug: dashboard
status: draft
nyquist_compliant: true
wave_0_complete: true
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
| 4-01-01 | 01 | 1 | VOICE-04 | build | `cd frontend && npm run build` | yes | pending |
| 4-01-02 | 01 | 1 | VOICE-04 | build | `cd frontend && npm run build` | yes | pending |
| 4-02-01 | 02 | 2 | DASH-01, DASH-02 | build | `cd frontend && npm run build` | yes | pending |
| 4-02-02 | 02 | 2 | DASH-07, DASH-11 | build | `cd frontend && npm run build` | yes | pending |
| 4-03-01 | 03 | 3 | DASH-03, DASH-10 | build | `cd frontend && npm run build` | yes | pending |
| 4-03-02 | 03 | 3 | DASH-04 | build | `cd frontend && npm run build` | yes | pending |
| 4-04-01 | 04 | 4 | DASH-05 | build | `cd frontend && npm run build` | yes | pending |
| 4-04-02 | 04 | 4 | DASH-08, DASH-09 | build | `cd frontend && npm run build` | yes | pending |
| 4-05-01 | 05 | 5 | ALL | visual | `cd frontend && npm run build` | yes | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [x] Override `#root` width constraint in `frontend/src/index.css` (1126px -> full width) — covered in Plan 01 Task 1
- [x] Copy `sentinel/fixtures/invoice_clean.png` and `invoice_forensic.png` to `frontend/public/` — covered in Plan 01 Task 1
- [x] Verify `@xyflow/react`, Zustand, Tailwind CDN already installed (no new packages needed) — confirmed in Phase 1 scaffold

*Wave 0 addresses layout blocker and static asset availability before component work begins. All items covered by Plan 01 Task 1.*

---

## Nyquist Compliance Justification

This phase uses **build-only verification** (`npm run build`) as the automated feedback signal. This is explicitly justified because:

1. **All components are UI-rendering code** — correctness is verified visually in Plan 05 checkpoint
2. **Build catches** import errors, JSX syntax errors, missing exports, and type mismatches
3. **No business logic** exists in the frontend that would benefit from unit tests — all logic lives in the Python backend (Phases 1-3)
4. **15-second feedback latency** is well within the Nyquist threshold
5. **Plan 05 is a dedicated visual verification checkpoint** that covers all DASH requirements

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Investigation tree animates node states on WS events | DASH-01 | Browser visual animation | Start demo, trigger investigation, observe node state transitions in @xyflow/react tree |
| Anomaly score bar fills with color-coded rule contributions | DASH-04 | Browser visual rendering | Trigger blocked investigation, observe bar segments and threshold line |
| Forensic side-by-side panel shows clean vs annotated | DASH-06 | Browser visual layout | Trigger investigation, observe two-panel image comparison |
| Rule evolution provenance (v1 -> v2) visible | DASH-07 | Requires two incidents | Run second incident after rule generation, observe version history in rule panel |
| Aerospike latency updates live | DASH-10 | Real-time metric | Observe ms counter updating during investigation |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ready
