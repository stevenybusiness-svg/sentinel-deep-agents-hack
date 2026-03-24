"""Shared test configuration and fixtures for the Sentinel test suite."""
import os

import pytest

# Set test environment defaults so tests run without a real .env file
os.environ.setdefault("AEROSPIKE_HOST", "localhost")
os.environ.setdefault("AEROSPIKE_PORT", "3000")
os.environ.setdefault("AEROSPIKE_NAMESPACE", "sentinel")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-placeholder")
os.environ.setdefault("BLAND_API_KEY", "test-bland-placeholder")
os.environ.setdefault("OKTA_DOMAIN", "test.okta.com")
os.environ.setdefault("OKTA_CLIENT_ID", "test-client-id")


@pytest.fixture
def fixture_data() -> dict:
    """Mock FixtureData dict — placeholder until Plan 04 populates real fixtures."""
    return {
        "kyc_ledger": {
            "ACME Corp": {"status": "verified", "risk_tier": "low"},
            "Global Trade Partners": {"status": "verified", "risk_tier": "medium"},
            # Meridian Logistics intentionally absent — exposes Phase 2 spoofed pre-clearance
        },
        "counterparty_db": {
            "ACME Corp": {"authorized": True, "max_transfer_usd": 500000},
            "Global Trade Partners": {"authorized": True, "max_transfer_usd": 250000},
        },
        "behavioral_baselines": {
            "mean_confidence": 0.52,
            "std_confidence": 0.11,
        },
    }
