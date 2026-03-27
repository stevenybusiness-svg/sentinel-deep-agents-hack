# Phase 8: Sponsor Integrations, Demo UX, and Deployment Prep - Research

**Researched:** 2026-03-27
**Domain:** Auth0 React SDK, Slack Block Kit, @xyflow/react runtime animation, Vercel deployment, frontend flow restructuring
**Confidence:** HIGH (Auth0 SDK, Vercel rewrites, xyflow store patterns confirmed via official docs / npm; Slack Block Kit confirmed via official docs)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Auth0 Integration
- Auth0 protects the dashboard entry point — SRE operator logs in before seeing any data
- Auth0 is the FIRST screen in the demo flow (before any attack scenarios)
- Auth0 does NOT gate the /api/confirm endpoint — the confirm action runs without re-auth
- Use Auth0 React SDK (@auth0/auth0-react) for frontend, auth0 Python SDK for backend JWT verification

#### Guided Demo Flow
- The flow is linear and sequential:
  1. Auth0 login screen
  2. Attack 1 scenario screen (explains invoice injection)
  3. Attack 1 investigation dashboard
  4. Self-improvement learning moment (confirm -> rule generated -> tree animates)
  5. Attack 2 scenario screen (explains identity spoofing)
  6. Attack 2 investigation dashboard (generated rule fires)
- Scenario screens appear BEFORE the investigation runs — they explain what attack is about to be demonstrated
- Scenario screens are NOT the same as the existing forensic intro screen (Phase 7) — they are attack-specific context screens

#### Self-Improvement Tree Animation
- When rule_generated or rule_deployed WS event fires, the investigation tree (@xyflow/react) must:
  1. Animate with an orange pulse (living, breathing visual)
  2. Add a new node representing the generated/evolved rule
  3. This node persists into Attack 2 as proof the system learned
- The new node should be visually distinct from investigation nodes (different color, icon, or shape)

#### Slack Webhook
- Direct httpx.post() to Slack Incoming Webhook — no Airbyte involvement
- Channel: #payment-system-infosec (configured via webhook URL, not code)
- Report includes: decision, composite score, agent verdict summaries, rules fired
- Run 2 report includes a "Self-Improvement Arc" block (generated rule fired)
- send_investigation_report() already exists in sentinel/integrations/slack_reporter.py — extend it with richer content

