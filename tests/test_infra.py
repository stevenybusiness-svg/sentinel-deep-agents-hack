"""Infrastructure tests for Aerospike client.

Aerospike integration tests require Docker to be running.
Set AEROSPIKE_TEST=1 to run them.
"""
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest


# ── Non-skipped tests (always run) ─────────────────────────────────────────

def test_aerospike_client_init():
    """AerospikeClient() creates instance with correct defaults."""
    from sentinel.memory import AerospikeClient

    client = AerospikeClient()
    assert client.host == "localhost"
    assert client.port == 3000
    assert client.namespace == "sentinel"


def test_aerospike_client_uses_executor():
    """Client uses ThreadPoolExecutor (not aioaerospike)."""
    from sentinel.memory import AerospikeClient

    client = AerospikeClient()
    assert hasattr(client, "_executor")
    assert isinstance(client._executor, ThreadPoolExecutor)


def test_env_config():
    """.env.example exists and contains required Aerospike vars."""
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), ".env.example"
    )
    assert os.path.exists(env_path), ".env.example must exist at repo root"
    content = open(env_path).read()
    assert "AEROSPIKE_HOST" in content
    assert "AEROSPIKE_PORT" in content
    assert "AEROSPIKE_NAMESPACE" in content


# ── Integration tests (require Docker + AEROSPIKE_TEST=1) ──────────────────

requires_aerospike = pytest.mark.skipif(
    os.getenv("AEROSPIKE_TEST", "0") != "1",
    reason="Set AEROSPIKE_TEST=1 to run Aerospike integration tests (requires Docker)",
)


@requires_aerospike
def test_aerospike_health_check():
    """Client connect() + health_check() returns healthy=True."""
    from sentinel.memory import AerospikeClient

    client = AerospikeClient()
    client.connect()
    try:
        result = asyncio.run(client.health_check())
        assert result["healthy"] is True
        assert "write_latency_ms" in result
        assert "read_latency_ms" in result
        assert result["namespace"] == "sentinel"
    finally:
        client.close()


@requires_aerospike
def test_aerospike_put_get_roundtrip():
    """Write a record, read it back, assert values match."""
    from sentinel.memory import AerospikeClient

    client = AerospikeClient()
    client.connect()
    try:
        test_bins = {"value": "roundtrip-test", "num": 42}
        asyncio.run(client.put("test", "roundtrip-key", test_bins))
        result = asyncio.run(client.get("test", "roundtrip-key"))
        assert result["value"] == "roundtrip-test"
        assert result["num"] == 42
    finally:
        client.close()


# ── Frontend build test (INFRA-04) ─────────────────────────────────────────

import subprocess


def test_frontend_build():
    """INFRA-04: Verify React frontend builds successfully with all dependencies."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
    frontend_dir = os.path.abspath(frontend_dir)
    assert os.path.isdir(frontend_dir), f"frontend/ directory not found at {frontend_dir}"

    result = subprocess.run(
        ["npx", "vite", "build"],
        cwd=frontend_dir,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"vite build failed:\n{result.stderr}"
