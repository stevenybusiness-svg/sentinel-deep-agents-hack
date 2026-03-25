"""
Unit tests for sentinel/agents/payment_agent.py.

These tests verify tool call handling and response parsing without making
any real API calls. The payment_agent module does not call the LLM directly,
so no ANTHROPIC_API_KEY is needed.
"""
from __future__ import annotations

import io
import json
import struct
import zlib
from pathlib import Path

import pytest

from sentinel.agents.payment_agent import (
    PAYMENT_AGENT_SYSTEM_PROMPT,
    PAYMENT_TOOLS,
    handle_tool_call,
    parse_payment_decision,
)
from sentinel.schemas.payment import PaymentDecision

# ---------------------------------------------------------------------------
# Minimal fixture data for tests
# ---------------------------------------------------------------------------

MINIMAL_FIXTURES: dict = {
    "kyc_ledger": {
        "Acme Corp": {"status": "verified", "risk_tier": "low"},
        "Verified Vendor": {"status": "verified", "risk_tier": "medium"},
    },
    "counterparty_db": {
        "Acme Corp": {"authorized": True, "max_transfer_usd": 500000},
        "Verified Vendor": {"authorized": True, "max_transfer_usd": 250000},
    },
    "behavioral_baselines": {
        "mean_confidence": 0.52,
        "std_confidence": 0.11,
    },
}


def _make_1x1_png() -> bytes:
    """Return minimal valid 1x1 pixel white PNG bytes."""
    # PNG signature
    sig = b"\x89PNG\r\n\x1a\n"

    def _chunk(name: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)
        return length + name + data + crc

    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw_pixel = b"\x00\xff\xff\xff"  # filter byte + RGB white
    idat = _chunk(b"IDAT", zlib.compress(raw_pixel))
    iend = _chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


# ---------------------------------------------------------------------------
# Module-level export tests
# ---------------------------------------------------------------------------


def test_payment_tools_count():
    """PAYMENT_TOOLS must have exactly 3 tools."""
    assert len(PAYMENT_TOOLS) == 3


def test_payment_tools_names():
    """PAYMENT_TOOLS must include the three required tool names."""
    names = {t["name"] for t in PAYMENT_TOOLS}
    assert "check_counterparty" in names
    assert "verify_kyc" in names
    assert "read_invoice" in names


def test_payment_agent_system_prompt_not_empty():
    """PAYMENT_AGENT_SYSTEM_PROMPT must be a non-empty string."""
    assert isinstance(PAYMENT_AGENT_SYSTEM_PROMPT, str)
    assert len(PAYMENT_AGENT_SYSTEM_PROMPT) > 0


# ---------------------------------------------------------------------------
# handle_tool_call — check_counterparty
# ---------------------------------------------------------------------------


def test_handle_tool_call_counterparty_found():
    """check_counterparty returns the fixture entry as JSON text block."""
    result = handle_tool_call(
        "check_counterparty",
        {"name": "Acme Corp"},
        MINIMAL_FIXTURES,
        None,
    )
    assert isinstance(result, list)
    assert len(result) == 1
    block = result[0]
    assert block["type"] == "text"
    data = json.loads(block["text"])
    assert data["authorized"] is True
    assert data["max_transfer_usd"] == 500000


def test_handle_tool_call_counterparty_not_found():
    """check_counterparty returns {found: false} when name absent from fixtures."""
    result = handle_tool_call(
        "check_counterparty",
        {"name": "Unknown Entity LLC"},
        MINIMAL_FIXTURES,
        None,
    )
    assert len(result) == 1
    data = json.loads(result[0]["text"])
    assert data["found"] is False


def test_handle_tool_call_counterparty_case_insensitive():
    """check_counterparty lookup is case-insensitive."""
    result = handle_tool_call(
        "check_counterparty",
        {"name": "acme corp"},
        MINIMAL_FIXTURES,
        None,
    )
    data = json.loads(result[0]["text"])
    assert data["authorized"] is True


# ---------------------------------------------------------------------------
# handle_tool_call — verify_kyc
# ---------------------------------------------------------------------------


def test_handle_tool_call_kyc_found():
    """verify_kyc returns the KYC record when beneficiary is known."""
    result = handle_tool_call(
        "verify_kyc",
        {"beneficiary": "Verified Vendor"},
        MINIMAL_FIXTURES,
        None,
    )
    assert len(result) == 1
    data = json.loads(result[0]["text"])
    assert data["status"] == "verified"


def test_handle_tool_call_kyc_not_found():
    """verify_kyc returns {status: not_found} for unknown beneficiary."""
    result = handle_tool_call(
        "verify_kyc",
        {"beneficiary": "Meridian Logistics"},
        MINIMAL_FIXTURES,
        None,
    )
    assert len(result) == 1
    data = json.loads(result[0]["text"])
    assert data["status"] == "not_found"