#### Vercel Deployment Prep
- Frontend builds for Vercel (React static build, `npm run build`)
- vercel.json with rewrites: /api/* -> EC2 backend URL
- VITE_API_URL env var for API base URL (Vercel environment variable)
- VITE_WS_URL env var for WebSocket URL (direct to EC2, Vercel can't proxy WS)
- Frontend code must handle configurable API/WS URLs (no hardcoded localhost)

#### Airbyte
- Airbyte is CUT from scope — no PyAirbyte, no DuckDB cache, no Airbyte panel
- Remove AirbyteReportPanel if it exists, replace with a simpler report status indicator
- Remove airbyte_cache.py calls from the investigation pipeline

#### Target User Narrative
- Target user is SRE operator on-call at 3am
- Value props: auditability, traceability, autonomous security, knowledge enrichment
- All UI copy should reflect this framing (not "cybersecurity tool" but "autonomous agent security for SRE operators")

### Claude's Discretion
- Whether to use Auth0 Universal Login (redirect) or embedded Lock widget
- Visual design of scenario screens (cards, full-page, modal)
- Whether scenario screens auto-advance or require button click
- Animation duration, easing, exact orange shade
- Whether rule node appears with an edge connecting it to the Safety Gate node
- Block Kit layout and formatting details
- Whether to use Vercel CLI or Git-based deployment

### Deferred Ideas (OUT OF SCOPE)
- Airbyte integration (cut from scope entirely)
- Auth0 MFA (unnecessary for demo — basic login sufficient)
- Role-based access control (single SRE operator role is sufficient)
- Slack thread replies (flat channel messages are simpler)
- Vercel Edge Functions for WebSocket (direct EC2 connection is simpler)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PHASE8-01 | Auth0 login protects dashboard access — operator authenticates before seeing any investigation data | Auth0Provider + useAuth0 hook; Universal Login redirect is standard pattern for React SPAs; no backend JWT verification needed for dashboard-only protection |
| PHASE8-02 | Guided flow: scenario screens appear BEFORE each investigation, explaining the attack being demonstrated | App.jsx flow state machine: auth -> scenario1 -> dashboard -> scenario2 -> dashboard; scenario screens are new components inserted before runAttack() |
| PHASE8-03 | Self-improvement visual — when rule is generated/deployed, investigation tree animates (orange pulse) and adds a new node as proof of learning | addRuleNode() already exists in store.js; animation requires CSS @keyframes rule-pulse added to index.html style block; applied to SentinelNode when status='rule_node' |
| PHASE8-04 | Slack webhook posts formatted Block Kit report after each gate evaluation, including agent verdicts and arc narrative on Run 2 | send_investigation_report() exists in slack_reporter.py; needs agent_verdicts param added; Block Kit section+fields pattern supports structured data; conditional arc block on version>1 |
| PHASE8-05 | Full arc QA — Attack 1 -> block -> confirm -> rule generated (tree animates) -> Attack 2 -> generated rule fires -> rule evolves — works end-to-end | Existing pipeline handles this; QA task validates UX flow gates and WebSocket events all fire |
| PHASE8-06 | Vercel deployment prep — vercel.json with API rewrites, VITE_API_URL and VITE_WS_URL env vars, frontend builds cleanly | vercel.json rewrites pattern confirmed; VITE_ env vars work natively with Vite; WS must be direct (Vercel cannot proxy WS) |
| PHASE8-07 | Aerospike latency panel shows real sub-10ms numbers (verified locally with Docker Aerospike) | Existing AerospikeLatency component displays aerospikeLatencyMs from store; no code change needed — verification task |
</phase_requirements>

---

## Summary

Phase 8 adds four independent capabilities on top of the existing working system. The codebase already has the investigation pipeline, WebSocket events, Zustand store, and React components in place. Phase 8 reshapes the frontend flow (add Auth0 gate, add scenario screens, replace Airbyte with direct Slack delivery), enhances the tree animation on rule deployment, enriches the Slack Block Kit report, and prepares static deployment assets for Vercel.

The highest-complexity work is the **Auth0 integration** (new dependency, new environment variables, wraps entire app) and the **guided flow state machine** (replaces the single `showIntro` boolean with a multi-step flow). The tree animation is low-risk — `addRuleNode()` already exists in the store; it only needs a CSS @keyframes pulse applied to the rule_node status. Slack enrichment is additive to existing code. Vercel prep is mechanical (vercel.json + env var parameterization).

**Primary recommendation:** Implement in dependency order: Auth0 first (gates everything), guided flow second (restructures App.jsx), tree animation third (additive), Slack enrichment fourth (additive), Vercel prep last (mechanical).

---

## Current Codebase State

This section documents what exists and what must change — critical for avoiding duplication.

### Existing Components and Their Phase 8 Fate

| File | Current State | Phase 8 Action |
|------|--------------|----------------|
| `frontend/src/App.jsx` | ForensicIntroScreen shown first, then dashboard with attack buttons | Replace `showIntro` boolean with multi-step flow enum: `auth` -> `scenario1` -> `dashboard` -> `scenario2` -> `dashboard2` |
| `frontend/src/components/ForensicIntroScreen.jsx` | Serves as current landing page with forensic comparison + two attack buttons | Keep as-is — it becomes the scenario screen content for Attack 1 (forensic comparison), or replace with new `ScenarioScreen` component |
| `frontend/src/components/AirbyteReportPanel.jsx` | Shows Airbyte+Slack delivery status with "PyAirbyte persists to DuckDB" copy | Replace with `SlackReportPanel` — simpler, honest, shows Slack delivery only |
| `frontend/src/components/InvestigationTree.jsx` | Renders `SentinelNode` with 5 statuses; `rule_node` status = gold border | Add orange pulse CSS animation when status transitions to `rule_node` |
| `frontend/src/store.js` | `addRuleNode()` already exists; appends node at position x=450, y=340+(n-6)*80 | No structural changes needed; `rule_node` status triggers animation |
| `frontend/src/hooks/useWebSocket.js` | `rule_deployed` case calls `addRuleNode()` already | Add orange pulse trigger on `rule_deployed` and `rule_generating` events |
| `sentinel/integrations/airbyte_cache.py` | DuckDB write logic, imported in supervisor.py step 9a | Remove import and call from supervisor.py; keep file but gut it (or delete) |
| `sentinel/integrations/slack_reporter.py` | `send_investigation_report(episode_id, decision, composite_score, attribution)` — 4-param signature | Extend signature to include `agent_verdicts`, `rules_fired`, `generated_rules_fired`, `is_second_run` |
| `sentinel/agents/supervisor.py` step 9a | Calls both `write_episode_to_cache` and `send_investigation_report` | Remove airbyte call; update Slack call signature with richer data |

### WebSocket Events Currently Handled

The `rule_deployed` event already triggers `addRuleNode()` in the store. The animation enhancement is purely visual — the node is added, it just doesn't pulse yet. The `rule_generating` event streams tokens; no node action today.

### URL Hardcoding State

All API calls in the frontend use relative paths (`/api/investigate`, `/api/confirm`). The WebSocket uses `ws://${window.location.host}/ws` — both of these need parameterization for Vercel deployment:

- API calls: replace with `${import.meta.env.VITE_API_URL || ''}/api/investigate` (empty string = same-origin, works for both dev and Vercel-proxied)
- WebSocket: replace with `${import.meta.env.VITE_WS_URL || `ws://${window.location.host}`}/ws`

---

## Standard Stack

### Core (all already installed)
| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| React | 19.2.4 (current in package.json) | Frontend framework | Auth0 SDK 2.16.0 supports React 19 |
| @auth0/auth0-react | 2.16.0 (latest as of 2026-03-27) | Auth0 SPA SDK | Universal Login redirect pattern recommended |
| @xyflow/react | 12.10.1 (current in package.json) | Investigation tree | addRuleNode() already wired in store.js |
| zustand | 5.0.12 | State management | Existing store.js handles all new state needs |
| httpx | (backend dep) | Slack webhook POST | Already used in slack_reporter.py |

### New Dependencies (frontend only)
```bash
# From frontend/ directory:
npm install @auth0/auth0-react
```

No new backend dependencies needed. The `auth0` Python package for backend JWT verification is optional for this phase because Auth0 only gates the dashboard (not /api/confirm). If JWT verification middleware is needed, use `python-jose` (already a transitive dep possibility) or direct httpx introspection — but the CONTEXT.md decision is Auth0 does NOT gate /api/confirm, so backend JWT middleware is out of scope for Phase 8.

### Versions Verified
```
@auth0/auth0-react: 2.16.0 (npm view @auth0/auth0-react version → verified 2026-03-27)
@xyflow/react: 12.10.1 (already installed)
```

---

## Architecture Patterns

### Pattern 1: Auth0 Universal Login (Recommended over Lock widget)

Universal Login is the standard pattern for SPAs. No embedded widget — Auth0 handles the login UI. Cleaner, more professional for judges.

**Setup in main.jsx:**
```jsx
// Source: https://auth0.com/docs/quickstart/spa/react/interactive
import { Auth0Provider } from '@auth0/auth0-react'

root.render(
  <Auth0Provider
    domain={import.meta.env.VITE_AUTH0_DOMAIN}
    clientId={import.meta.env.VITE_AUTH0_CLIENT_ID}
    authorizationParams={{
      redirect_uri: window.location.origin,
    }}
  >
    <App />
  </Auth0Provider>
)
```

**Guard pattern in App.jsx:**
```jsx
// Source: https://auth0.com/docs/quickstart/spa/react/interactive
const { isAuthenticated, isLoading, loginWithRedirect } = useAuth0()

if (isLoading) return <SentinelLoadingScreen />
if (!isAuthenticated) {
  // Show login screen — call loginWithRedirect() on button click
  return <Auth0LoginScreen onLogin={() => loginWithRedirect()} />
}
// Authenticated: show guided flow
```

**Key properties from `useAuth0()`:**
- `isAuthenticated` — boolean, derived from valid session
- `isLoading` — boolean, true while checking session
- `loginWithRedirect()` — triggers Universal Login redirect
- `logout({ logoutParams: { returnTo: window.location.origin } })` — clears session and returns
- `user` — profile object with name, email, picture

### Pattern 2: Multi-Step Demo Flow State Machine

Replace the single `showIntro` boolean in App.jsx with a flow enum. Do NOT put flow state in Zustand — it is UI navigation state, not investigation data state.

```jsx
// App.jsx local state (not Zustand)
const FLOW = {
  AUTH: 'auth',           // Auth0 gate (before anything)
  SCENARIO_1: 'scenario1', // Attack 1 context screen
  DASHBOARD_1: 'dashboard1', // Attack 1 investigation + confirm
  SCENARIO_2: 'scenario2', // Attack 2 context screen
  DASHBOARD_2: 'dashboard2', // Attack 2 investigation
}
const [flow, setFlow] = useState(FLOW.AUTH)
```

**Flow transitions:**
- `AUTH` -> `SCENARIO_1`: after successful Auth0 authentication (isAuthenticated becomes true)
- `SCENARIO_1` -> `DASHBOARD_1`: user clicks "Run Attack 1" on scenario screen (triggers handleAttack1())
- `DASHBOARD_1` -> `SCENARIO_2`: after rule_deployed WS event fires AND operator clicks confirm (or explicit "Next Attack" button)
- `SCENARIO_2` -> `DASHBOARD_2`: user clicks "Run Attack 2" on scenario screen

**Transition from DASHBOARD_1 to SCENARIO_2:** The most natural trigger is a "Proceed to Attack 2" button that appears AFTER rule_deployed fires. The button should not appear until the self-improvement loop completes.

### Pattern 3: Orange Pulse Animation for Rule Node

The rule_node status is already defined in `SentinelNode`. The animation is a CSS @keyframes pulse added to `index.html` (where all other keyframes live) and applied to the node via a conditional class.

**Add to index.html `<style>` block:**
```css
/* Orange pulse for rule nodes (self-improvement visual) */
@keyframes rule-pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(227, 179, 65, 0.7);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(227, 179, 65, 0);
  }
}
.rule-pulse { animation: rule-pulse 1.5s ease-in-out infinite; }
```

**In SentinelNode (InvestigationTree.jsx), case 'rule_node':**
```jsx
// Add .rule-pulse class to the node wrapper div
className={`bg-surface rounded-lg px-3 py-2 ... ${borderClass} ${status === 'rule_node' ? 'rule-pulse' : ''}`}
```

The warning color `#e3b341` (Tailwind `warning`) is the existing gold/amber used for rule nodes — this is appropriate as orange. No need for a new color.

