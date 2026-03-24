"""Centralized configuration loading from .env for Sentinel."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from repo root
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)


class Settings:
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    AEROSPIKE_HOST: str = os.getenv("AEROSPIKE_HOST", "localhost")
    AEROSPIKE_PORT: int = int(os.getenv("AEROSPIKE_PORT", "3000"))
    AEROSPIKE_NAMESPACE: str = os.getenv("AEROSPIKE_NAMESPACE", "sentinel")
    BLAND_API_KEY: str = os.getenv("BLAND_API_KEY", "")
    OKTA_DOMAIN: str = os.getenv("OKTA_DOMAIN", "")
    OKTA_CLIENT_ID: str = os.getenv("OKTA_CLIENT_ID", "")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
