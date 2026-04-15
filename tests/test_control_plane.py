from pathlib import Path

from control_plane.service import NimbusMeshControlPlane
from nimbusmesh_x.config import load_config
from nimbusmesh_x.types import InferenceRequest


ROOT = Path(__file__).resolve().parents[1]


def test_router_returns_valid_pool() -> None:
    config = load_config(ROOT / "configs" / "multi_cluster_long_context.json")
    control_plane = NimbusMeshControlPlane(config)
    request = InferenceRequest(
        request_id="demo",
        tenant_id="copilot",
        model_id="llama-3-70b",
        prompt_tokens=8192,
        generation_tokens=1024,
        arrival_ts=0.0,
        sla_class="interactive",
        session_id="copilot-session",
    )
    control_plane.refresh(0.0)
    candidate, decision = control_plane.route(request, 0.0)
    assert candidate.cluster_id in control_plane.clusters
    assert candidate.pool_id in control_plane.clusters[candidate.cluster_id].pools
    assert decision.estimated_latency_ms > 0


def test_realtime_request_prefers_premium_pool() -> None:
    config = load_config(ROOT / "configs" / "heterogeneous_accelerators.json")
    control_plane = NimbusMeshControlPlane(config)
    request = InferenceRequest(
        request_id="rt-1",
        tenant_id="realtime-apps",
        model_id="llama-3-8b",
        prompt_tokens=4096,
        generation_tokens=512,
        arrival_ts=0.0,
        sla_class="realtime",
        session_id="rt-session",
    )
    control_plane.refresh(0.0)
    candidate, _ = control_plane.route(request, 0.0)
    assert candidate.pool_id == "premium-h100"


def test_failure_window_routes_away_from_unavailable_cluster() -> None:
    config = load_config(ROOT / "configs" / "failure_congestion.json")
    control_plane = NimbusMeshControlPlane(config)
    request = InferenceRequest(
        request_id="fail-1",
        tenant_id="copilot",
        model_id="llama-3-70b",
        prompt_tokens=4096,
        generation_tokens=512,
        arrival_ts=26.0,
        sla_class="interactive",
        session_id="fail-session",
    )
    control_plane.refresh(26.0)
    candidate, _ = control_plane.route(request, 26.0)
    assert candidate.cluster_id != "eastus-bw"


def test_fairness_penalty_grows_for_hot_tenant() -> None:
    config = load_config(ROOT / "configs" / "multi_cluster_long_context.json")
    control_plane = NimbusMeshControlPlane(config)
    control_plane.tenant_stats["copilot"].completed = 80
    control_plane.tenant_stats["agent-fleet"].completed = 10
    control_plane.tenant_stats["analytics"].completed = 5
    control_plane.tenant_stats["sandbox"].completed = 5
    hot_penalty = control_plane._fairness_penalty("copilot")
    cool_penalty = control_plane._fairness_penalty("sandbox")
    assert hot_penalty > cool_penalty