### Pattern 4: Slack Block Kit Rich Report

The existing `send_investigation_report()` sends a 3-block payload. Extend to include agent verdicts as a `section` with `fields`, and a conditional "Self-Improvement Arc" section when `generated_rules_fired` is non-empty.

**New signature:**
```python
async def send_investigation_report(
    episode_id: str,
    decision: str,
    composite_score: float,
    attribution: str,
    agent_verdicts: list[dict] | None = None,
    rules_fired: list[str] | None = None,
    generated_rules_fired: list[str] | None = None,
) -> bool:
```

**Block Kit structure for rich report:**
```json
{
  "blocks": [
    { "type": "header", "text": { "type": "plain_text", "text": "Sentinel: NO-GO — Episode EP-001" } },
    {
      "type": "section",
      "fields": [
        { "type": "mrkdwn", "text": "*Decision:*\n`NO-GO`" },
        { "type": "mrkdwn", "text": "*Score:*\n`1.87`" }
      ]
    },
    { "type": "section", "text": { "type": "mrkdwn", "text": "*Attribution:*\n..." } },
    { "type": "divider" },
    {
      "type": "section",
      "text": { "type": "mrkdwn", "text": "*Agent Verdicts*\n..." }
    },
    /* conditional: only when generated_rules_fired is non-empty */
    { "type": "divider" },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": ":sparkles: *Self-Improvement Arc*\nGenerated Rule #001 fired on this attack..."
      }
    },
    { "type": "context", "elements": [ { "type": "mrkdwn", "text": "Sentinel autonomous investigation pipeline" } ] }
  ]
}
```

