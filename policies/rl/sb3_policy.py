from __future__ import annotations

from policies.heuristics.base import RoutingPolicy
from nimbusmesh_x.types import CandidatePlacement, InferenceRequest

try:  # pragma: no cover - optional dependency path
    from stable_baselines3 import PPO  # noqa: F401
except Exception:  # pragma: no cover - optional dependency path
    PPO = None


class SB3Policy(RoutingPolicy):
    name = "sb3_placeholder"

    def __init__(self) -> None:
        self.available = PPO is not None

    def choose(self, request: InferenceRequest, candidates: list[CandidatePlacement]) -> CandidatePlacement:
        usable = [candidate for candidate in candidates if candidate.available] or candidates
        # Placeholder policy until PPO environment wiring is finalized.
        return min(usable, key=lambda item: item.estimated_total_latency_ms)

