"""
FastAPI application for Sentinel — API-01, API-02.

Provides:
  POST /investigate — triggers full investigation pipeline (API-02)
  GET  /ws          — WebSocket endpoint for dashboard event streaming (API-01)
  GET  /health      — health check with Aerospike status

Lifespan loads all app state at startup (fixtures, LLM client, Safety Gate,
Aerospike). Aerospike is optional — the server degrades gracefully if unavailable.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from sentinel.api.routes.bland_webhook import router as bland_webhook_router
from sentinel.api.routes.confirm import router as confirm_router
from sentinel.api.routes.investigate import router as investigate_router
from sentinel.api.websocket import ws_manager
from sentinel.config import get_settings
from sentinel.engine.safety_gate import SafetyGate
from sentinel.fixtures import load_fixtures, get_invoice_paths
from sentinel.llm_client import get_async_client, get_model_ids
from sentinel.memory.aerospike_client import get_aerospike_client
from sentinel.memory.trust_store import store_baselines

# ---------------------------------------------------------------------------
# Shared mutable app state (module-level for route access)
# ---------------------------------------------------------------------------

app_state: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize shared resources on startup, clean up on shutdown."""
    # ---- Startup ----
    _settings = get_settings()  # noqa: F841 — triggers .env load

    # Fixtures (KYC ledger, counterparty DB, behavioral baselines)
    app_state["fixtures"] = load_fixtures()
    app_state["invoice_paths"] = get_invoice_paths()

    # LLM client and model IDs
    app_state["llm_client"] = get_async_client()
    app_state["models"] = get_model_ids()

    # Safety Gate with hardcoded scoring rules
    gate = SafetyGate()
    rules_dir = Path(__file__).parent.parent / "gate" / "rules"
    if rules_dir.exists():
        gate.load_rules_from_directory(rules_dir)
    app_state["safety_gate"] = gate

    # Aerospike — optional, graceful degradation if unavailable
    try:
        aerospike = get_aerospike_client()
        aerospike.connect()
        # Pre-load behavioral baselines into the Aerospike trust store
        await store_baselines(app_state["fixtures"]["behavioral_baselines"], aerospike)
        app_state["aerospike"] = aerospike
    except Exception:
        # Server continues without Aerospike — episodes won't be persisted
        app_state["aerospike"] = None

    # Load generated rules from Aerospike into Safety Gate (MEM-02)
    if app_state.get("aerospike"):
        try:
            from sentinel.memory.rule_store import load_all_rules
            stored_rules = await load_all_rules(app_state["aerospike"])
            for rule_record in stored_rules:
                try:
                    gate.register_rule(rule_record["rule_id"], rule_record["source"])
                except Exception:
                    pass  # Skip invalid stored rules — don't crash startup
        except Exception:
            pass  # Aerospike rule load failure is non-fatal

    # In-memory episode cache for voice Q&A (API-02)
    app_state["active_episodes"] = {}

    yield

    # ---- Shutdown ----
    if app_state.get("aerospike"):
        app_state["aerospike"].close()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Sentinel",
    description="Runtime security system for autonomous AI agents",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# WebSocket endpoint — API-01
# ---------------------------------------------------------------------------


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket connection for dashboard event streaming.

    Clients connect here to receive all named investigation events:
    investigation_started, agent_completed (x3), verdict_board_assembled,
    gate_evaluated, episode_written, rule_generated, rule_deployed.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive; messages are server-pushed
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ---------------------------------------------------------------------------
# Investigation routes — API-02
# ---------------------------------------------------------------------------

app.include_router(investigate_router, prefix="/api")
app.include_router(confirm_router, prefix="/api")
app.include_router(bland_webhook_router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict:
    """Health check. Returns Aerospike connection status."""
    return {
        "status": "ok",
        "aerospike": app_state.get("aerospike") is not None,
    }


# ---------------------------------------------------------------------------
# Static frontend — serve React build from frontend/dist
# ---------------------------------------------------------------------------

_FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.exists():
    # Serve hashed assets (JS/CSS chunks) under /assets
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_catch_all(full_path: str) -> FileResponse:
        """Return index.html for all non-API paths to support client-side routing."""
        return FileResponse(str(_FRONTEND_DIST / "index.html"))