**Constraint:** Slack `section.fields` array is limited to 10 items. Agent verdicts should be summarized (agent name + confidence + key finding), not the full verdict object.

### Pattern 5: Vercel deployment prep

**vercel.json** (lives in project root, not frontend/):
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://YOUR_EC2_HOST/api/:path*"
    },
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

Vercel processes rewrites in order — the `/api/:path*` rule must come BEFORE the SPA catch-all `/(.*) -> /index.html`, otherwise all API calls become index.html.

**Critical: Vercel CANNOT proxy WebSocket connections.** The CONTEXT.md decision (VITE_WS_URL direct to EC2) is correct. The WS URL must be a full URL to EC2: `wss://YOUR_EC2_HOST/ws`.

**Frontend env var parameterization:**
- `VITE_API_URL`: base URL for API calls (empty string for same-origin dev, `https://YOUR_EC2_HOST` for direct EC2, empty for Vercel with rewrites)
- `VITE_WS_URL`: WebSocket base URL (`ws://localhost:8000` for dev, `wss://EC2_HOST` for prod)

For Vercel with rewrites, `VITE_API_URL` should be empty string (rewrites handle routing). Only `VITE_WS_URL` needs to be the EC2 address.

**Vercel build configuration:** The `frontend/` subdirectory structure means Vercel needs to be configured with root directory = `frontend/`. This is done in the Vercel dashboard or via `vercel.json` `buildCommand` + `outputDirectory`.

