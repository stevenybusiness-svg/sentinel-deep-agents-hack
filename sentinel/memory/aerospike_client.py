from __future__ import annotations
"""Async-compatible Aerospike client using sync client + ThreadPoolExecutor.

Per CLAUDE.md: official sync client + run_in_executor is the supported pattern.
aioaerospike is archived/unmaintained as of August 2025.
"""
import os
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

try:
    import aerospike as _aerospike_lib
except ImportError:
    _aerospike_lib = None


class AerospikeClient:
    """Async-compatible Aerospike client wrapper.

    Wraps the synchronous aerospike C-extension with run_in_executor so it
    can be awaited from FastAPI async routes without blocking the event loop.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        namespace: Optional[str] = None,
        max_workers: int = 4,
    ):
        self.host = host or os.getenv("AEROSPIKE_HOST", "localhost")
        self.port = port or int(os.getenv("AEROSPIKE_PORT", "3000"))
        self.namespace = namespace or os.getenv("AEROSPIKE_NAMESPACE", "sentinel")
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._client = None

    def connect(self) -> "AerospikeClient":
        """Connect to Aerospike server. Call once at app startup."""
        if _aerospike_lib is None:
            raise RuntimeError("aerospike package not installed")
        config = {"hosts": [(self.host, self.port)]}
        self._client = _aerospike_lib.client(config).connect()
        return self

    def close(self) -> None:
        """Close the connection. Call at app shutdown."""
        if self._client:
            self._client.close()
            self._client = None

    def _key(self, set_name: str, pk: str) -> tuple:
        return (self.namespace, set_name, pk)

    async def put(self, set_name: str, pk: str, bins: dict[str, Any]) -> None:
        """Async write: stores bins dict under (namespace, set_name, pk)."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            self._executor,
            lambda: self._client.put(self._key(set_name, pk), bins),
        )

    async def get(self, set_name: str, pk: str) -> dict[str, Any]:
        """Async read: returns bins dict for (namespace, set_name, pk)."""
        loop = asyncio.get_running_loop()
        _, _, bins = await loop.run_in_executor(
            self._executor,
            lambda: self._client.get(self._key(set_name, pk)),
        )
        return bins

    async def health_check(self) -> dict[str, Any]:
        """Read-after-write health check per INFRA-02.

        Writes a sentinel key, reads it back, measures write and read latency.
        Returns dict with healthy flag and latency metrics for dashboard display.
        """
        test_key = "__health_check__"
        test_bins = {"status": "ok", "ts": int(time.time())}

        start = time.perf_counter()
        await self.put("health", test_key, test_bins)
        write_ms = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        result = await self.get("health", test_key)
        read_ms = (time.perf_counter() - start) * 1000

        return {
            "healthy": result.get("status") == "ok",
            "write_latency_ms": round(write_ms, 2),
            "read_latency_ms": round(read_ms, 2),
            "namespace": self.namespace,
        }


# Module-level singleton (lazy -- call connect() at app startup)
_client: Optional["AerospikeClient"] = None


def get_aerospike_client() -> AerospikeClient:
    """Return the module-level AerospikeClient singleton.

    Instantiates on first call; caller must call .connect() before use.
    """
    global _client
    if _client is None:
        _client = AerospikeClient()
    return _client
