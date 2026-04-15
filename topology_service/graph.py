from __future__ import annotations

import heapq
from collections import defaultdict

from nimbusmesh_x.config import ExperimentConfig
from nimbusmesh_x.types import TOPOLOGY_TIER_SCORE, TopologyLink, TopologyNode
from topology.gpu_topology_parser import GpuTopologySnapshot


class TopologyService:
    def __init__(self, config: ExperimentConfig) -> None:
        self.nodes: dict[str, TopologyNode] = {}
        self.adjacency: dict[str, list[TopologyLink]] = defaultdict(list)
        self.cluster_gateways: dict[str, str] = {}
        self.cluster_probe_affinity: dict[str, float] = {}
        self.cluster_probe_cost_factor: dict[str, float] = {}
        self._build_from_config(config)

    def _add_edge(self, source: str, target: str, bandwidth_gbps: float, latency_us: float, cost: float) -> None:
        self.adjacency[source].append(
            TopologyLink(
                source=source,
                target=target,
                bandwidth_gbps=bandwidth_gbps,
                latency_us=latency_us,
                cost=cost,
            )
        )

    def _build_from_config(self, config: ExperimentConfig) -> None:
        for cluster in config.clusters:
            gateway_id = f"gateway:{cluster.cluster_id}"
            self.cluster_gateways[cluster.cluster_id] = gateway_id
            self.nodes[gateway_id] = TopologyNode(
                node_id=gateway_id,
                kind="gateway",
                cluster_id=cluster.cluster_id,
                zone=cluster.zone,
            )
            for pool in cluster.pools:
                pool_node_id = self.pool_node_id(cluster.cluster_id, pool.pool_id)
                self.nodes[pool_node_id] = TopologyNode(
                    node_id=pool_node_id,
                    kind="pool",
                    cluster_id=cluster.cluster_id,
                    zone=cluster.zone,
                    metadata={
                        "accelerator_type": pool.accelerator_type,
                        "topology_tier": pool.topology_tier,
                        "gpu_count": pool.gpu_count,
                    },
                )
                tier_score = TOPOLOGY_TIER_SCORE.get(pool.topology_tier, 0.6)
                internal_cost = max(0.05, 1.2 - tier_score)
                bandwidth = 800.0 * tier_score
                latency = 8.0 + (1.0 - tier_score) * 35.0
                self._add_edge(gateway_id, pool_node_id, bandwidth, latency, internal_cost)
                self._add_edge(pool_node_id, gateway_id, bandwidth, latency, internal_cost)
            if cluster.gpu_topology_file:
                parsed = GpuTopologySnapshot.from_file(cluster.gpu_topology_file)
                self.cluster_probe_affinity[cluster.cluster_id] = parsed.overall_affinity()
                self.cluster_probe_cost_factor[cluster.cluster_id] = parsed.average_cost()

        for cluster in config.clusters:
            source_gateway = self.cluster_gateways[cluster.cluster_id]
            for target_cluster_id, cost in cluster.network_costs.items():
                if target_cluster_id == "ingress":
                    continue
                target_gateway = self.cluster_gateways.get(target_cluster_id)
                if not target_gateway:
                    continue
                self._add_edge(source_gateway, target_gateway, 400.0 / max(cost, 0.5), 25.0 * cost, cost)

    @staticmethod
    def pool_node_id(cluster_id: str, pool_id: str) -> str:
        return f"pool:{cluster_id}:{pool_id}"

    def shortest_path_cost(self, source: str, target: str) -> float:
        frontier: list[tuple[float, str]] = [(0.0, source)]
        visited: set[str] = set()
        distances: dict[str, float] = {source: 0.0}
        while frontier:
            cost, node_id = heapq.heappop(frontier)
            if node_id in visited:
                continue
            visited.add(node_id)
            if node_id == target:
                return cost
            for edge in self.adjacency.get(node_id, []):
                new_cost = cost + edge.cost
                if new_cost < distances.get(edge.target, float("inf")):
                    distances[edge.target] = new_cost
                    heapq.heappush(frontier, (new_cost, edge.target))
        return float("inf")

    def pool_affinity(self, cluster_id: str, pool_id: str, prompt_tokens: int) -> float:
        pool_node_id = self.pool_node_id(cluster_id, pool_id)
        node = self.nodes[pool_node_id]
        tier = node.metadata["topology_tier"]
        tier_score = TOPOLOGY_TIER_SCORE.get(tier, 0.6)
        long_context_factor = min(1.0, prompt_tokens / 8192.0)
        probe_affinity = self.cluster_probe_affinity.get(cluster_id, tier_score)
        blended = (tier_score * 0.8) + (probe_affinity * 0.2)
        return round(blended * (0.65 + 0.35 * long_context_factor), 4)

    def route_cost(self, cluster_id: str, pool_id: str) -> float:
        gateway_id = self.cluster_gateways[cluster_id]
        pool_node_id = self.pool_node_id(cluster_id, pool_id)
        base_cost = self.shortest_path_cost(gateway_id, pool_node_id)
        return round(base_cost * self.cluster_probe_cost_factor.get(cluster_id, 1.0), 4)

    def snapshot(self) -> dict[str, object]:
        return {
            "nodes": {node_id: node.metadata | {"kind": node.kind, "cluster_id": node.cluster_id} for node_id, node in self.nodes.items()},
            "edges": {
                node_id: [
                    {
                        "target": edge.target,
                        "bandwidth_gbps": edge.bandwidth_gbps,
                        "latency_us": edge.latency_us,
                        "cost": edge.cost,
                    }
                    for edge in edges
                ]
                for node_id, edges in self.adjacency.items()
            },
        }