Alternative: place `vercel.json` inside `frontend/` with:
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "rewrites": [...]
}
```

### Anti-Patterns to Avoid

- **Putting flow state in Zustand:** Flow state (which screen is showing) is UI navigation, not investigation data. Local React state is correct.
- **Gating /api/confirm with Auth0 tokens:** CONTEXT.md explicitly says Auth0 does NOT gate /api/confirm. Do not add Authorization headers to confirm calls.
- **Using vercel.json `routes` instead of `rewrites`:** `routes` is a legacy API with different semantics. Use `rewrites` (higher-level, cleaner).
- **Proxying WebSocket through Vercel:** Vercel cannot proxy WebSocket upgrades. Use direct EC2 URL via VITE_WS_URL.
- **Importing airbyte_cache after gutting it:** The import must be fully removed from supervisor.py step 9a, not just guarded.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Auth0 session management | Custom JWT storage, refresh logic | `@auth0/auth0-react` (AuthProvider handles token lifecycle) | Silent refresh, PKCE flow, cookie/localStorage management has security edge cases |
| Auth0 callback handling | Manual URL param parsing after redirect | Auth0Provider handles callback automatically (parses `code`, exchanges for token, clears URL) | Auth0 SDK handles state, nonce, PKCE verifier automatically |
| Pulse animation timing | JS `setInterval` / `setTimeout` for animation | CSS `@keyframes` + `animation: rule-pulse infinite` | Hardware-accelerated, no JS overhead, survives React re-renders |
| Slack message formatting | Custom markdown builder | Slack Block Kit JSON (header/section/fields/divider/context) | Block Kit has 50-block limit per message but no other constraints for incoming webhooks |

---

## Common Pitfalls

### Pitfall 1: Auth0 Callback Loop on First Load

**What goes wrong:** After Auth0 redirect, the `code` param in the URL causes the SDK to process the callback. If the component re-renders during this and calls `loginWithRedirect()` again (e.g., because `isAuthenticated` is still false during processing), it creates a redirect loop.

**Why it happens:** `isLoading` is true during callback processing, but React renders happen between state updates.

**How to avoid:** Always check `isLoading` FIRST, before `isAuthenticated`. Only call `loginWithRedirect()` when `isLoading === false && !isAuthenticated`.

**Warning signs:** Redirect loop in browser, multiple Auth0 "code" exchanges in network tab.

### Pitfall 2: Vercel Rewrite Order — SPA Catch-All Swallows API Calls

**What goes wrong:** If the SPA catch-all `/(.*) -> /index.html` appears BEFORE `/api/:path*` in vercel.json, all API calls return the React app HTML instead of proxying to EC2.

**Why it happens:** Vercel processes rewrites in array order. First match wins.

**How to avoid:** Always put specific API rewrite before the SPA catch-all. Verify with a test POST to `/api/health` after deployment.

### Pitfall 3: VITE_ Env Vars Not Available at Runtime

**What goes wrong:** `import.meta.env.VITE_API_URL` is `undefined` even though you set it in Vercel dashboard.

**Why it happens:** Vite bakes VITE_ env vars into the static build at compile time. You must redeploy after adding env vars — they are not injected at runtime.

**How to avoid:** Always trigger a new build after adding/changing VITE_ env vars in Vercel. Use `import.meta.env.VITE_WS_URL || fallback` pattern to fail gracefully in dev.

### Pitfall 4: WebSocket Protocol Mismatch (ws:// vs wss://)

**What goes wrong:** Browser blocks WebSocket connection from HTTPS page to ws:// URL (mixed content).

**Why it happens:** Vercel frontend is served over HTTPS. WebSocket must use `wss://` from an HTTPS page.

