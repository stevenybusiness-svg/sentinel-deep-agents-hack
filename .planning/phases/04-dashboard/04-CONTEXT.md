# Phase 4: Dashboard - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the React dashboard that visualizes the complete Sentinel investigation lifecycle in real time. This phase wires all WebSocket events from the backend (Phase 2/3) to visible UI state: investigation tree animation, prediction vs. actual panel, anomaly score bar, verdict board table, forensic scan, rule source panel, gate decision, decision log, and Aerospike latency display.

**This phase does NOT include:** voice integration (Phase 5), demo deployment scripts (Phase 6), new backend endpoints beyond what Phases 1-3 already provide.

</domain>

<decisions>
## Implementation Decisions

### Layout

- **D-01:** Fixed multi-column grid — all panels visible simultaneously, no scrolling during demo. Two columns: left = investigation tree (full height), right = stacked data panels. This is non-negotiable for a live demo where simultaneous animation is the key visual.

- **D-02:** Left column: investigation tree takes the full left column height. No splits — maximum node graph space for the tree to grow as agents complete and rule nodes appear.

- **D-03:** Right column panel order (top to bottom):
  1. Gate Decision (prominent — GO/NO-GO/ESCALATE + attribution text + Confirm button)
  2. Composite Anomaly Score Bar (color-coded rule contributions + threshold line)
  3. Verdict Board Table (field-level match/mismatch with severity)
  4. Forensic Scan (clean invoice vs. forensic scan side-by-side)
  5. Rule Source Panel (generated Python + provenance)
  6. Aerospike latency metric (small, bottom)
  Prediction vs. actual panel is integrated into the verdict board or as a sub-panel near it — not a separate full-width panel.

### Demo Trigger UX

- **D-04:** Two hardcoded buttons in the header bar: "Run Attack 1 — Invoice Injection" and "Run Attack 2 — Identity Spoofing". Always visible in the header alongside the WebSocket status indicator. One click, zero form inputs, no dropdowns. Calls POST /investigate with the corresponding fixture payload.

- **D-05:** Buttons are disabled/greyed while an investigation is running (`investigationStatus === 'running'`). Reset to enabled after gate decision lands.

### Confirm / Operator Action

- **D-06:** "Confirm Attack — Learn ▶" button appears in the gate decision panel immediately after a NO-GO verdict. The button is not visible during GO or ESCALATE decisions, and not visible before gate evaluation. Calls POST /confirm with the current episode ID.

- **D-07:** No modal. The button is inline within the gate decision panel. After click, the button state changes to "Generating rule..." and the rule source panel immediately begins streaming tokens from `rule_generating` WebSocket events.

- **D-08:** No spinner interstitial — streaming tokens begin immediately. If there's a 1-2s delay before first token, the rule source panel shows a blinking cursor. The streaming live generation is the demo moment, not a loading state.

### Rule Source Presentation

- **D-09:** Syntax-highlighted monospace for the generated Python. Keyword/string/value color distinction. Use a simple highlighting approach (css classes or a lightweight library — not a heavy editor like Monaco; this is display-only, not editable).

- **D-10:** Below the code: provenance section with horizontal rule separator:
  ```
  ―― Provenance ――
  Episode: {episode_id}  ·  Deployed: {relative_time}
  Prediction errors: {top 1-2 deviations from prediction_errors}
  ```

- **D-11:** After rule evolution (v2): replace displayed source with v2, add `[v2]` badge inline after the function signature line. Provenance section updates to: "Evolved from: {ep1} + {ep2} · Deployed: {time}". No diff view — replace in place. v1 is gone from the panel; the evolution story is told through the provenance text.

- **D-12:** During streaming (rule_generating events), tokens append to the code panel character by character. The panel scrolls automatically to keep the latest token visible. After `rule_deployed`, the final source replaces the streamed content (in case streaming was partial).

### WebSocket / State Architecture

- **D-13:** Use the existing native browser WebSocket (already wired in Phase 1 store.js). Add WebSocket connection management to a `useWebSocket` hook or directly in App.jsx. On each named event, dispatch to Zustand store.

