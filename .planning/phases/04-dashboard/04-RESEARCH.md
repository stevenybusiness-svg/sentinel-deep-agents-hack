# Phase 4: Dashboard - Research

**Researched:** 2026-03-25
**Domain:** React 18 + @xyflow/react dashboard wired to FastAPI WebSocket backend
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Fixed multi-column grid — all panels visible simultaneously, no scrolling during demo. Two columns: left = investigation tree (full height), right = stacked data panels. Non-negotiable for live demo.

**D-02:** Left column: investigation tree takes the full left column height. No splits.

**D-03:** Right column panel order (top to bottom):
1. Gate Decision (prominent — GO/NO-GO/ESCALATE + attribution text + Confirm button)
2. Composite Anomaly Score Bar
3. Verdict Board Table
4. Forensic Scan (clean invoice vs. forensic scan side-by-side)
5. Rule Source Panel
6. Aerospike latency metric (small, bottom)
Prediction vs. actual integrated into the verdict board as sub-row per mismatch.

**D-04:** Two hardcoded buttons: "Run Attack 1 — Invoice Injection" and "Run Attack 2 — Identity Spoofing". Always visible in header. One click, zero form inputs.

**D-05:** Buttons disabled while `investigationStatus === 'running'`. Reset to enabled after gate decision lands.

**D-06:** "Confirm Attack — Learn ▶" button appears in gate decision panel immediately after NO-GO. Not visible for GO or ESCALATE. Not visible before gate evaluation. Calls POST /confirm.

**D-07:** No modal. Inline button. After click, changes to "Generating rule..." (disabled). Rule source panel immediately begins streaming tokens.

**D-08:** No spinner interstitial — streaming tokens begin immediately. Blinking cursor in rule source panel if 1-2s delay before first token.

**D-09:** Syntax-highlighted monospace for generated Python. CSS classes only — no Monaco, no heavy editor.

**D-10:** Provenance section below code with `―― Provenance ――` separator. Shows episode ID, deployed timestamp, top 1-2 prediction error deviations.

**D-11:** After rule evolution (v2): replace displayed source with v2, add `[v2]` badge inline. Provenance updates to "Evolved from: {ep1} + {ep2}". No diff view.

**D-12:** During streaming, tokens append character by character. Panel auto-scrolls. After `rule_deployed`, final source replaces streamed content.

**D-13:** Native browser WebSocket (already in Phase 1 store.js). Add connection management to `useWebSocket` hook or directly in App.jsx. Dispatch named events to Zustand store.

**D-14:** Zustand store additions:
- `nodes` / `edges` for @xyflow/react
- `predictionData` — expected vs. actual values
- `ruleSources` — array of `{source, version, episodeIds, deployedAt, predictionErrors}`
- `ruleStreaming` — boolean + `streamingBuffer` string
- `decisionLog` — array of timestamped gate decisions

**D-15:** Store updates synchronous from WebSocket events. No async state in Zustand. WebSocket handler dispatches directly to store setters.

### Claude's Discretion