**How to avoid:** Set VITE_WS_URL to `wss://` (not `ws://`) when deploying to Vercel. Dev on localhost still uses `ws://`.

```javascript
// Correct pattern in useWebSocket.js
const wsBase = import.meta.env.VITE_WS_URL || `ws://${window.location.host}`
const ws = new WebSocket(`${wsBase}/ws`)
```

### Pitfall 5: addRuleNode() Position Collision

**What goes wrong:** When two rule nodes are added (rule v1 and rule v2 from evolution), they overlap because the position formula uses `s.nodes.length - 6`.

**Why it happens:** After rule v1 node is added, the node count is 7. Rule v2 gets y = 340 + (7-6)*80 = 420. But if the tree is reset between attacks (`resetInvestigation()` clears nodes), this works correctly.

**How to avoid:** `resetInvestigation()` is already called on `investigation_started`. Rule nodes from Attack 1 are cleared before Attack 2 starts — this is correct behavior per the flow design. The rule node from Attack 1 should persist for the SCENARIO_2 screen (visual proof) but be cleared when Attack 2 investigation starts.

**Decision needed:** Should rule nodes from Attack 1 persist through the Attack 2 investigation, or be cleared? The CONTEXT.md says "this node persists into Attack 2 as proof the system learned." This means `resetInvestigation()` should NOT clear rule nodes — or they should be re-added when the attack 2 investigation tree is initialized.

Recommended approach: Keep `resetInvestigation()` clearing all nodes (existing behavior, safe), and re-add any persisted rule nodes when `initInvestigationTree()` fires for attack 2. Add a `persistedRuleNodes` field to the store that survives `resetInvestigation()`.

### Pitfall 6: Slack Fields Array Limit

**What goes wrong:** Section with `fields` array errors out if more than 10 items.

**Why it happens:** Slack Block Kit limit on section fields.

**How to avoid:** Keep agent verdicts to a 2-field summary per agent: name + decision. 3 agents = 6 fields, well under limit.

### Pitfall 7: Auth0 Free Tier Callback URL Not Registered

**What goes wrong:** Auth0 returns "Callback URL mismatch" error after login.

**Why it happens:** Auth0 SPA applications require explicit allowlist of allowed callback URLs. Localhost and Vercel URL must both be registered.

**How to avoid:** In Auth0 dashboard -> Application Settings, add both `http://localhost:5173` and `https://sentinel-demo.vercel.app` to:
- Allowed Callback URLs
- Allowed Logout URLs
- Allowed Web Origins

---

## Code Examples

### Auth0Provider setup in main.jsx

```jsx
// Source: https://auth0.com/docs/quickstart/spa/react/interactive
import { Auth0Provider } from '@auth0/auth0-react'

root.render(
  <Auth0Provider
    domain={import.meta.env.VITE_AUTH0_DOMAIN}
    clientId={import.meta.env.VITE_AUTH0_CLIENT_ID}
    authorizationParams={{ redirect_uri: window.location.origin }}
  >
    <App />
  </Auth0Provider>
)
```

