from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from control_plane.service import NimbusMeshControlPlane
from nimbusmesh_x.config import load_config
from nimbusmesh_x.metrics import MetricsCollector
from nimbusmesh_x.types import InferenceRequest
from simulators.engine import SimulationEngine


DEFAULT_CONFIG = Path("configs/multi_cluster_long_context.json")


def create_app(config_path: str | Path = DEFAULT_CONFIG) -> FastAPI:
    config = load_config(config_path)
    control_plane = NimbusMeshControlPlane(config)
    metrics = MetricsCollector()
    app = FastAPI(title="NimbusMesh-X Control Plane", version="0.1.0")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/topology")
    def topology() -> dict[str, object]:
        return control_plane.topology_snapshot()

    @app.get("/v1/cache")
    def cache() -> dict[str, object]:
        return control_plane.cache_snapshot(now=0.0)

    @app.post("/v1/route")
    def route(payload: dict) -> dict[str, object]:
        request = InferenceRequest(**payload)
        control_plane.refresh(request.arrival_ts)
        control_plane.note_submission(request)
        candidate, decision = control_plane.route(request, request.arrival_ts)
        return {
            "decision": asdict(decision),
            "candidate": asdict(candidate),
        }

    @app.post("/v1/simulate")
    def simulate(payload: dict[str, object]) -> dict[str, object]:
        config_to_use = load_config(payload.get("config_path", str(config_path)))
        policy_name = payload.get("policy")
        engine = SimulationEngine(config_to_use.with_policy(policy_name) if isinstance(policy_name, str) else config_to_use)
        return engine.run()

    @app.get("/metrics")
    def metrics_endpoint() -> PlainTextResponse:
        return PlainTextResponse(metrics.render_prometheus(), media_type="text/plain; version=0.0.4")

    return app