# ---------------------------------------------------------------------------
# handle_tool_call — read_invoice
# ---------------------------------------------------------------------------


def test_handle_tool_call_read_invoice(tmp_path: Path):
    """read_invoice returns image content block with base64-encoded PNG."""
    import base64

    invoice_file = tmp_path / "test_invoice.png"
    png_bytes = _make_1x1_png()
    invoice_file.write_bytes(png_bytes)

    result = handle_tool_call(
        "read_invoice",
        {"invoice_id": "INV-001"},
        MINIMAL_FIXTURES,
        invoice_file,
    )
    # Should return 2 blocks: image + text annotation
    assert len(result) == 2
    img_block = result[0]
    assert img_block["type"] == "image"
    assert img_block["source"]["type"] == "base64"
    assert img_block["source"]["media_type"] == "image/png"
    # Verify the base64 data round-trips to the original bytes
    decoded = base64.b64decode(img_block["source"]["data"])
    assert decoded == png_bytes
    # Text annotation block
    assert result[1]["type"] == "text"
    assert "Invoice" in result[1]["text"]


def test_handle_tool_call_read_invoice_no_path():
    """read_invoice returns error block when invoice_path is None."""
    result = handle_tool_call(
        "read_invoice",
        {"invoice_id": "INV-999"},
        MINIMAL_FIXTURES,
        None,
    )
    assert len(result) == 1
    data = json.loads(result[0]["text"])
    assert "error" in data


# ---------------------------------------------------------------------------
# parse_payment_decision
# ---------------------------------------------------------------------------


def test_parse_payment_decision_basic():
    """parse_payment_decision handles a plain JSON response."""
    response = json.dumps({
        "decision": "approve",
        "amount": 12500.00,
        "beneficiary": "Acme Corp",
        "account": "ACC-001",
        "rationale": "All checks passed.",
        "confidence": 0.92,
        "claims": {"kyc_verified": "true", "counterparty_authorized": "true"},
    })
    decision = parse_payment_decision(
        response_text=response,
        episode_id="ep-abc123",
        steps_taken=["check_counterparty", "verify_kyc"],
    )
    assert isinstance(decision, PaymentDecision)
    assert decision.episode_id == "ep-abc123"
    assert decision.decision == "approve"
    assert decision.amount == 12500.00
    assert decision.beneficiary == "Acme Corp"
    assert decision.account == "ACC-001"
    assert decision.confidence == 0.92
    assert decision.steps_taken == ["check_counterparty", "verify_kyc"]
    assert decision.claims["kyc_verified"] == "true"


def test_parse_payment_decision_from_markdown():
    """parse_payment_decision extracts JSON from markdown code fence."""
    inner = json.dumps({
        "decision": "deny",
        "amount": 999.99,
        "beneficiary": "Suspicious Inc",
        "account": "ACC-XYZ",
        "rationale": "KYC not verified.",
        "confidence": 0.15,
        "claims": {"kyc_verified": "false"},
    })
    response = f"After analysis, here is my decision:\n\n```json\n{inner}\n```"
    decision = parse_payment_decision(
        response_text=response,
        episode_id="ep-def456",
        steps_taken=["verify_kyc"],
    )
    assert decision.decision == "deny"
    assert decision.beneficiary == "Suspicious Inc"
    assert decision.confidence == 0.15
    assert decision.episode_id == "ep-def456"


def test_parse_payment_decision_json_embedded_in_text():
    """parse_payment_decision extracts JSON block embedded in prose."""
    inner = json.dumps({
        "decision": "approve",
        "amount": 5000.0,
        "beneficiary": "Vendor B",
        "account": "VB-001",
        "rationale": "Counterparty approved.",
        "confidence": 0.85,
        "claims": {"counterparty_authorized": "true"},
    })
    response = f"I have completed my analysis. My final decision is:\n{inner}\nThank you."
    decision = parse_payment_decision(
        response_text=response,
        episode_id="ep-ghi789",
        steps_taken=["check_counterparty", "verify_kyc", "read_invoice"],
    )
    assert decision.decision == "approve"
    assert decision.amount == 5000.0
    assert len(decision.steps_taken) == 3


def test_parse_payment_decision_invalid_raises():
    """parse_payment_decision raises ValueError on unparseable response."""
    with pytest.raises(ValueError, match="Could not parse JSON"):
        parse_payment_decision(
            response_text="I cannot decide. The invoice is unclear.",
            episode_id="ep-fail",
            steps_taken=[],
        )