### Auth0 guard pattern in App.jsx

```jsx
// Check isLoading FIRST to prevent redirect loop
const { isAuthenticated, isLoading, loginWithRedirect } = useAuth0()

if (isLoading) {
  return <div className="h-screen bg-bg-dark flex items-center justify-center">
    <span className="text-text-muted text-sm">Authenticating...</span>
  </div>
}

if (!isAuthenticated) {
  return <LoginScreen onLogin={() => loginWithRedirect()} />
}
```

### Parameterized WebSocket URL

```javascript
// frontend/src/hooks/useWebSocket.js
const wsBase = import.meta.env.VITE_WS_URL || `ws://${window.location.host}`
const ws = new WebSocket(`${wsBase}/ws`)
```

### Parameterized API fetch

```javascript
// Pattern for App.jsx and any component making API calls
const apiBase = import.meta.env.VITE_API_URL || ''
await fetch(`${apiBase}/api/investigate`, { ... })
```

### vercel.json (place in project root or frontend/)

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://YOUR_EC2_IP/api/:path*"
    },
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

Note: When VITE_API_URL is empty and vercel.json proxies `/api/*`, the EC2 URL only appears in vercel.json — not embedded in the JS bundle. This is the correct pattern.

### Slack Block Kit agent verdict summary

```python
# Source: https://docs.slack.dev/block-kit/ (verified Block Kit section+fields pattern)
def _build_verdict_fields(agent_verdicts: list[dict]) -> list[dict]:
    fields = []
    for v in (agent_verdicts or [])[:5]:  # cap at 5 agents, 10 fields max
        agent_id = v.get("agent_id", "unknown")
        confidence = v.get("agent_confidence", 0.0)
        flags = len(v.get("behavioral_flags", []))
        fields.append({
            "type": "mrkdwn",
            "text": f"*{agent_id.title()}:*\nConf: `{confidence:.2f}` | Flags: `{flags}`"
        })
    return fields
```

### Orange pulse CSS @keyframes

```css
/* Add to index.html <style> block */
@keyframes rule-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(227, 179, 65, 0.7); }
  50%       { box-shadow: 0 0 0 8px rgba(227, 179, 65, 0); }
}
.rule-pulse { animation: rule-pulse 1.5s ease-in-out infinite; }
```

### persistedRuleNodes pattern for cross-attack persistence

```javascript
// store.js additions
persistedRuleNodes: [],  // survives resetInvestigation()
addPersistedRuleNode: (node) => set((s) => ({
  persistedRuleNodes: [...s.persistedRuleNodes, node]
})),

// Modified initInvestigationTree: re-add persisted rule nodes
initInvestigationTree: () => set((s) => {
  const baseNodes = [ /* ...existing 6 nodes... */ ]
  const baseEdges = [ /* ...existing edges... */ ]
  // Re-add any rule nodes from previous attacks
  const ruleNodes = s.persistedRuleNodes
  const ruleEdges = ruleNodes.map(rn => ({
    id: `e-gate-${rn.id}`,
    source: 'gate',
    target: rn.id,
    animated: true,
    style: { stroke: '#e3b341' },
  }))
  return { nodes: [...baseNodes, ...ruleNodes], edges: [...baseEdges, ...ruleEdges] }
}),
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | npm install @auth0/auth0-react | Yes | v24.13.1 | — |
| @auth0/auth0-react | PHASE8-01 | Not installed yet | 2.16.0 (latest) | — |
| Docker (Aerospike) | PHASE8-07 latency verification | Assumed yes (was used in Phase 6) | — | — |
| Auth0 free tier account | PHASE8-01 | Must be created | — | No fallback — judge requirement |
| Slack Incoming Webhook URL | PHASE8-04 | Must be configured | — | Silent skip (existing behavior in slack_reporter.py) |

