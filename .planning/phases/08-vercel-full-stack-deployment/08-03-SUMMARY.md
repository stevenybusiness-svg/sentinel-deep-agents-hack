---
phase: 08-vercel-full-stack-deployment
plan: 03
subsystem: frontend, deployment
tags: [vercel, vite, env-vars, deployment-prep]

# Dependency graph
requires:
  - phase: 08-01
    provides: Auth0 login gate and Slack reporter
  - phase: 08-02
    provides: Guided flow, self-improvement animation, Aerospike latency panel
provides:
  - frontend/vercel.json with API rewrites to EC2 before SPA catch-all
  - All frontend API and WebSocket URLs parameterized via VITE_ env vars
  - Frontend builds cleanly for Vercel deployment
affects: [vercel-deployment, ec2-backend-routing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "vercel.json rewrites: /api/:path* -> EC2 before SPA catch-all /(.*) -> /index.html"
    - "apiBase = import.meta.env.VITE_API_URL || '' for API calls (empty = same-origin/rewrite)"
    - "wsBase = import.meta.env.VITE_WS_URL || ws://window.location.host for WebSocket"

key-files:
  created:
    - frontend/vercel.json
  modified:
    - frontend/src/hooks/useWebSocket.js
    - frontend/src/App.jsx
    - frontend/src/components/GateDecisionPanel.jsx
    - frontend/src/components/VoicePanel.jsx

decisions:
  - "EC2 URL placeholder (YOUR_EC2_HOST) in vercel.json -- replaced when EC2 provisioned in Phase 9"
  - "apiBase defined at module level in each file -- no React context overhead for a simple constant"
  - "VoicePanel.jsx parameterized too even though VoicePanel is legacy -- prevents broken fetch if component re-enabled"

metrics:
  duration: 5
  completed_date: "2026-03-27"
  tasks_total: 2
  tasks_completed: 1
  files_created: 1
  files_modified: 4
---

# Phase 8 Plan 3: Vercel Deployment Prep Summary

One-liner: vercel.json with EC2 API rewrites + VITE_API_URL/VITE_WS_URL parameterization across all frontend fetch and WebSocket calls.

## Status: PARTIAL -- Awaiting Checkpoint

Task 1 is complete and committed. Task 2 is a `checkpoint:human-verify` gate requiring human confirmation of the full demo arc.

## Tasks

| # | Name | Status | Commit |
|---|------|--------|--------|
| 1 | Vercel deployment prep -- vercel.json, env var parameterization | COMPLETE | 2d3bce6 |
| 2 | Full arc QA + Aerospike latency verification | PENDING HUMAN VERIFY | - |

## What Was Built

**Task 1: Vercel Deployment Prep**

Created `frontend/vercel.json` with two rewrites in correct order:
1. `/api/:path*` -> `https://YOUR_EC2_HOST/api/:path*` (API proxy to EC2)
2. `/(.*)`  -> `/index.html` (SPA catch-all)

The API rewrite MUST come before the SPA catch-all (Pitfall 2 from research). The EC2 URL placeholder will be replaced in Phase 9 when the actual EC2 instance is provisioned.

Parameterized all frontend API calls:
- `frontend/src/App.jsx`: `apiBase = import.meta.env.VITE_API_URL || ''` -- used in `runAttack()`
- `frontend/src/components/GateDecisionPanel.jsx`: `apiBase` for `/api/confirm`
- `frontend/src/components/VoicePanel.jsx`: `apiBase` for `/api/bland-call`
- `frontend/src/hooks/useWebSocket.js`: `wsBase = import.meta.env.VITE_WS_URL || ws://window.location.host`

The `.env.example` already had both `VITE_API_URL` and `VITE_WS_URL` entries -- no changes needed there.

**Build verification:** `npm run build` succeeds -- 188 modules transformed in 654ms.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Coverage] Parameterized GateDecisionPanel.jsx and VoicePanel.jsx**
- **Found during:** Task 1, step 4 (grep for all `fetch('/api/` patterns)
- **Issue:** Plan said to grep for all hardcoded API calls -- found `/api/confirm` in GateDecisionPanel.jsx and `/api/bland-call` in VoicePanel.jsx
- **Fix:** Added `apiBase` constant and updated fetch URLs in both files
- **Files modified:** `frontend/src/components/GateDecisionPanel.jsx`, `frontend/src/components/VoicePanel.jsx`
- **Commit:** 2d3bce6

## Verification (Task 1 Automated)

All acceptance criteria verified:
- `test -f frontend/vercel.json` -- PASS
- `grep "rewrites" frontend/vercel.json` -- PASS (1 match)
- `grep "/api/:path*" frontend/vercel.json` -- PASS
- `grep "VITE_WS_URL" frontend/src/hooks/useWebSocket.js` -- PASS
- `grep "VITE_API_URL" frontend/src/App.jsx` -- PASS
- `grep "VITE_API_URL" .env.example` -- PASS
- `grep "VITE_WS_URL" .env.example` -- PASS
- API rewrite before SPA catch-all -- PASS
- `npm run build` -- PASS (188 modules, 654ms)

## Known Stubs

None -- vercel.json uses `YOUR_EC2_HOST` placeholder intentionally. This is not a stub -- it is a documented placeholder to be replaced in Phase 9 (AWS/EC2 provisioning).

## Self-Check: PASSED

- `frontend/vercel.json` exists: FOUND
- commit 2d3bce6 exists: FOUND
