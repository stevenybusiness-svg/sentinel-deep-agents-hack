"""Slack Incoming Webhook reporter for autonomous investigation reports.

Sends Block Kit formatted investigation reports to Slack after each gate evaluation.
Demonstrates autonomous report delivery for Slack integration judges.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

_PLACEHOLDER_PREFIX = "https://hooks.slack.com/services/YOUR"


def _build_verdict_fields(agent_verdicts: list[dict]) -> list[dict]:
    """Build Block Kit fields for agent verdicts (max 10 fields, max 5 agents)."""
    fields = []
    for verdict in agent_verdicts[:5]:
        agent_id = verdict.get("agent_id", "unknown")
        confidence = verdict.get("confidence", 0.0)
        flags = verdict.get("flags", [])
        flag_count = len(flags) if isinstance(flags, list) else 0

        agent_label = agent_id.replace("_", " ").title()
        fields.append({
            "type": "mrkdwn",
            "text": f"*{agent_label}*\nConfidence: `{confidence:.2f}` | Flags: `{flag_count}`",
        })
    return fields


_ATTACK_LABELS: dict[str, str] = {
    "prompt_injection_hidden_text": "Prompt Injection — Hidden Text Manipulation",
    "identity_spoofing": "Identity Spoofing — KYC Pre-Clearance Forgery",
}


async def send_investigation_report(
    episode_id: str,
    decision: str,
    composite_score: float,
    attribution: str,
    agent_verdicts: list[dict] | None = None,
    rules_fired: list[str] | None = None,
    generated_rules_fired: list[str] | None = None,
    attack_narrative: str | None = None,
    agent_reasoning: str | None = None,
    prediction_summary: str | None = None,
    attack_type: str | None = None,
) -> bool:
    """Send investigation report to Slack via Incoming Webhook.

    Returns True if the webhook POST returned 200, False otherwise.
    Silently returns False if SLACK_WEBHOOK_URL is not configured or is a placeholder.

    Args:
        episode_id: Unique episode identifier.
        decision: Gate decision (GO / NO-GO / ESCALATE).
        composite_score: Composite anomaly score from Safety Gate.
        attribution: Human-readable attribution chain from Safety Gate.
        agent_verdicts: List of agent verdict dicts with agent_id, confidence, flags.
        rules_fired: List of all rule IDs that contributed to the gate decision.
        generated_rules_fired: Subset of rules_fired that are generated (not hardcoded).
        attack_narrative: Plain-English summary of what happened (from narrative template).
        agent_reasoning: Per-agent finding summary (from narrative template).
        prediction_summary: Prediction vs. actual divergence summary (from narrative template).
    """
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
    if not webhook_url or webhook_url.startswith(_PLACEHOLDER_PREFIX):
        return False

    color = (
        "#f85149" if decision == "NO-GO"
        else "#e3b341" if decision == "ESCALATE"
        else "#3fb950"
    )
    _ = color  # reserved for future attachment color support

    # Header block — show attack type as title
    attack_label = _ATTACK_LABELS.get(attack_type or "", f"Attack Detected ({decision})")
    header_text = f":rotating_light: {attack_label}"

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": header_text,
                "emoji": True,
            },
        },
        # Decision + Score fields
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Decision*\n`{decision}`",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Composite Score*\n`{composite_score:.2f}`",
                },
            ],
        },
        # Attribution
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Attribution*\n{attribution}",
            },
        },
        {"type": "divider"},
    ]

    # Key Findings section — top 3 qualitative findings in plain English
    findings_bullets: list[str] = []
    if attack_narrative:
        findings_bullets.append(attack_narrative)
    if agent_reasoning:
        findings_bullets.append(agent_reasoning)
    if prediction_summary:
        findings_bullets.append(prediction_summary)

    if findings_bullets:
        # Build bullet-point list (up to 3 items)
        bullet_text = "\n".join(f"\u2022 {f}" for f in findings_bullets[:3])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Key Findings*\n{bullet_text}",
            },
        })
        blocks.append({"type": "divider"})

    # Agent verdicts section
    if agent_verdicts:
        verdict_fields = _build_verdict_fields(agent_verdicts)
        if verdict_fields:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Agent Verdicts*",
                },
                "fields": verdict_fields,
            })

    # Self-Improvement Arc (conditional — only when generated rules fired)
    if generated_rules_fired:
        rule_list = ", ".join(f"`{r}`" for r in generated_rules_fired)
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":sparkles: *Self-Improvement Arc*\n"
                    f"Generated rules fired on this attack: {rule_list}. "
                    "These rules were autonomously written by Sentinel after a previous confirmed incident "
                    "and caught this attack via the same behavioral fingerprint."
                ),
            },
        })

    # Context block
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "Generated by Sentinel autonomous investigation pipeline",
            }
        ],
    })

    payload = {
        "text": f"Sentinel Investigation Report - Episode {episode_id}",
        "blocks": blocks,
    }
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(webhook_url, json=payload, timeout=5.0)
            return r.status_code == 200
    except Exception:
        return False