- **D-14:** Zustand store (store.js) needs additions for Phase 4:
  - `nodes` / `edges` for @xyflow/react (investigation tree state)
  - `predictionData` — expected vs. actual values
  - `ruleSources` — array of `{source, version, episodeIds, deployedAt, predictionErrors}`
  - `ruleStreaming` — boolean + `streamingBuffer` string for live token display
  - `decisionLog` — array of timestamped gate decisions

- **D-15:** Keep store updates synchronous from WebSocket events. No async state in Zustand. WebSocket handler dispatches directly to store setters.

### Claude's Discretion

- Node visual design in the investigation tree (icon choices, exact color palette for pending/active/complete/blocked states) — Claude decides, consistent with existing dark theme (bg-dark, accent purple #aa3bff).
- Exact panel border/shadow styling — consistent with existing App.jsx dark theme.
- Prediction vs. actual panel integration point (whether it's a sub-section of verdict board or its own panel above the verdict table) — Claude decides based on available right-column space.
- Animation timing for score bar fill and node state transitions — Claude decides, prioritize visual clarity over animation complexity.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Dashboard — DASH-01 through DASH-11, VOICE-04 (all must be satisfied)

### Existing Frontend Code
- `frontend/src/App.jsx` — current scaffold: dark theme classes, header structure, ReactFlow canvas, WebSocket status indicator
- `frontend/src/store.js` — existing Zustand store: agent statuses, verdictBoard, gateDecision, aerospikeLatencyMs placeholders
- `frontend/src/index.css` — CSS variables: --accent (#aa3bff / #c084fc dark), --bg-dark (#16171d), --border (#2e303a)

### Backend WebSocket Events (Phase 2/3)
- `sentinel/schemas/events.py` — EventType Literal: all 9 named events that the dashboard consumes
- `sentinel/api/routes/confirm.py` — POST /confirm: accepts `{episode_id, attack_type}`, returns 202, streams rule_generating events

### Phase 1 Frontend Scaffold Context
- `.planning/phases/01-foundation/01-03-SUMMARY.md` — documents the Tailwind CDN v3 decision and @xyflow/react import pattern

### No external UI specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `App.jsx` header: existing `flex items-center justify-between h-12 px-4 border-b border-border-muted` pattern — extend with Attack buttons
- `store.js`: agent status shape `{ risk: { status: 'pending' }, ... }` already defined — extend for Phase 4 fields
- WebSocket status indicator in header: existing `pulse-dot` pattern for live status

### Established Patterns
- Dark theme: `bg-bg-dark`, `text-text-main`, `font-display`, `border-border-muted` — all panels must use these
- Accent color: `#aa3bff` (light) / `#c084fc` (dark) — use for active states, highlights, NO-GO indicators
- Tailwind CDN v3 (not npm) — no new Tailwind config, use utility classes only

### Integration Points
- `@xyflow/react` already imported and rendering in App.jsx — extend nodes/edges from Zustand store
- `useStore` hook pattern already established — all new UI state goes through Zustand
- WebSocket connects to `ws://localhost:8000/ws` — add message handler that dispatches to store setters

</code_context>

<specifics>
## Specific Ideas

- Gate decision panel mockup (from discussion):
  ```
  ⛔ NO-GO
  Score: 1.84 › threshold
  Attribution: rule_mismatch ...

  [ Confirm Attack — Learn ▶ ]
  ```

- Rule source panel mockup (from discussion):
  ```
  def score(verdict_board: dict) -> float:  [v2]
      """Evolved: drops single-attack artifacts,
      strengthens compound behavioral signals."""
      ...

  ―― Provenance ――
  Evolved from: ep_abc123 + ep_def456
  Deployed: 30s ago
  ```

- Header layout (from discussion):
  ```
  Sentinel Dashboard    [Run Attack 1 — Invoice Injection] [Run Attack 2 — Identity Spoofing]   ● connected · idle
  ```

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-dashboard*
*Context gathered: 2026-03-25*
