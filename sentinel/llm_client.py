"""LLM client factory and model ID lookup for Sentinel.

Supports two backends selectable via the LLM_BACKEND env var:
  - "anthropic" (default): direct Anthropic API via AsyncAnthropic
  - "bedrock": Amazon Bedrock via AsyncAnthropicBedrock

Zero-friction fallback: default behavior unchanged when LLM_BACKEND is unset.
"""
from anthropic import AsyncAnthropic
from anthropic import AsyncAnthropicBedrock

from sentinel.config import get_settings

# Default model IDs per backend
_MODELS: dict[str, dict[str, str]] = {
    "anthropic": {
        "supervisor": "claude-opus-4-6",
        "agent": "claude-sonnet-4-6",
    },
    "bedrock": {
        "supervisor": "us.anthropic.claude-opus-4-5-20251101-v1:0",
        "agent": "us.anthropic.claude-sonnet-4-5-20251001-v1:0",
    },
}


def get_async_client() -> AsyncAnthropic | AsyncAnthropicBedrock:
    """Return an async LLM client for the configured backend.

    Reads LLM_BACKEND from settings (via env var). Defaults to "anthropic".

    Returns:
        AsyncAnthropic for "anthropic" backend.
        AsyncAnthropicBedrock for "bedrock" backend.

    Raises:
        ValueError: If LLM_BACKEND is set to an unrecognized value.
    """
    settings = get_settings()
    backend = settings.LLM_BACKEND or "anthropic"

    if backend == "anthropic":
        return AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    elif backend == "bedrock":
        return AsyncAnthropicBedrock(
            aws_region=settings.AWS_REGION,
            aws_access_key=settings.AWS_ACCESS_KEY_ID,
            aws_secret_key=settings.AWS_SECRET_ACCESS_KEY,
        )
    else:
        raise ValueError(
            f"Unknown LLM_BACKEND: {backend!r}. Must be 'anthropic' or 'bedrock'."
        )


def get_model_ids() -> dict[str, str]:
    """Return model IDs for the configured backend.

    Reads LLM_BACKEND, SUPERVISOR_MODEL, and AGENT_MODEL from settings.
    SUPERVISOR_MODEL and AGENT_MODEL env vars override backend defaults when non-empty.

    Returns:
        Dict with keys "supervisor" and "agent" mapping to model ID strings.
    """
    settings = get_settings()
    backend = settings.LLM_BACKEND or "anthropic"

    if backend not in _MODELS:
        raise ValueError(
            f"Unknown LLM_BACKEND: {backend!r}. Must be 'anthropic' or 'bedrock'."
        )

    defaults = dict(_MODELS[backend])

    if settings.SUPERVISOR_MODEL:
        defaults["supervisor"] = settings.SUPERVISOR_MODEL
    if settings.AGENT_MODEL:
        defaults["agent"] = settings.AGENT_MODEL

    return defaults
