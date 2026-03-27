# Phase 8: Sponsor Integrations, Demo UX, and Deployment Prep - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning
**Source:** Direct discussion with user (conversation context)

<domain>
## Phase Boundary

This phase delivers four capabilities:
1. Auth0 dashboard login (sponsor integration)
2. Guided demo UX flow with scenario screens
3. Self-improvement tree animations (visual proof of learning)
4. Slack webhook reports + Vercel deployment prep

The backend + Aerospike AWS deployment (Phase 9) is out of scope — this phase only prepares the codebase to work behind a single Vercel URL with API rewrites to an EC2 backend.

</domain>

<decisions>
## Implementation Decisions

### Auth0 Integration
- **Locked:** Auth0 protects the dashboard entry point — SRE operator logs in before seeing any data
- **Locked:** Auth0 is the FIRST screen in the demo flow (before any attack scenarios)
- **Locked:** Auth0 does NOT gate the /api/confirm endpoint — the confirm action runs without re-auth
- **Locked:** Use Auth0 React SDK (@auth0/auth0-react) for frontend, auth0 Python SDK for backend JWT verification
- **Locked:** Free tier Auth0 account — create a Single Page Application in Auth0 dashboard
- **Claude's Discretion:** Whether to use Auth0 Universal Login (redirect) or embedded Lock widget

### Guided Demo Flow
- **Locked:** The flow is linear and sequential:
  1. Auth0 login screen
  2. Attack 1 scenario screen (explains invoice injection)
  3. Attack 1 investigation dashboard
  4. Self-improvement learning moment (confirm → rule generated → tree animates)
  5. Attack 2 scenario screen (explains identity spoofing)
  6. Attack 2 investigation dashboard (generated rule fires)
- **Locked:** Scenario screens appear BEFORE the investigation runs — they explain what attack is about to be demonstrated
- **Locked:** Scenario screens are NOT the same as the existing forensic intro screen (Phase 7) — they are attack-specific context screens
- **Claude's Discretion:** Visual design of scenario screens (cards, full-page, modal)
- **Claude's Discretion:** Whether scenario screens auto-advance or require button click

### Self-Improvement Tree Animation
- **Locked:** When rule_generated or rule_deployed WS event fires, the investigation tree (@xyflow/react) must:
  1. Animate with an orange pulse (living, breathing visual)
  2. Add a new node representing the generated/evolved rule
  3. This node persists into Attack 2 as proof the system learned
- **Locked:** The new node should be visually distinct from investigation nodes (different color, icon, or shape)
- **Claude's Discretion:** Animation duration, easing, exact orange shade
- **Claude's Discretion:** Whether rule node appears with an edge connecting it to the Safety Gate node

### Slack Webhook
- **Locked:** Direct httpx.post() to Slack Incoming Webhook — no Airbyte involvement
- **Locked:** Channel: #payment-system-infosec (configured via webhook URL, not code)
- **Locked:** Report includes: decision, composite score, agent verdict summaries, rules fired
- **Locked:** Run 2 report includes a "Self-Improvement Arc" block (generated rule fired)
- **Locked:** send_investigation_report() already exists in sentinel/integrations/slack_reporter.py — extend it with richer content
- **Claude's Discretion:** Block Kit layout and formatting details

### Vercel Deployment Prep
- **Locked:** Frontend builds for Vercel (React static build, `npm run build`)
- **Locked:** vercel.json with rewrites: /api/* -> EC2 backend URL
- **Locked:** VITE_API_URL env var for API base URL (Vercel environment variable)
- **Locked:** VITE_WS_URL env var for WebSocket URL (direct to EC2, Vercel can't proxy WS)
- **Locked:** Frontend code must handle configurable API/WS URLs (no hardcoded localhost)
- **Claude's Discretion:** Whether to use Vercel CLI or Git-based deployment

### Airbyte
- **Locked:** Airbyte is CUT from scope — no PyAirbyte, no DuckDB cache, no Airbyte panel
- **Locked:** Remove AirbyteReportPanel if it exists, replace with a simpler report status indicator
- **Locked:** Remove airbyte_cache.py calls from the investigation pipeline

### Target User Narrative
- **Locked:** Target user is SRE operator on-call at 3am
- **Locked:** Value props: auditability, traceability, autonomous security, knowledge enrichment
- **Locked:** All UI copy should reflect this framing (not "cybersecurity tool" but "autonomous agent security for SRE operators")

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Frontend
- `frontend/src/App.jsx` — Main app component, current flow structure
- `frontend/src/store.js` — Zustand state, current voice/report state to replace
- `frontend/src/hooks/useWebSocket.js` — WS event handlers, where to add rule animation triggers
- `frontend/src/components/InvestigationTree.jsx` — @xyflow/react tree, where to add rule nodes

### Backend
- `sentinel/api/routes/investigate.py` — Investigation pipeline, where Slack/Airbyte calls are wired
- `sentinel/integrations/slack_reporter.py` — Existing Slack reporter to enhance
- `sentinel/integrations/airbyte_cache.py` — To be removed or gutted
- `sentinel/agents/supervisor.py` — Supervisor pipeline, where integrations are called post-gate

### Config
- `.env` — Current env vars (ANTHROPIC_API_KEY, AEROSPIKE_NAMESPACE)
- `.env.example` — Template, needs Auth0 + Slack + VITE vars added

### Planning
- `.planning/phases/07-demo-polish-airbyte-integration/07-CONTEXT.md` — Prior Slack decisions (partially superseded)

</canonical_refs>

<specifics>
## Specific Ideas

- Auth0 login should look clean and professional — it's the first thing judges see
- Scenario screens should clearly explain "what is about to happen" in 2-3 sentences + a visual
- The orange tree animation is the single most important visual moment in the demo — it needs to feel alive
- Slack reports should be rich enough that a judge scrolling through #payment-system-infosec sees the full story

</specifics>

<deferred>
## Deferred Ideas

- Airbyte integration (cut from scope entirely)
- Auth0 MFA (unnecessary for demo — basic login sufficient)
- Role-based access control (single SRE operator role is sufficient)
- Slack thread replies (flat channel messages are simpler)
- Vercel Edge Functions for WebSocket (direct EC2 connection is simpler)

</deferred>

---

*Phase: 08-vercel-full-stack-deployment*
*Context gathered: 2026-03-27 via direct discussion*
