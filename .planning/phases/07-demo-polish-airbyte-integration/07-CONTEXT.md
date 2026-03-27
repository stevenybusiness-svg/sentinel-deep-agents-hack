---
phase: 07-demo-polish-airbyte-integration
type: context
created: 2026-03-27
scope: Slack integration enhancement — richer report content for Run 1 and Run 2
---

# Phase 07 — Slack Integration Context

> Decisions captured to guide implementation of enhanced Slack report delivery.
> Plan 02 covers the base integration (webhook, DuckDB cache, AirbyteReportPanel).
> These decisions govern the **content** and **arc narrative** shape of the reports.

---

## What's Already Decided (Plan 02 — do not re-litigate)

- **Delivery mechanism:** Slack Incoming Webhook via `httpx.AsyncClient.post` — no `slack_sdk`, no Canvas API
- **Trigger point:** After `gate_evaluated` WS event fires in `sentinel/api/routes/investigate.py`
- **Format:** Slack Block Kit (`blocks` array in JSON payload) with `mrkdwn` text fields
- **Airbyte layer:** PyAirbyte / DuckDB cache write before Slack POST (episode persistence)
- **Frontend:** `AirbyteReportPanel` replaces `VoicePanel`; `report_delivered` WS event updates status
- **Guard:** Returns `False` immediately if `SLACK_WEBHOOK_URL` is empty or placeholder — never blocks pipeline
- **Channel:** #payment-system-infosec — set by which webhook URL is configured; no code change needed

---

## New Decisions — Report Content & Arc Narrative

### Decision 1: Report content must include full investigation breakdown

**Locked:** YES

The current Plan 02 sends only: `episode_id`, `decision`, `composite_score`, `attribution`.

The report must include:
- Gate decision + composite score (already in Plan 02)
- **Risk agent verdict summary** — extracted from `verdict_board` or `agent_outputs` (1-2 sentences)
- **Compliance agent verdict summary** — same
- **Forensics agent verdict summary** — same (+ flag if hidden text was detected)
- **Rules fired** — list of rule IDs/names that contributed to the composite score
- **Generated rules fired** (if any) — highlighted distinctly as "AI-generated detection"

The `send_investigation_report` function signature must be extended to accept these fields. The caller in `investigate.py` must pass them from the gate result.

---

### Decision 2: Run 2 report must tell the self-improvement arc story

**Locked:** YES

After **Run 2 (identity spoofing attack)** completes, the Slack report must include an arc section that was absent from Run 1:

```
*Self-Improvement Arc:*
Run 1 (invoice injection) → Generated rule deployed
Run 2 (identity spoofing) → Generated rule FIRED → Rule evolved
```

**How to detect Run 2:** Check if `generated_rules_fired` is non-empty in the gate result. If generated rules fired, this is Run 2 (or later) — add the arc block. If empty, this is Run 1 — omit the arc block.

This is the key narrative for the Airbyte judges: the system didn't just detect the second attack — it detected it with a rule it wrote itself.

---

### Decision 3: Format is Markdown (mrkdwn) within Block Kit — NOT Slack Canvas

**Locked:** YES

Slack Canvas requires a Slack API token (not just an Incoming Webhook URL). Incoming Webhooks cannot create Canvases. Since we only have a webhook URL, Canvas is not viable.

Use structured Block Kit sections with `mrkdwn` type:
- Header block: `"Sentinel: {decision} — Episode {episode_id}"`
- Section block: Decision, score, rules fired
- Section block: Agent verdict summaries (risk / compliance / forensics)
- Context block (conditional, Run 2 only): Self-improvement arc callout
- Footer: `"Airbyte → DuckDB cache → Slack delivery"`

---

### Decision 4: One report per run, not one combined report after both

**Locked:** YES

Send one report after each individual gate evaluation. The arc story is told within each report's content (Run 1 has no arc block; Run 2 has the arc block). Do not wait for both runs to complete before sending — that would require stateful run counting and is brittle for a live demo.

---

## Data Flow for Extended Report

```
gate_evaluated event
  → gate_result (decision, composite_score, attribution, rules_fired, generated_rules_fired)
  → verdict_board (agent outputs from Risk/Compliance/Forensics)
       ↓
write_episode_to_cache(episode_id, decision, composite_score, attribution, agent_summaries)
       ↓
send_investigation_report(
    episode_id,
    decision,
    composite_score,
    attribution,
    risk_summary,       # NEW
    compliance_summary, # NEW
    forensics_summary,  # NEW
    rules_fired,        # NEW
    generated_rules_fired, # NEW — triggers arc block if non-empty
)
       ↓
ws_manager.broadcast("report_delivered", episode_id, {"channel": "slack", "success": bool})
```

---

## Where to Extract Agent Summaries

The `verdict_board` dict in `investigate.py` holds each agent's structured output. After the gate runs:
- `verdict_board.get("risk_assessment", {}).get("summary", "")` or equivalent field
- `verdict_board.get("compliance_check", {}).get("summary", "")` or equivalent field
- `verdict_board.get("forensic_scan", {}).get("summary", "")` or equivalent field

**Note for implementer:** Read `sentinel/api/routes/investigate.py` to confirm exact field names before implementing. Do not assume field names — verify against the actual gate result structure.

---

## Scope Boundary — Deferred Ideas

- **Slack Canvas:** Not viable with webhook-only auth. Deferred to v2 if Slack API token is added.
- **Combined arc summary after both runs:** Deferred — per-run reports with arc detection is sufficient for demo.
- **Airbyte Cloud sync:** Deferred — local DuckDB is sufficient for demo; Cloud sync adds no judge value in 72h.
- **Slack thread replies:** Deferred — flat channel messages are simpler and just as visible.

---

## Downstream Agent Instructions

**For executor implementing Plan 02:**
1. Extend `send_investigation_report()` signature with `risk_summary`, `compliance_summary`, `forensics_summary`, `rules_fired`, `generated_rules_fired` params (all with default `""` / `[]` so existing tests don't break)
2. Build arc block conditionally: `if generated_rules_fired:` append the self-improvement arc context block
3. Update the call site in `investigate.py` to pass these fields from the gate result
4. Update `test_airbyte_slack.py` to test the arc block appears when `generated_rules_fired` is non-empty
5. Do NOT add Canvas API — Incoming Webhook only
