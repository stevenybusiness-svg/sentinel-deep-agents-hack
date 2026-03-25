"""
Payment Agent module -- tool definitions, tool call handler, and response parser.

Per D-03: This module does NOT contain an autonomous multi-turn conversation loop.
The Supervisor (Opus 4.6, Plan 02-06) drives the Payment Agent's conversation
turn-by-turn. This module provides the building blocks only.

Exports:
    PAYMENT_TOOLS           -- list of 3 tool definitions for Sonnet 4.6
    PAYMENT_AGENT_SYSTEM_PROMPT -- system prompt for the Payment Agent
    handle_tool_call        -- execute a single tool call against fixtures
    parse_payment_decision  -- extract PaymentDecision from final response text
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

from sentinel.fixtures import FixtureData
from sentinel.schemas.payment import PaymentDecision

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

PAYMENT_AGENT_SYSTEM_PROMPT: str = (
    "You are a payment processing agent. You analyze payment requests by verifying "
    "counterparty authorization, KYC status, and invoice documentation. Use the "
    "available tools to gather information, then make a decision to approve or deny "
    "the payment. Respond with your analysis including your confidence level and the "
    "claims you verified.\n\n"
    'When you have gathered enough information, provide your final decision in this '
    'JSON format:\n'
    '{"decision": "approve" or "deny", "amount": <float>, "beneficiary": "<name>", '
    '"account": "<account>", "rationale": "<your reasoning>", '
    '"confidence": <0.0-1.0>, "claims": {"<field>": "<value>"}}'
)

# ---------------------------------------------------------------------------
# Tool definitions (per D-01) -- 3 tools for the Sonnet 4.6 Payment Agent
# ---------------------------------------------------------------------------

PAYMENT_TOOLS: list[dict] = [
    {
        "name": "check_counterparty",
        "description": (
            "Look up a counterparty by name in the authorized counterparty database. "
            "Returns the counterparty record if found, or {\"found\": false} if not."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The counterparty name to look up.",
                }
            },
            "required": ["name"],
        },
    },
    {
        "name": "verify_kyc",
        "description": (
            "Verify the KYC (Know Your Customer) status of a beneficiary. "
            "Returns the KYC record if found, or {\"status\": \"not_found\"} if not."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "beneficiary": {
                    "type": "string",
                    "description": "The beneficiary name to verify.",
                }
            },
            "required": ["beneficiary"],
        },
    },
    {
        "name": "read_invoice",
        "description": (
            "Read and analyze an invoice document by its ID. "
            "Returns the invoice image as a base64-encoded PNG for vision analysis."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "invoice_id": {
                    "type": "string",
                    "description": "The invoice ID to retrieve.",
                }
            },
            "required": ["invoice_id"],
        },
    },
]

# ---------------------------------------------------------------------------
# Tool call handler
# ---------------------------------------------------------------------------


def handle_tool_call(
    tool_name: str,
    tool_input: dict,
    fixtures: FixtureData,
    invoice_path: Path | None,
) -> list[dict]:
    """Execute a single tool call against fixtures.

    Returns content blocks suitable for use in a tool_result message.

    For read_invoice: returns image content block with base64-encoded PNG plus
    a text annotation block.
    For check_counterparty / verify_kyc: returns a single text content block
    with the JSON result.

    Args:
        tool_name:    Name of the tool to execute.
        tool_input:   Dict of inputs as provided by the LLM.
        fixtures:     Loaded fixture data (counterparty_db, kyc_ledger).
        invoice_path: Path to the invoice PNG file; required for read_invoice.

    Returns:
        list of content block dicts for the tool_result message.
    """
    if tool_name == "check_counterparty":
        name = tool_input.get("name", "")
        counterparty_db: dict = fixtures["counterparty_db"]
        # Case-insensitive lookup
        entry = None
        for key, val in counterparty_db.items():
            if key.lower() == name.lower():
                entry = val
                break
        if entry is None:
            result = {"found": False}
        else:
            result = entry
        return [{"type": "text", "text": json.dumps(result)}]

    elif tool_name == "verify_kyc":
        beneficiary = tool_input.get("beneficiary", "")
        kyc_ledger: dict = fixtures["kyc_ledger"]
        entry = None
        for key, val in kyc_ledger.items():
            if key.lower() == beneficiary.lower():
                entry = val
                break
        if entry is None:
            result = {"status": "not_found"}
        else:
            result = entry
        return [{"type": "text", "text": json.dumps(result)}]

    elif tool_name == "read_invoice":
        if invoice_path is None or not Path(invoice_path).exists():
            return [{"type": "text", "text": json.dumps({"error": "Invoice not found"})}]
        with open(invoice_path, "rb") as f:
            raw_bytes = f.read()
        img_b64 = base64.standard_b64encode(raw_bytes).decode("ascii")
        return [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": img_b64,
                },
            },
            {"type": "text", "text": "Invoice document attached for analysis."},
        ]

    else:
        return [{"type": "text", "text": json.dumps({"error": f"Unknown tool: {tool_name}"})}]


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------


def parse_payment_decision(
    response_text: str,
    episode_id: str,
    steps_taken: list[str],
) -> PaymentDecision:
    """Parse Payment Agent's final text response into a PaymentDecision.

    Extracts JSON from response_text (handles raw JSON or markdown code fences),
    fills steps_taken from conversation history, sets episode_id from parameter.

    Args:
        response_text: Final text output from the Payment Agent LLM.
        episode_id:    UUID string for the current investigation episode.
        steps_taken:   Ordered list of tool call names made during the conversation.

    Returns:
        PaymentDecision with all required fields populated.

    Raises:
        ValueError: If JSON cannot be extracted or required fields are missing.
    """
    # Strip markdown code fences if present (```json ... ``` or ``` ... ```)
    text = response_text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        text = fence_match.group(1).strip()
    else:
        # Try to extract the first {...} block
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            text = brace_match.group(0)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Could not parse JSON from Payment Agent response: {exc}\n"
            f"Response was: {response_text[:500]}"
        ) from exc

    return PaymentDecision(
        episode_id=episode_id,
        decision=data.get("decision", "deny"),
        amount=float(data.get("amount", 0.0)),
        beneficiary=str(data.get("beneficiary", "")),
        account=str(data.get("account", "")),
        rationale=str(data.get("rationale", "")),
        steps_taken=steps_taken,
        confidence=float(data.get("confidence", 0.0)),
        claims={str(k): str(v) for k, v in data.get("claims", {}).items()},
        document_urls=list(data.get("document_urls", [])),
    )
