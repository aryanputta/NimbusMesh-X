from pathlib import Path

from nimbusmesh_x.config import load_config
from topology_service.graph import TopologyService


ROOT = Path(__file__).resolve().parents[1]


def test_topology_affinity_prefers_nvlink_mesh() -> None:
    config = load_config(ROOT / "configs" / "multi_cluster_long_context.json")
    topology = TopologyService(config)
    premium_affinity = topology.pool_affinity("eastus-bw", "bw-premium", prompt_tokens=16384)
    overflow_affinity = topology.pool_affinity("westus-overflow", "l40s-overflow", prompt_tokens=16384)
    assert premium_affinity > overflow_affinity


def test_route_cost_is_finite_for_known_pool() -> None:
    config = load_config(ROOT / "configs" / "multi_cluster_long_context.json")
    topology = TopologyService(config)
    cost = topology.route_cost("centralus-h100", "h100-main")
    assert cost > 0
    assert cost < 5

