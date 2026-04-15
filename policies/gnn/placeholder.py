from __future__ import annotations

from nimbusmesh_x.types import CandidatePlacement, InferenceRequest
from policies.heuristics.base import RoutingPolicy


class GNNPlaceholderPolicy(RoutingPolicy):
    name = "gnn_placeholder"

    def choose(self, request: InferenceRequest, candidates: list[CandidatePlacement]) -> CandidatePlacement:
        usable = [candidate for candidate in candidates if candidate.available] or candidates
        return min(
            usable,
            key=lambda item: (
                item.estimated_total_latency_ms
                - item.expected_cache_hit_ratio * 300.0
                - item.topology_affinity * 75.0
            ),
        )