- Node visual design in investigation tree (icon choices, exact color palette for pending/active/complete/blocked states) — consistent with dark theme (bg-dark, accent purple #aa3bff)
- Exact panel border/shadow styling — consistent with existing App.jsx dark theme
- Prediction vs. actual panel integration point (sub-section of verdict board or above table) — based on available right-column space
- Animation timing for score bar fill and node state transitions — prioritize visual clarity over animation complexity

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DASH-01 | Investigation tree rendered with @xyflow/react; nodes animate to active state as sub-agents receive dispatch; edges animate as data flows | @xyflow/react v12 node/edge state management; WebSocket `agent_completed` event drives node state transitions |
| DASH-02 | New rule node appears in investigation tree after rule deployment — tree is visibly larger after learning | `rule_deployed` WebSocket event triggers node/edge addition to Zustand `nodes`/`edges` arrays |
| DASH-03 | Verdict board table shows field-level match/mismatch for all claims_checked with severity indicators | `verdict_board_assembled` event payload: `verdict_board.mismatches[]` with field/agent_claimed/independently_found/match/severity |
| DASH-04 | Forensic scan panel shows clean invoice view vs. forensic scan side-by-side for Phase 1 demo | Static images at `sentinel/fixtures/invoice_clean.png` and `sentinel/fixtures/invoice_forensic.png`; served via Vite or backend static route |
| DASH-05 | Generated rule source panel shows readable Python with provenance and evolution history (v1 → v2) | `rule_deployed` payload: `{rule_id, version, source, episode_ids, attribution}`; `rule_generating` for streaming |
| DASH-06 | Trust score bar animates from 0.85 to post-investigation value as verdict board assembles | `gate_evaluated` payload includes `composite_score`; trust score derived from inverse: `max(0, 1.0 - composite_score)` |
| DASH-07 | Gate decision (GO / NO-GO / ESCALATE) displayed prominently with full attribution | `gate_evaluated` payload: `{decision, composite_score, attribution, rule_contributions[]}` |
| DASH-08 | Decision log shows timestamped trail of all gate decisions with one-line attribution per entry | Each `gate_evaluated` event appended to `decisionLog` Zustand array |
| DASH-09 | Aerospike latency metric displayed live on dashboard | `episode_written` event payload: `{episode_id, write_latency_ms}` |
| DASH-10 | Prediction vs. actual panel shows expected values alongside actual findings with prediction errors highlighted | `verdict_board_assembled` payload includes `prediction_errors`; displayed as sub-row within verdict table per D-03 |
| DASH-11 | Composite anomaly score bar shows each rule's weighted contribution color-coded, with threshold line | `gate_evaluated` payload: `rule_contributions[]` with `{rule_id, score, is_generated}` |
| VOICE-04 | Dashboard always shows same information as voice narration — text fallback always present | All WS event data displayed in UI panels; no voice-only information paths |
</phase_requirements>

---

## Summary

Phase 4 is a pure frontend build phase — no new backend endpoints, no schema changes. The backend (Phases 1–3) is complete and emitting all 9 named WebSocket events. The frontend scaffold (Phase 1) exists at `frontend/src/App.jsx` + `frontend/src/store.js` with @xyflow/react already imported, Zustand store initialized, and Tailwind CDN v3 configured with the full design token set.

The primary work is: (1) extend the Zustand store with 7 new fields, (2) wire a `useWebSocket` hook that dispatches each named event to the store, (3) build 8 UI components consuming store state, and (4) compose them into the two-column fixed-viewport layout. The UI spec (04-UI-SPEC.md) is fully approved and defines every visual detail — this research focuses on the technical integration patterns.

The key constraint is the two-column fixed-height layout with no scroll. Right-column panels must fit on screen simultaneously. The @xyflow/react canvas must fill the entire left column. All state flows unidirectionally: WebSocket event → Zustand setter → React component re-render.

**Primary recommendation:** Build bottom-up — store extensions first, then WebSocket hook, then individual panels in isolation, then compose the two-column layout last. This order allows each piece to be verified independently before integration.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @xyflow/react | 12.4.4 | Investigation tree node graph | Already installed (Phase 1); v12 has built-in animated edges, custom nodes, controlled mode |
| zustand | 5.x | Client state management | Already installed (Phase 1); all state changes sync from WS handler |
| React | 18.x | Component framework | Already installed (Phase 1) |
| Tailwind CDN v3 | 3.x (CDN) | Styling | Already configured in index.html with full custom token set |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Material Symbols Outlined | variable font (CDN) | Icons for node states | Already loaded in index.html; use for hourglass_empty, sync, check_circle, block, auto_awesome |
| Inter + Roboto Mono | Google Fonts CDN | Typography | Already loaded in index.html |
| Native browser WebSocket | built-in | Backend event stream | No additional WS library — browser native WebSocket to ws://localhost:8000/ws via Vite proxy |

**No new npm packages needed for this phase.** All dependencies are already installed.

**Version verification:** Confirmed against package.json from Phase 1 scaffold.

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/src/
├── App.jsx              # Root layout: header + two-column grid
├── store.js             # Zustand store (extend with Phase 4 fields)
├── hooks/
│   └── useWebSocket.js  # WS connection + event dispatch to store
└── components/
    ├── InvestigationTree.jsx    # @xyflow/react canvas + node/edge config
    ├── GateDecisionPanel.jsx    # GO/NO-GO/ESCALATE + Confirm button
    ├── AnomalyScoreBar.jsx      # Segmented color-coded score bar
    ├── VerdictBoardTable.jsx    # Field-level mismatch table + prediction sub-rows
    ├── ForensicScanPanel.jsx    # Side-by-side invoice images
    ├── RuleSourcePanel.jsx      # Streaming Python + provenance
    ├── DecisionLog.jsx          # Timestamped gate decision trail
    └── AerospikeLatency.jsx     # Small metric chip
```

### Pattern 1: Zustand Store Extensions

**What:** Add all Phase 4 state fields to the existing store.js. Keep all setter functions synchronous — no async side effects inside setters.

**When to use:** All new UI state.

```js
// Extend existing create() block in store.js
nodes: [],
edges: [],
predictionData: null,
ruleSources: [],
ruleStreaming: false,
streamingBuffer: '',
decisionLog: [],

// Setters (synchronous, called from WS handler)
setNodes: (nodes) => set({ nodes }),
setEdges: (edges) => set({ edges }),
addRuleSource: (rule) => set((s) => ({ ruleSources: [...s.ruleSources, rule] })),
appendStreamToken: (token) => set((s) => ({ streamingBuffer: s.streamingBuffer + token })),
setRuleStreaming: (val) => set({ ruleStreaming: val }),
addDecisionLogEntry: (entry) => set((s) => ({ decisionLog: [entry, ...s.decisionLog] })),
```

### Pattern 2: WebSocket Hook (useWebSocket)

**What:** Single hook that opens the WebSocket connection, parses JSON messages, and dispatches to store setters based on `event` field. Reconnects on close.

**When to use:** Mount once in App.jsx via `useEffect`.

```js
// frontend/src/hooks/useWebSocket.js
import { useEffect } from 'react'
import { useStore } from '../store'

export function useWebSocket() {
  const store = useStore()

  useEffect(() => {
    let ws
    let reconnectTimer

    function connect() {
      ws = new WebSocket('ws://localhost:8000/ws')

      ws.onopen = () => store.setWsConnected(true)
      ws.onclose = () => {
        store.setWsConnected(false)
        reconnectTimer = setTimeout(connect, 2000)
      }
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data)
        handleEvent(msg, store)
      }
    }

    connect()
    return () => {
      clearTimeout(reconnectTimer)
      ws?.close()
    }
  }, [])
}

