"""Tests for Slack reporter integration (Airbyte removed from scope in Phase 8)."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_send_investigation_report_returns_false_when_no_url():
    """Slack reporter returns False when SLACK_WEBHOOK_URL is unset."""
    from sentinel.integrations.slack_reporter import send_investigation_report
    with patch.dict("os.environ", {"SLACK_WEBHOOK_URL": ""}):
        result = await send_investigation_report("ep-1", "NO-GO", 0.85, "test attr")
        assert result is False


@pytest.mark.asyncio
async def test_send_investigation_report_returns_false_on_placeholder():
    """Slack reporter returns False when SLACK_WEBHOOK_URL is placeholder."""
    from sentinel.integrations.slack_reporter import send_investigation_report
    with patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"}):
        result = await send_investigation_report("ep-1", "NO-GO", 0.85, "test attr")
        assert result is False


@pytest.mark.asyncio
async def test_send_investigation_report_posts_to_webhook():
    """Slack reporter POSTs Block Kit payload to webhook URL."""
    from sentinel.integrations.slack_reporter import send_investigation_report
    mock_response = MagicMock()
    mock_response.status_code = 200
    with patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T/B/X"}):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            result = await send_investigation_report("ep-1", "NO-GO", 0.85, "suspicious")
            assert result is True
            mock_post.assert_called_once()
            payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
            assert "blocks" in payload


@pytest.mark.asyncio
async def test_send_investigation_report_includes_agent_verdicts():
    """Slack reporter includes agent verdicts in Block Kit payload."""
    from sentinel.integrations.slack_reporter import send_investigation_report
    mock_response = MagicMock()
    mock_response.status_code = 200
    agent_verdicts = [
        {"agent_id": "risk_agent", "confidence": 0.92, "flags": ["high_z_score", "step_deviation"]},
        {"agent_id": "compliance_agent", "confidence": 0.88, "flags": ["kyc_mismatch"]},
        {"agent_id": "forensics_agent", "confidence": 0.95, "flags": ["hidden_text_detected"]},
    ]
    with patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T/B/X"}):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            result = await send_investigation_report(
                "ep-2",
                "NO-GO",
                1.85,
                "Hardcoded rule: adversarial content detected",
                agent_verdicts=agent_verdicts,
            )
            assert result is True
            payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
            # Verify agent verdicts appear somewhere in the blocks
            blocks_text = str(payload["blocks"])
            assert "Risk Agent" in blocks_text or "risk_agent" in blocks_text.lower()
            assert "0.92" in blocks_text


@pytest.mark.asyncio
async def test_send_investigation_report_includes_self_improvement_arc():
    """Slack reporter includes Self-Improvement Arc block when generated rules fired."""
    from sentinel.integrations.slack_reporter import send_investigation_report
    mock_response = MagicMock()
    mock_response.status_code = 200
    with patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T/B/X"}):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            result = await send_investigation_report(
                "ep-3",
                "NO-GO",
                1.5,
                "Generated rule: gen_rule_001 fired",
                generated_rules_fired=["gen_rule_001"],
            )
            assert result is True
            payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
            blocks_text = str(payload["blocks"])
            assert "Self-Improvement Arc" in blocks_text
            assert "gen_rule_001" in blocks_text


@pytest.mark.asyncio
async def test_send_investigation_report_no_arc_when_no_generated_rules():
    """Slack reporter omits Self-Improvement Arc block when generated_rules_fired is empty."""
    from sentinel.integrations.slack_reporter import send_investigation_report
    mock_response = MagicMock()
    mock_response.status_code = 200
    with patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T/B/X"}):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            result = await send_investigation_report(
                "ep-4",
                "NO-GO",
                1.0,
                "Hardcoded rules fired",
                generated_rules_fired=[],
            )
            assert result is True
            payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
            blocks_text = str(payload["blocks"])
            assert "Self-Improvement Arc" not in blocks_text

            # Also verify None case
            result2 = await send_investigation_report(
                "ep-5",
                "GO",
                0.2,
                "Clean",
                generated_rules_fired=None,
            )
            assert result2 is True
            payload2 = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
            blocks_text2 = str(payload2["blocks"])
            assert "Self-Improvement Arc" not in blocks_text2
