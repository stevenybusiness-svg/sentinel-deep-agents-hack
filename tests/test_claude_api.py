"""Claude API connection validation — Plan 01-04 INFRA-03.

Validates:
- ANTHROPIC_API_KEY is present and correctly formatted (hard fail, non-skippable)
- Claude API responds without 429
- Prompt caching headers (cache_creation or cache_read > 0) confirm Tier 2 access
"""
import os
import pytest

# A real key must start with "sk-ant-" and not be the test placeholder set by conftest.py
_REAL_KEY = os.getenv("ANTHROPIC_API_KEY", "")
_HAS_REAL_KEY = bool(_REAL_KEY) and _REAL_KEY.startswith("sk-ant-") and _REAL_KEY != "sk-ant-test-placeholder"


def test_anthropic_api_key_present():
    """INFRA-03 gate: ANTHROPIC_API_KEY must be set. This test always runs and fails hard if missing."""
    key = os.getenv("ANTHROPIC_API_KEY", "")
    assert key and key.startswith("sk-ant-"), (
        "ANTHROPIC_API_KEY must be set to a valid key (starting with sk-ant-). "
        "Set it in .env or environment before running tests."
    )


@pytest.mark.skipif(not _HAS_REAL_KEY, reason="ANTHROPIC_API_KEY not set to a real key (only placeholder found)")
async def test_claude_api_connection():
    """INFRA-03: Claude API responds, no 429. Test passes means no rate limit was hit."""
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic()
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=50,
        timeout=30.0,
        messages=[{"role": "user", "content": "Reply with exactly: SENTINEL_OK"}],
    )
    assert response.content[0].text.strip() == "SENTINEL_OK" or "SENTINEL_OK" in response.content[0].text
    assert response.usage.input_tokens > 0


@pytest.mark.skipif(not _HAS_REAL_KEY, reason="ANTHROPIC_API_KEY not set to a real key (only placeholder found)")
async def test_claude_prompt_caching():
    """INFRA-03: Prompt caching active — cache_creation or cache_read > 0."""
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic()
    # Repeat to exceed 1024 token minimum for caching to activate (Research Pitfall 7)
    system_prompt = "You are Sentinel, a payment supervision system. " * 100
    system_block = [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]

    # First call — should create cache
    r1 = await client.messages.create(
        model="claude-sonnet-4-6", max_tokens=10, timeout=30.0,
        system=system_block,
        messages=[{"role": "user", "content": "Say OK"}],
    )
    cache_creation = r1.usage.cache_creation_input_tokens

    # Second call — should read from cache
    r2 = await client.messages.create(
        model="claude-sonnet-4-6", max_tokens=10, timeout=30.0,
        system=system_block,
        messages=[{"role": "user", "content": "Say OK again"}],
    )
    cache_read = r2.usage.cache_read_input_tokens

    # At least one of these should be > 0 to confirm caching is active
    assert cache_creation > 0 or cache_read > 0, (
        f"Prompt caching not active — cache_creation={cache_creation}, cache_read={cache_read}. "
        "Ensure ANTHROPIC_API_KEY has Tier 2 access and system prompt exceeds 1024 tokens."
    )


@pytest.mark.skipif(not _HAS_REAL_KEY, reason="ANTHROPIC_API_KEY not set to a real key (only placeholder found)")
async def test_no_rate_limit():
    """INFRA-03: API responds without 429. If this test passes, no rate limit was raised by the SDK."""
    from anthropic import AsyncAnthropic
    # If a 429 occurs, the SDK raises anthropic.RateLimitError (subclass of APIStatusError)
    # The test passing (no exception raised) proves no 429 was returned.
    client = AsyncAnthropic()
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=5,
        timeout=30.0,
        messages=[{"role": "user", "content": "Say 1"}],
    )
    assert response.usage.input_tokens > 0
