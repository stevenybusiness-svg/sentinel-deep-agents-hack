"""Tests for Airbyte cache write and Slack reporter integration."""
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
async def test_write_episode_to_cache_creates_record():
    """Airbyte cache write persists episode data to DuckDB."""
    from sentinel.integrations.airbyte_cache import write_episode_to_cache
    result = await write_episode_to_cache(
        episode_id="ep-test-1",
        decision="NO-GO",
        composite_score=0.85,
        attribution="test attribution",
    )
    # Should return True on success (DuckDB write)
    assert result is True