function handleEvent(msg, store) {
  const { event, data, episode_id, timestamp } = msg
  switch (event) {
    case 'investigation_started':
      store.resetInvestigation()
      store.set({ currentEpisodeId: episode_id, investigationStatus: 'running' })
      store.setNodes(buildInitialNodes())
      store.setEdges(buildInitialEdges())
      break
    case 'agent_completed':
      store.setAgentStatus(data.agent, 'complete', data.verdict)
      store.setNodes(updateNodeState(store.getState().nodes, data.agent, 'complete'))
      break
    case 'verdict_board_assembled':
      store.set({ verdictBoard: data.verdict_board })
      break
    case 'gate_evaluated':
      store.set({ gateDecision: data, investigationStatus: 'complete' })
      store.addDecisionLogEntry({ timestamp, ...data })
      break
    case 'episode_written':
      store.set({ aerospikeLatencyMs: data.write_latency_ms })
      break
    case 'rule_generating':
      store.set({ ruleStreaming: true })
      store.appendStreamToken(data.token ?? data.content ?? '')
      break
    case 'rule_deployed':
      store.addRuleSource({
        source: data.source,
        version: data.version,
        episodeIds: data.episode_ids,
        deployedAt: new Date().toISOString(),
        ruleId: data.rule_id,
        attribution: data.attribution,
      })
      store.set({ ruleStreaming: false, streamingBuffer: '' })
      store.setNodes(addRuleNode(store.getState().nodes, data))
      store.setEdges(addRuleEdge(store.getState().edges, data))
      break
  }
}
```

### Pattern 3: @xyflow/react Controlled Mode

**What:** Pass `nodes` and `edges` from Zustand store to ReactFlow via props. Use `onNodesChange` and `onEdgesChange` to allow pan/zoom without losing store-driven state.

**When to use:** Investigation tree component.

```jsx
// Source: @xyflow/react v12 docs — controlled flow
import { ReactFlow, Background, applyNodeChanges, applyEdgeChanges } from '@xyflow/react'
import { useStore } from '../store'

export default function InvestigationTree() {
  const nodes = useStore((s) => s.nodes)
  const edges = useStore((s) => s.edges)
  const setNodes = useStore((s) => s.setNodes)
  const setEdges = useStore((s) => s.setEdges)

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={(changes) => setNodes(applyNodeChanges(changes, nodes))}
      onEdgesChange={(changes) => setEdges(applyEdgeChanges(changes, edges))}
      fitView
      nodesDraggable={false}
      nodesConnectable={false}
    >
      <Background color="#30363d" gap={24} />
    </ReactFlow>
  )
}
```

### Pattern 4: Initial Node Topology

**What:** Build the fixed investigation tree topology when `investigation_started` fires. 7 nodes, 6 edges. Rule node(s) added dynamically after `rule_deployed`.

**Static topology:**
```js
function buildInitialNodes() {
  return [
    { id: 'supervisor',   type: 'sentinelNode', position: { x: 220, y: 20 },  data: { label: 'Supervisor',     state: 'active'   } },
    { id: 'payment',      type: 'sentinelNode', position: { x: 20,  y: 140 }, data: { label: 'Payment Agent',  state: 'pending'  } },
    { id: 'risk',         type: 'sentinelNode', position: { x: 140, y: 140 }, data: { label: 'Risk Agent',     state: 'pending'  } },
    { id: 'compliance',   type: 'sentinelNode', position: { x: 260, y: 140 }, data: { label: 'Compliance',     state: 'pending'  } },
    { id: 'forensics',    type: 'sentinelNode', position: { x: 380, y: 140 }, data: { label: 'Forensics',      state: 'pending'  } },
    { id: 'safetygate',   type: 'sentinelNode', position: { x: 220, y: 260 }, data: { label: 'Safety Gate',    state: 'pending'  } },
  ]
}