**Missing dependencies requiring human action before execution:**
- Auth0 free tier account: create at auth0.com, create a Single Page Application, copy domain + clientId
- Slack Incoming Webhook URL: create at api.slack.com, configure for #payment-system-infosec channel

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x with pytest-asyncio |
| Config file | pyproject.toml (`asyncio_mode = "auto"`, `testpaths = ["tests"]`) |
| Quick run command | `pytest tests/test_airbyte_slack.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PHASE8-01 | Auth0 SDK installed, AuthProvider renders without error | smoke | Manual browser check (no unit test needed for SDK wiring) | N/A — browser only |
| PHASE8-04 | Slack reporter sends richer payload with agent verdicts | unit | `pytest tests/test_airbyte_slack.py -x -q` | Yes (test_airbyte_slack.py exists) |
| PHASE8-04 | Conditional self-improvement arc block appears when generated_rules_fired non-empty | unit | `pytest tests/test_airbyte_slack.py -x -q` | Yes — extend existing test |
| PHASE8-06 | VITE_API_URL / VITE_WS_URL env vars consumed by Vite build | smoke | `cd frontend && npm run build` (no errors) | N/A — build check |

### Wave 0 Gaps
- [ ] `tests/test_airbyte_slack.py` — existing file covers send_investigation_report(); extend tests for new parameters (agent_verdicts, generated_rules_fired conditional block)

---

## Airbyte Removal Checklist

This is a concrete, safe-to-execute list of all places Airbyte must be removed:

1. `sentinel/agents/supervisor.py` line ~1039: Remove `from sentinel.integrations.airbyte_cache import write_episode_to_cache`
2. `sentinel/agents/supervisor.py` lines ~1041-1046: Remove `await write_episode_to_cache(...)` call
3. `frontend/src/components/AirbyteReportPanel.jsx`: Replace or rename to `SlackReportPanel.jsx` — keep same status indicator UI, remove Airbyte copy
4. `frontend/src/App.jsx` line 12: Replace `import { AirbyteReportPanel }` with `import { SlackReportPanel }`
5. `sentinel/integrations/airbyte_cache.py`: Can be deleted or gutted — not needed by any other module
6. `requirements.txt` / `pyproject.toml`: Remove `airbyte` and `duckdb` if present

Verify `duckdb` is not imported anywhere else before removing:
```bash
grep -r "duckdb\|airbyte" sentinel/ --include="*.py" | grep -v airbyte_cache.py
```

---

## Sources

### Primary (HIGH confidence)
- [auth0.com/docs/quickstart/spa/react/interactive](https://auth0.com/docs/quickstart/spa/react/interactive) — Auth0Provider setup, useAuth0 hook properties, Universal Login pattern
- [auth0.github.io/auth0-react/](https://auth0.github.io/auth0-react/) — Auth0ProviderOptions interface, full API reference
- [vercel.com/docs/project-configuration/vercel-json](https://vercel.com/docs/project-configuration/vercel-json) — rewrites format, rewrite ordering, external URL destination syntax
- [docs.slack.dev/block-kit/](https://docs.slack.dev/block-kit/) — Block Kit types: header/section/fields/divider/context, 10-item fields limit

### Secondary (MEDIUM confidence)
- [reactflow.dev/api-reference/hooks/use-react-flow](https://reactflow.dev/api-reference/hooks/use-react-flow) — addNodes() pattern (current store.js uses setNodes directly, which is equivalent)
- npm: `@auth0/auth0-react` version 2.16.0 verified via `npm view @auth0/auth0-react version` on 2026-03-27
- npm: `@xyflow/react` version 12.10.1 confirmed from frontend/package.json

### Tertiary (LOW confidence)
- WebSearch result: Vercel cannot proxy WebSocket — confirmed consistent with official Vercel rewrites docs (no WS proxy support in rewrites)

---

## Metadata

**Confidence breakdown:**
- Auth0 SDK setup: HIGH — official docs + npm version verified
- xyflow/react animation: HIGH — existing code pattern (addRuleNode in store.js), CSS @keyframes standard
- Slack Block Kit: HIGH — official docs, fields array limit documented
- Vercel rewrites: HIGH — official vercel.json docs, rewrite order confirmed
- Airbyte removal: HIGH — all import sites found via grep, no hidden consumers

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable libraries, Auth0 SDK, Vercel config format)
