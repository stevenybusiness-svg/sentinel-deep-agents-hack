---
phase: 08-vercel-full-stack-deployment
plan: 02
subsystem: ui, demo-flow
tags: [react, zustand, scenario-screen, animation, demo-ux, guided-flow]

# Dependency graph
requires:
  - phase: 08-01
    provides: Auth0 login gate and ScenarioScreen import already wired in App.jsx
provides:
  - ScenarioScreen component with attack1/attack2 context screens
  - Multi-step flow state machine (scenario1 -> dashboard1 -> scenario2 -> dashboard2)
  - Orange pulse CSS animation on rule_node status nodes
  - persistedRuleNodes/persistedRuleEdges surviving resetInvestigation()
affects: [demo-ux, investigation-tree, self-improvement-visual]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "flowStep enum state machine in AuthenticatedApp: scenario1 -> dashboard1 -> scenario2 -> dashboard2"
    - "persistedRuleNodes: rule nodes accumulated across investigations, re-added on initInvestigationTree()"
    - "@keyframes rule-pulse in index.html: box-shadow glow animation applied to rule_node status"

key-files:
  created:
    - frontend/src/components/ScenarioScreen.jsx
    - frontend/src/demoData.js
  modified:
    - frontend/src/App.jsx
    - frontend/src/store.js
    - frontend/src/components/InvestigationTree.jsx
    - frontend/index.html

key-decisions:
  - "flowStep replaces showIntro boolean -- supports multi-step narrative flow not just on/off toggle"
  - "persistedRuleNodes accumulated via addRuleNode, re-injected in initInvestigationTree -- rule nodes survive resetInvestigation() without storing in resetInvestigation's explicit clear list"
  - "demoData.js copied from main repo to fix pre-existing build blocker (Rule 3 deviation)"

requirements-completed: [PHASE8-02, PHASE8-03]

# Metrics
duration: 10min
completed: 2026-03-27
---

# Phase 8 Plan 02: Guided Demo Flow + Orange Pulse Animation Summary

**ScenarioScreen component with multi-step flow state machine, @keyframes rule-pulse animation on rule_node nodes, and persistedRuleNodes that survive resetInvestigation() and re-appear in Attack 2 investigation tree**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-27T12:00:00Z
- **Completed:** 2026-03-27T12:10:08Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Judges see attack-specific context screens before each investigation, not the dashboard directly after login
- ScenarioScreen explains what will be demonstrated for each attack (hidden text injection vs. KYC spoofing), with "What to Watch" bullet points
- Attack 2 scenario screen shows "Generated Rule from Attack 1 is now active in the Safety Gate" alert -- sets up the self-improvement reveal
- Orange pulsing box-shadow animation fires on rule_node status nodes in the investigation tree -- most important visual in the demo
- Rule nodes from Attack 1 persist into Attack 2 as proof the system learned (via persistedRuleNodes store field)
- "Proceed to Attack 2" button appears in dashboard header after Attack 1 completes (flowStep === 'dashboard1' && status === 'complete')

## Task Commits

Each task was committed atomically:

1. **Task 1: Multi-step guided flow with ScenarioScreen components** - `aefd47c` (feat)
2. **Task 2: Orange pulse animation + persistedRuleNodes for cross-attack persistence** - `b975abe` (feat)

## Files Created/Modified

- `frontend/src/components/ScenarioScreen.jsx` - Attack-specific context screens with details list, hasLearnedRule alert banner, and Launch Investigation button
- `frontend/src/demoData.js` - Demo seed data copied from main repo (was untracked in worktree, blocking build)
- `frontend/src/App.jsx` - flowStep state machine replacing showIntro boolean; ScenarioScreen render guards; Proceed to Attack 2 button
- `frontend/src/store.js` - persistedRuleNodes/persistedRuleEdges fields; updated addRuleNode to persist; updated initInvestigationTree to spread persisted nodes/edges
- `frontend/src/components/InvestigationTree.jsx` - rule-pulse class applied to SentinelNode when status === 'rule_node'
- `frontend/index.html` - @keyframes rule-pulse and .rule-pulse CSS added to style block

## Decisions Made

- `flowStep` enum (scenario1/dashboard1/scenario2/dashboard2) replaces simple `showIntro` boolean -- four distinct render states map directly to the demo narrative
- `persistedRuleNodes` lives in Zustand store as an accumulating list; `resetInvestigation()` intentionally does NOT clear it (not listed in the reset); `initInvestigationTree()` spreads persisted nodes into the fresh tree
- Both attack buttons remain visible in the header for judge control, but the guided flow (flowStep) determines the narrative sequence

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing demoData.js in worktree**
- **Found during:** Task 1 verification (npm run build)
- **Issue:** `frontend/src/App.jsx` imports `./demoData` but the file only exists as untracked in the main repo, not in this worktree
- **Fix:** Copied `demoData.js` from `/Users/stevenyang/Documents/deep-agents-hackathon/frontend/src/demoData.js` to worktree `frontend/src/demoData.js`
- **Files modified:** `frontend/src/demoData.js` (created)
- **Commit:** `aefd47c` (included in Task 1 commit)

## Known Stubs

None -- all wired data. ScenarioScreen renders from static config (intentional, no dynamic data needed). persistedRuleNodes populated by real rule_deployed WebSocket events. Demo seed data in demoData.js provides realistic fallback state.

## Self-Check

Checking created files exist and commits are present...

---
*Phase: 08-vercel-full-stack-deployment*
*Completed: 2026-03-27*
