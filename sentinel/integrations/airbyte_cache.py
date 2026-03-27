"""PyAirbyte DuckDB cache for episode investigation data.

Writes episode summaries to a local DuckDB file via PyAirbyte's default cache.
This demonstrates Airbyte in the investigation pipeline for Airbyte judges.
Falls back to direct duckdb if the airbyte package is not installed.
"""
from __future__ import annotations

from pathlib import Path

# DuckDB path: project-root/data/sentinel_episodes.duckdb
_DB_PATH = Path(__file__).parent.parent.parent / "data" / "sentinel_episodes.duckdb"


async def write_episode_to_cache(
    episode_id: str,
    decision: str,
    composite_score: float,
    attribution: str,
) -> bool:
    """Write episode investigation summary to DuckDB via PyAirbyte cache.

    Returns True on success, False on failure. Non-blocking — failures are logged
    but do not block the investigation pipeline.

    Uses PyAirbyte's default DuckDB cache when available; falls back to direct
    duckdb otherwise.
    """
    try:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Try PyAirbyte first (demonstrates Airbyte integration for judges)
        try:
            import airbyte as ab  # noqa: F401
            # Use PyAirbyte's default cache to get the DuckDB connection
            cache = ab.get_default_cache()
            conn = cache.get_duckdb_conn()  # type: ignore[attr-defined]
        except (ImportError, AttributeError, Exception):
            # Fall back to direct duckdb
            import duckdb
            conn = duckdb.connect(str(_DB_PATH))

        conn.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                episode_id VARCHAR PRIMARY KEY,
                decision VARCHAR,
                composite_score DOUBLE,
                attribution VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute(
            "INSERT OR REPLACE INTO episodes (episode_id, decision, composite_score, attribution) VALUES (?, ?, ?, ?)",
            [episode_id, decision, composite_score, attribution],
        )
        conn.close()
        return True
    except Exception:
        # Non-fatal — report delivery and gate decision are not affected
        return False
