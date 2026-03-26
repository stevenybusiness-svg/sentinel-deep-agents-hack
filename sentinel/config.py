from __future__ import annotations
"""Centralized configuration loading from .env for Sentinel."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from repo root
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)


class Settings:
    def __init__(self) -> None:
        self.ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
        self.AEROSPIKE_HOST: str = os.getenv("AEROSPIKE_HOST", "localhost")
        self.AEROSPIKE_PORT: int = int(os.getenv("AEROSPIKE_PORT", "3000"))
        self.AEROSPIKE_NAMESPACE: str = os.getenv("AEROSPIKE_NAMESPACE", "sentinel")
        self.BLAND_API_KEY: str = os.getenv("BLAND_API_KEY", "")
        self.OKTA_DOMAIN: str = os.getenv("OKTA_DOMAIN", "")
        self.OKTA_CLIENT_ID: str = os.getenv("OKTA_CLIENT_ID", "")
        # LLM backend selection: "anthropic" (default) | "bedrock"
        self.LLM_BACKEND: str = os.getenv("LLM_BACKEND", "anthropic")
        self.AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
        self.AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
        self.AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
        self.SUPERVISOR_MODEL: str = os.getenv("SUPERVISOR_MODEL", "")  # empty = use backend default
        self.AGENT_MODEL: str = os.getenv("AGENT_MODEL", "")  # empty = use backend default


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
