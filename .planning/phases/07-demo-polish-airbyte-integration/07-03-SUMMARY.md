---
phase: 07-demo-polish-airbyte-integration
plan: "03"
subsystem: frontend
tags: [demo-polish, intro-screen, forensic-comparison, react]
dependency_graph:
  requires: ["07-01", "07-02"]
  provides: [forensic-intro-screen, showIntro-state]
  affects: [frontend/src/App.jsx, frontend/src/components/ForensicIntroScreen.jsx]
tech_stack:
  added: []
  patterns: [conditional-render, useState-gate, callback-props]
key_files:
  created:
    - frontend/src/components/ForensicIntroScreen.jsx
  modified:
    - frontend/src/App.jsx
decisions:
  - "ForensicIntroScreen dismissed by clicking attack button — single click triggers both setShowIntro(false) and runAttack() simultaneously for zero-delay transition"
  - "showIntro defaults to true — intro screen appears on every fresh page load, not just first visit (no localStorage persistence needed for demo)"
metrics:
  duration: 64s
  completed: "2026-03-27"
  tasks_completed: 2
  files_changed: 2
requirements:
  - DEMO-POLISH-06
---

# Phase 07 Plan 03: Forensic Intro Screen Summary

**One-liner:** Full-screen forensic scan comparison intro screen gating the main dashboard — clean invoice vs. annotated forensic scan side-by-side, dismissed by attack button click.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create ForensicIntroScreen component | 03255c3 | frontend/src/components/ForensicIntroScreen.jsx |
| 2 | Wire intro screen into App.jsx with showIntro state | 4c9931c | frontend/src/App.jsx |

## What Was Built

ForensicIntroScreen is a full-screen React component that renders on first load before the main Sentinel dashboard. It shows:

- A title and one-sentence explanation of the attack scenario
- Two-column forensic comparison: "What the Agent Sees" (clean invoice) vs. "What Sentinel Finds" (forensic scan with hidden text highlighted)
- Two attack buttons: "Attack 1: Invoice Injection" and "Attack 2: Identity Spoofing"

Clicking either button calls `handleIntroAttack1` or `handleIntroAttack2` in App.jsx, which both: (1) dismiss the intro via `setShowIntro(false)`, and (2) immediately call `handleAttack1()` or `handleAttack2()` to fire the investigation. The transition is instant — no separate "dismiss" step.

App.jsx wiring:
- `useState` added alongside existing `useEffect` import
- `ForensicIntroScreen` imported
- `const [showIntro, setShowIntro] = useState(true)` added in App function body
- `handleIntroAttack1` and `handleIntroAttack2` wrapper functions defined
- Conditional early return before main dashboard JSX renders the intro when `showIntro === true`

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. Invoice images (`/invoice_clean.png`, `/invoice_forensic.png`) are served by the FastAPI backend as static files (wired in Phase 07 Plan 01). The intro screen always shows real images.

## Self-Check: PASSED

- `frontend/src/components/ForensicIntroScreen.jsx` — FOUND
- `frontend/src/App.jsx` — modified with showIntro state — FOUND
- Commit `03255c3` — FOUND (feat(07-03): create ForensicIntroScreen component)
- Commit `4c9931c` — FOUND (feat(07-03): wire ForensicIntroScreen into App.jsx)
- `npx vite build` — exits 0, 187 modules transformed, built in 256ms
