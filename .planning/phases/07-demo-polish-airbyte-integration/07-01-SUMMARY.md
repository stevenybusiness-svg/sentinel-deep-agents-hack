---
phase: 07-demo-polish-airbyte-integration
plan: 01
subsystem: frontend-serving
tags: [demo-polish, frontend, fastapi, investigation-tree]
dependency_graph:
  requires: []
  provides: [invoice-image-serving, renamed-attack-buttons, colored-edge-animations]
  affects: [frontend/src/App.jsx, frontend/src/store.js, frontend/src/hooks/useWebSocket.js, sentinel/api/main.py]
tech_stack:
  added: []
  patterns: [FileResponse-before-SPA-catch-all, zustand-edge-color-action, colored-edge-WS-events]
key_files:
  created: []
  modified:
    - sentinel/api/main.py
    - frontend/src/App.jsx
    - frontend/src/store.js
    - frontend/src/hooks/useWebSocket.js
decisions:
  - Invoice PNG routes registered before SPA catch-all — FastAPI route priority requires explicit routes first
  - setEdgeActive action adds both animated and colored style to edges — distinct from setEdgeAnimated (preserved)
  - Color scheme: blue=agent-active, gold=gate-evaluating, red=blocked, green=passed
metrics:
  duration: "~5 minutes"
  completed: "2026-03-27"
  tasks: 2
  files: 4
---

# Phase 7 Plan 1: Demo Visual Polish — Invoice Images, Button Labels, Edge Colors Summary

**One-liner:** Fixed invoice PNG serving via explicit FastAPI routes, renamed attack buttons to clean labels, and added blue/gold/red/green edge color animations to the investigation tree on WS events.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix invoice image serving and rename attack buttons | 6981dde | sentinel/api/main.py, frontend/src/App.jsx |
| 2 | Add colored edge animations on investigation tree | 5c41a2f | frontend/src/store.js, frontend/src/hooks/useWebSocket.js |

## What Was Built

### Task 1 — Invoice Image Serving + Button Rename

**Root cause:** The SPA catch-all `@app.get("/{full_path:path}")` intercepted `/invoice_clean.png` and `/invoice_forensic.png` requests, returning `index.html` instead of the image files.

**Fix:** Added two explicit FileResponse routes for `/invoice_clean.png` and `/invoice_forensic.png` inside the `if _FRONTEND_DIST.exists():` block, positioned before the catch-all route. FastAPI evaluates routes in registration order, so these now intercept PNG requests correctly.

**Button rename:** Replaced `Run Attack 1 &mdash; Invoice Injection` with `Attack 1: Invoice Injection` and `Run Attack 2 &mdash; Identity Spoofing` with `Attack 2: Identity Spoofing`. Removes visual clutter and uses clean colon separator.

### Task 2 — Colored Edge Animations

**New store action:** Added `setEdgeActive(edgeId, color)` to `store.js` alongside the existing `setEdgeAnimated`. Sets `animated: true` plus `style: { stroke: color, strokeWidth: 2 }` on the edge.

**WebSocket handler updates in `useWebSocket.js`:**
- `agent_completed`: Blue (#3b82f6) on supervisor→agent and agent→gate edges
- `verdict_board_assembled`: Gold (#e3b341) on all three agent→gate edges (gate evaluating)
- `gate_evaluated`: Red (#f85149) for NO-GO, gold (#e3b341) for ESCALATE, green (#3fb950) for GO on agent→gate edges

The existing `setEdgeAnimated` action is preserved — still used internally by other code.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all changes are functional wiring (serving real files, renaming labels, wiring real WS events to real store actions).

## Self-Check: PASSED

Files exist:
- sentinel/api/main.py — FOUND (modified)
- frontend/src/App.jsx — FOUND (modified)
- frontend/src/store.js — FOUND (modified)
- frontend/src/hooks/useWebSocket.js — FOUND (modified)

Commits exist:
- 6981dde — FOUND
- 5c41a2f — FOUND

Vite build: succeeded (186 modules, 0 errors)
