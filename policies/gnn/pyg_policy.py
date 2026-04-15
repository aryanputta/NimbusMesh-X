from __future__ import annotations

from policies.heuristics.base import RoutingPolicy
from nimbusmesh_x.types import CandidatePlacement, InferenceRequest

try:  # pragma: no cover - optional dependency path
    import torch_geometric  # noqa: F401
except Exception:  # pragma: no cover - optional dependency path
    torch_geometric = None


class PyGGNNPolicy(RoutingPolicy):
    name = "pyg_placeholder"

    def __init__(self) -> None:
        self.available = torch_geometric is not None

    def choose(self, request: InferenceRequest, candidates: list[CandidatePlacement]) -> CandidatePlacement:
        usable = [candidate for candidate in candidates if candidate.available] or candidates
        # Until graph encoder training is integrated, use a deterministic proxy objective.
        return min(
            usable,
            key=lambda item: (
                item.estimated_total_latency_ms
                - item.topology_affinity * 120.0
                - item.expected_cache_hit_ratio * 320.0
            ),
        )