function buildInitialEdges() {
  return [
    { id: 'e-sup-pay', source: 'supervisor', target: 'payment',    animated: true },
    { id: 'e-sup-risk', source: 'supervisor', target: 'risk',      animated: true },
    { id: 'e-sup-comp', source: 'supervisor', target: 'compliance', animated: true },
    { id: 'e-sup-fore', source: 'supervisor', target: 'forensics',  animated: true },
    { id: 'e-risk-gate', source: 'risk',       target: 'safetygate', animated: true },
    { id: 'e-comp-gate', source: 'compliance', target: 'safetygate', animated: true },
    { id: 'e-fore-gate', source: 'forensics',  target: 'safetygate', animated: true },
  ]
}
```

### Pattern 5: Custom Node Type (sentinelNode)

**What:** Register a custom `sentinelNode` type that renders state-based styling per the UI spec (pending/active/complete/blocked/rule_node).

```jsx
// State → visual encoding (from UI spec)
const STATE_STYLES = {
  pending:   { border: 'border-border-muted border',   bg: 'bg-surface',               icon: 'hourglass_empty', iconColor: 'text-text-muted' },
  active:    { border: 'border-accent border-2 pulse-dot', bg: 'bg-surface',            icon: 'sync',           iconColor: 'text-accent spin' },
  complete:  { border: 'border-success border',        bg: 'bg-surface',               icon: 'check_circle',   iconColor: 'text-success' },
  blocked:   { border: 'border-danger border-2',       bg: 'bg-danger/10',             icon: 'block',          iconColor: 'text-danger' },
  rule_node: { border: 'border-warning border',        bg: 'bg-warning/10',            icon: 'auto_awesome',   iconColor: 'text-warning' },
}
```

### Pattern 6: Syntax Highlighting (CSS-Only)

**What:** Simple regex-based `String.replace()` that wraps Python keywords, strings, numbers, and comments in `<span>` tags with Tailwind color classes. Use `dangerouslySetInnerHTML` on a `<pre>` block. No Prism, no highlight.js.

```js
function highlightPython(src) {
  return src
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    // Comments first (avoid re-processing)
    .replace(/(#[^\n]*)/g, '<span class="text-text-muted italic">$1</span>')
    // Strings (triple-quoted docstrings first, then single/double)
    .replace(/("""[\s\S]*?""")/g, '<span class="text-success">$1</span>')
    .replace(/('[^']*'|"[^"]*")/g, '<span class="text-success">$1</span>')
    // Numbers
    .replace(/\b(\d+\.?\d*)\b/g, '<span class="text-warning">$1</span>')
    // Keywords
    .replace(/\b(def|return|if|else|elif|and|or|not|float|dict|bool|int|str|True|False|None)\b/g,
      '<span class="text-primary">$1</span>')
}
```

**Caution:** Order matters — comments and strings must be replaced before keywords to avoid double-wrapping. The regex approach is fragile for complex Python but is sufficient for the generated scoring functions (simple float-returning functions, no complex string content).

### Anti-Patterns to Avoid

- **Async Zustand state:** Zustand setters must be synchronous. Never `await` inside a setter. All async work happens in the WebSocket handler before calling the setter.
- **Multiple WebSocket connections:** One hook in App.jsx only. Child components read from store, not from their own WS connections.
- **`initialNodes`/`initialEdges` constants for controlled ReactFlow:** In controlled mode, pass store-derived arrays. The `initialNodes` pattern from Phase 1 scaffold is placeholder only — Phase 4 replaces it.
- **`reactflow` import:** The package is `@xyflow/react` (rebranded). App.jsx already uses the correct import.
- **Importing index.css Tailwind tokens:** The `--code-bg` and `--accent` CSS variables are defined in `index.css` but are not Tailwind tokens — reference them via `bg-[#1f2028]` or `var(--code-bg)` inline style, not `bg-code-bg`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Node graph with animated edges | Custom SVG/D3 flow graph | `@xyflow/react` v12 (already installed) | Built-in animated edges, node drag, pan/zoom, custom node types; handles all layout math |
| Icon set | SVG sprite or emoji | Material Symbols Outlined (already in index.html) | Variable font renders any icon size; consistent with existing pulse-dot icon usage |
| Token streaming display | Custom streaming protocol | Append `streamingBuffer` string to `<pre>` content on each `rule_generating` event | Simple string accumulation — no streaming library needed |
| WebSocket reconnection logic | Complex retry with backoff | `setTimeout(connect, 2000)` in `ws.onclose` | Simple 2s reconnect is sufficient for localhost demo; no need for exponential backoff |
| Panel scroll management | Manual scroll position tracking | `scrollTop = scrollHeight` on the rule source panel ref after each token append | Standard DOM pattern, no library needed |

---

## WebSocket Event Payload Reference

Critical reference for the WS handler — these are the actual shapes broadcast by the backend.

| Event | Key `data` Fields |
|-------|-------------------|
| `investigation_started` | `{payment_request: dict}` |
| `agent_completed` | `{agent: "risk"|"compliance"|"forensics", verdict: VerdictSchema}` |
| `verdict_board_assembled` | `{verdict_board: VerdictBoardSchema}` — includes `prediction_errors` attached by supervisor |
| `gate_evaluated` | `{decision: "GO"|"NO-GO"|"ESCALATE", composite_score: float, attribution: str, rule_contributions: [{rule_id, score, is_generated}]}` |
| `episode_written` | `{episode_id: str, write_latency_ms: float}` |
| `rule_generating` | Token data — field name needs verification (likely `token` or `content`) |
| `rule_deployed` | `{rule_id: str, version: int, source: str, episode_ids: list[str], write_latency_ms: float, attribution: str}` |
| `rule_generation_failed` | `{reason: str, attempts: int}` |

**Important — `rule_generating` token field name:** The confirm.py route streams via RuleGenerator which calls `ws_broadcast(event, data, episode_id)`. The exact field name for the token chunk inside `data` depends on RuleGenerator's streaming implementation. **The WS handler must read the actual field name from the RuleGenerator source** before writing the `rule_generating` case. Check `sentinel/engine/rule_generator.py` for the streaming data shape.

**`gate_evaluated` payload:** The supervisor broadcasts `gate_result` directly as the `data` dict: `await ws.broadcast("gate_evaluated", episode_id, gate_result)`. The `gate_result` dict includes `decision`, `composite_score`, `attribution`, and `rule_contributions`.

---

## Forensic Image Serving

Two static images exist at:
- `sentinel/fixtures/invoice_clean.png` — the invoice as the human/agent sees it
- `sentinel/fixtures/invoice_forensic.png` — the same invoice with hidden text visible

The frontend needs to serve/reference these. Options:
1. **Copy to `frontend/public/`** — Vite serves `public/` as static at `/`; images accessible as `/invoice_clean.png`
2. **Expose via FastAPI static mount** — add `app.mount("/fixtures", StaticFiles(directory="sentinel/fixtures"))` in main.py; images at `/fixtures/invoice_clean.png`

Option 1 (copy to public/) is simpler for a demo build. Option 2 avoids file duplication. Either works — the planner should pick one and commit to it. The forensic scan panel renders `<img src="..." />` with a fixed height container.

The red overlay for hidden text annotation in the forensic scan: `invoice_forensic.png` already has the hidden text rendered as near-white; the Forensics Agent detected it via vision. For the dashboard, the simplest approach is to display `invoice_forensic.png` as-is (the hidden text IS visible in the forensic scan image) plus a red `rgba(248,81,73,0.4)` overlay box via absolute positioning — but this requires knowing the pixel coordinates of the hidden text region. **If the hidden text region coordinates are not known, just display `invoice_forensic.png` without overlay — the image itself should show the detected content.**

---

## Common Pitfalls

### Pitfall 1: ReactFlow Controlled Mode — applyNodeChanges Required

**What goes wrong:** Passing `nodes` from Zustand to ReactFlow but not handling `onNodesChange` causes the graph to freeze when users try to pan or the graph tries to update node positions internally.

**Why it happens:** ReactFlow v12 in controlled mode requires the parent to apply any internally-generated changes (position updates, selection state) back to the node array.

**How to avoid:** Always wire `onNodesChange={(changes) => setNodes(applyNodeChanges(changes, nodes))}` and the equivalent for edges. Import `applyNodeChanges` and `applyEdgeChanges` from `@xyflow/react`.

**Warning signs:** Nodes don't move when dragged; graph jumps back to initial positions.

### Pitfall 2: @xyflow/react CSS Must Be Imported

**What goes wrong:** ReactFlow renders blank or with broken layout.

**Why it happens:** @xyflow/react requires its own CSS for the canvas, handles, and edge rendering. Without it, the graph has no visual output.

**How to avoid:** `import '@xyflow/react/dist/style.css'` — this is already present in App.jsx from Phase 1. Do NOT remove it when refactoring App.jsx.

### Pitfall 3: Tailwind CDN v3 Does Not Support Arbitrary Opacity Modifiers on Custom Colors

**What goes wrong:** `bg-danger/20` works for Tailwind built-in colors but may not compile for custom tokens in CDN mode.

**Why it happens:** Tailwind CDN v3 JIT scans for class names at runtime; opacity modifiers on custom color tokens require the color to be defined as an RGB value (not hex) for the opacity math to work. However, this project's Tailwind config defines custom colors as hex strings (e.g. `"danger": "#f85149"`).

**How to avoid:** Test `bg-danger/20` in the actual browser early. If it doesn't work, fall back to explicit inline style: `style={{ background: 'rgba(248,81,73,0.2)' }}`. The UI spec shows these patterns — have inline-style fallbacks ready.

**Warning signs:** Panel backgrounds or badge backgrounds appear solid or transparent instead of semi-transparent.

### Pitfall 4: Two-Column Layout Height Overflow

**What goes wrong:** Right column content overflows below the viewport; panels are cut off or push other content down.

**Why it happens:** The right column needs `overflow-y-auto` but its parent must be `h-full` with the overall layout `h-screen`. If any parent container has `height: auto`, the scrollable container has no height constraint.

**How to avoid:** The layout chain must be: `html/body: h-screen` → `#root: h-full` → App `h-screen flex flex-col` → main area `flex-1 overflow-hidden` → columns `h-full` → right column `overflow-y-auto`. The `#root` in `index.css` currently has `width: 1126px; max-width: 100%; margin: 0 auto` which may constrain the dashboard width — verify this doesn't conflict with the intended full-width two-column layout.

**Warning signs:** Right column panels are not visible; page scrolls as a whole instead of the right column scrolling internally.

**Fix:** The current `index.css` `#root` styles (width: 1126px, margin: 0 auto, border-inline) are from the Vite default — they should be overridden or removed for the dashboard phase since the dashboard needs full viewport width.

### Pitfall 5: WebSocket Event Order Dependency

**What goes wrong:** The WS handler references `store.getState()` to read existing nodes/edges when building updated arrays, but Zustand's `getState()` returns stale state if called synchronously during a render cycle.

**Why it happens:** React batches state updates; reading store state inside a state setter using `set((s) => ...)` is safe, but reading it outside via `getState()` at event dispatch time is also safe (it reads the current committed state). The issue arises if event handlers are bound at mount time and close over stale state.

**How to avoid:** In the WS `onmessage` handler, use the Zustand `set((s) => ...)` form for any state that builds on previous state (e.g., appending to arrays, updating node arrays). Avoid reading `useStore.getState()` and then passing the result to a setter synchronously — use the updater function form.

### Pitfall 6: rule_generating Token Field Name Unknown

**What goes wrong:** The `rule_generating` WebSocket event handler tries to read `data.token` but the actual field is named differently (e.g., `data.content` or `data.chunk`), causing `appendStreamToken(undefined)` which appends the string "undefined".

**Why it happens:** The RuleGenerator streaming implementation in `sentinel/engine/rule_generator.py` determines the exact field name for token chunks. This was not verified during research (the supervisor.py doesn't call rule generation directly — it happens via the confirm route).

**How to avoid:** Read `sentinel/engine/rule_generator.py` at the start of the WS hook implementation plan to confirm the exact data shape for `rule_generating` events before writing the handler.

---

## Code Examples

### Two-Column Layout Shell

```jsx
// App.jsx — Phase 4 layout
export default function App() {
  useWebSocket()

  return (
    <div className="h-screen bg-bg-dark text-text-main font-display flex flex-col overflow-hidden">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        {/* Left column — full height investigation tree */}
        <div className="flex-1 h-full">
          <InvestigationTree />
        </div>
        {/* Right column — stacked panels, internal scroll */}
        <div className="w-[480px] h-full overflow-y-auto border-l border-border-muted flex flex-col gap-0">
          <GateDecisionPanel />
          <AnomalyScoreBar />
          <VerdictBoardTable />
          <ForensicScanPanel />
          <RuleSourcePanel />
          <AerospikeLatency />
        </div>
      </div>
    </div>
  )
}
```

### Gate Decision Panel (GO/NO-GO/ESCALATE)

```jsx
const DECISION_STYLES = {
  'GO':       { color: 'text-success', symbol: '✓' },
  'NO-GO':    { color: 'text-danger',  symbol: '⛔' },
  'ESCALATE': { color: 'text-warning', symbol: '⚠' },
}

export default function GateDecisionPanel() {
  const gateDecision = useStore((s) => s.gateDecision)
  const currentEpisodeId = useStore((s) => s.currentEpisodeId)
  const ruleStreaming = useStore((s) => s.ruleStreaming)

  const [confirmed, setConfirmed] = useState(false)

  async function handleConfirm() {
    setConfirmed(true)
    await fetch('/api/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ episode_id: currentEpisodeId, attack_type: 'prompt_injection_hidden_text' }),
    })
  }

  if (!gateDecision) return <EmptyGateDecision />

  const style = DECISION_STYLES[gateDecision.decision] ?? DECISION_STYLES['GO']
  return (
    <div className="p-4 border-b border-border-muted">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-1">Gate Decision</p>
      <div className={`text-xl font-semibold ${style.color}`}>
        {style.symbol} {gateDecision.decision}
        <span className="text-sm font-normal text-text-muted ml-2">Score: {gateDecision.composite_score?.toFixed(2)}</span>
      </div>
      <p className="text-[13px] text-text-main mt-1">{gateDecision.attribution}</p>
      {gateDecision.decision === 'NO-GO' && (
        <button
          onClick={handleConfirm}
          disabled={confirmed}
          className="mt-3 bg-accent text-white font-semibold text-sm px-4 py-2 rounded disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {confirmed ? (ruleStreaming ? 'Generating rule...' : 'Rule generating...') : 'Confirm Attack — Learn ▶'}
        </button>
      )}
    </div>
  )
}
```

### Attack trigger buttons in header

```jsx
function AttackButtons() {
  const investigationStatus = useStore((s) => s.investigationStatus)
  const isRunning = investigationStatus === 'running'

  async function runAttack(scenario) {
    const fixtures = scenario === 'phase1' ? ATTACK1_PAYLOAD : ATTACK2_PAYLOAD
    await fetch('/api/investigate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ payment_request: fixtures, scenario }),
    })
  }

  return (
    <div className="flex gap-2">
      {['phase1', 'phase2'].map((s, i) => (
        <button
          key={s}
          onClick={() => runAttack(s)}
          disabled={isRunning}
          className="text-xs font-mono px-3 py-1.5 rounded border border-border-muted bg-surface text-text-main hover:border-accent disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {i === 0 ? 'Run Attack 1 — Invoice Injection' : 'Run Attack 2 — Identity Spoofing'}
        </button>
      ))}
    </div>
  )
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `reactflow` npm package | `@xyflow/react` | v12 (2023) | Old package still works but misses v12 features; already using correct package from Phase 1 |
| ReactFlow uncontrolled mode | Controlled mode with `onNodesChange` | v11+ | Controlled mode required for store-driven node state |
| Socket.io for real-time | Native browser WebSocket | Always standard for demos | 5 lines, no library, already in Vite proxy config |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Vite dev server | ✓ | Check at runtime | — |
| Vite dev server | Frontend hot reload | ✓ | 8.x (Phase 1) | — |
| FastAPI backend | WebSocket connection | ✓ | Phase 2/3 complete | — |
| invoice_clean.png | DASH-04 | ✓ | fixture from Phase 1 | "No documents attached" placeholder |
| invoice_forensic.png | DASH-04 | ✓ | fixture from Phase 1 | "No documents attached" placeholder |
| @xyflow/react | DASH-01/02 | ✓ | 12.4.4 | — |
| zustand | All panels | ✓ | 5.x | — |
| Material Symbols CDN | Node icons | Network-dependent | CDN | Text labels only if CDN unavailable |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** Material Symbols CDN requires internet access at browser load time. For demo: pre-loaded in browser cache from prior page visit. If offline demo environment required, self-host the icon font.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (backend); no frontend test framework configured |
| Config file | `pyproject.toml` (pytest section) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-01 | Investigation tree renders and node state updates | manual-only | — | — |
| DASH-02 | Rule node appears after rule_deployed event | manual-only | — | — |
| DASH-03 | Verdict board table displays claims_checked | manual-only | — | — |
| DASH-04 | Forensic scan images render side-by-side | manual-only | — | — |
| DASH-05 | Rule source panel shows Python + provenance | manual-only | — | — |
| DASH-06 | Trust score bar animates | manual-only | — | — |
| DASH-07 | Gate decision displays with attribution | manual-only | — | — |
| DASH-08 | Decision log shows timestamped entries | manual-only | — | — |
| DASH-09 | Aerospike latency metric updates live | manual-only | — | — |
| DASH-10 | Prediction vs. actual inline in verdict table | manual-only | — | — |
| DASH-11 | Anomaly score bar segments color-coded | manual-only | — | — |
| VOICE-04 | All voice-narrated info visible on screen | manual-only | — | — |

**Justification for manual-only:** All DASH requirements are visual/interactive behaviors in a React SPA. No frontend testing framework (Vitest, Jest, Playwright) is configured or installed. Setting one up is out of scope for a 72-hour solo build. The verification strategy is: run both attack scenarios end-to-end and visually confirm each panel updates correctly.

**Backend smoke test applicable to Phase 4:**
`pytest tests/test_api.py -x -q` — confirms the /investigate and /confirm routes respond correctly; the WebSocket events they emit drive the dashboard.

### Sampling Rate

- **Per task commit:** `pytest tests/test_api.py tests/test_end_to_end_loop.py -x -q` (backend event emission)
- **Per wave merge:** `pytest tests/ -x -q` (full backend suite)
- **Phase gate:** Full backend suite green + manual browser walkthrough of both attack scenarios

### Wave 0 Gaps

None — existing test infrastructure covers all backend event emission (test_api.py, test_end_to_end_loop.py). No new test files required for this phase.

---

## Open Questions

1. **`rule_generating` token field name**
   - What we know: The confirm route streams via RuleGenerator and broadcasts `rule_generating` events via `ws_broadcast(event, data, episode_id)`
   - What's unclear: The exact key inside `data` that holds the token text chunk (likely `token`, `content`, or `chunk`)
   - Recommendation: The first task in the WebSocket hook plan must read `sentinel/engine/rule_generator.py` to confirm the data shape before writing the `rule_generating` case

2. **`index.css` `#root` width constraint**
   - What we know: `#root` has `width: 1126px; max-width: 100%; margin: 0 auto; border-inline: 1px solid var(--border)` from the Vite default, which was left in place from Phase 1 scaffold
   - What's unclear: Whether this constraint interferes with the full-width two-column layout
   - Recommendation: Override or remove the `#root` width/margin/border-inline styles in `index.css` for the dashboard phase; replace with `width: 100%; height: 100vh` to enable full-viewport layout

3. **Fixture image serving path**
   - What we know: Images exist at `sentinel/fixtures/invoice_clean.png` and `sentinel/fixtures/invoice_forensic.png`
   - What's unclear: Whether the planner chooses FastAPI static mount vs. copy-to-frontend-public
   - Recommendation: Copy to `frontend/public/` during Phase 4 Wave 0 setup — zero backend changes, simpler, confirmed works with Vite

4. **Attack payload hardcoding in frontend**
   - What we know: The header buttons call `POST /investigate` with a fixture payload; D-04 specifies "zero form inputs"
   - What's unclear: Whether the attack payloads should be inline JS constants in the component or loaded from a JSON file
   - Recommendation: Inline JS constants in the AttackButtons component — sufficient for demo, no file loading complexity

---

## Project Constraints (from CLAUDE.md)

The following CLAUDE.md directives apply to Phase 4 dashboard work:

| Directive | Impact on Phase 4 |
|-----------|-------------------|
| React 18.x (not 19) | Already installed; do not upgrade |
| @xyflow/react 12.4.4 (not `reactflow` old name) | Already installed; use correct import |
| Tailwind CDN v3 (not npm, not v4) | Already configured; no new Tailwind config changes |
| No Socket.io — native browser WebSocket only | Implement `useWebSocket` with raw `new WebSocket()` |
| No LangChain/LlamaIndex | N/A to frontend |
| Demo reliability: self-improvement loop must be bulletproof before polish | The investigate → confirm → rule_generated → rule_deployed flow must work before any visual polish |
| Aerospike latency must be visible on dashboard | DASH-09 is a hard requirement, not optional |
| Voice deferred to Phase 5 — but VOICE-04 (text fallback always present) is in Phase 4 scope | All information panels must display data even if Bland AI is not running |
| Safety Gate block decision is an if-statement — no LLM in enforcement path | N/A to frontend; confirmed — frontend only reads gate_result values, never triggers them |

---

## Sources

### Primary (HIGH confidence)

- `frontend/src/App.jsx` — existing scaffold, established patterns confirmed
- `frontend/src/store.js` — existing Zustand store shape confirmed
- `frontend/index.html` — Tailwind config + font/icon CDN confirmed
- `.planning/phases/04-dashboard/04-CONTEXT.md` — locked decisions
- `.planning/phases/04-dashboard/04-UI-SPEC.md` — component visual contract
- `sentinel/schemas/events.py` — all 9 EventType literals confirmed
- `sentinel/agents/supervisor.py` — all broadcast() call sites + exact data shapes confirmed
- `sentinel/api/routes/confirm.py` — rule_deployed payload shape confirmed
- `sentinel/api/websocket.py` — broadcast() signature confirmed
- `.planning/phases/01-foundation/01-03-SUMMARY.md` — Phase 1 decisions confirmed

### Secondary (MEDIUM confidence)

- @xyflow/react v12 controlled mode pattern — applyNodeChanges/applyEdgeChanges pattern from official docs (reactflow.dev)
- `sentinel/fixtures/invoice_clean.png`, `invoice_forensic.png` — existence confirmed via glob; image content not inspected

### Tertiary (LOW confidence)

- `rule_generating` data field name — NOT verified; `sentinel/engine/rule_generator.py` not read during research; flagged as Open Question 1

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified as installed from Phase 1
- Architecture patterns: HIGH — WS event shapes verified from backend source; component structure follows locked CONTEXT.md decisions
- WebSocket event payloads: HIGH for all events except `rule_generating` token field (LOW — not verified)
- Pitfalls: HIGH — based on direct code inspection of existing scaffold and Tailwind CDN behavior
- Forensic image serving: MEDIUM — images confirmed to exist; serving path decision deferred to planner

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (stable stack, no fast-moving dependencies)
