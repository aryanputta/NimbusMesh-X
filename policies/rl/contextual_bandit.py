from __future__ import annotations

from collections import defaultdict

from nimbusmesh_x.types import CandidatePlacement, InferenceRequest, RequestResult
from policies.heuristics.base import RoutingPolicy


class ContextualBanditPolicy(RoutingPolicy):
    name = "contextual_bandit"

    def __init__(self, exploration_bonus: float = 18.0) -> None:
        self.exploration_bonus = exploration_bonus
        self.counts = defaultdict(int)
        self.value = defaultdict(float)

    def choose(self, request: InferenceRequest, candidates: list[CandidatePlacement]) -> CandidatePlacement:
        usable = [candidate for candidate in candidates if candidate.available] or candidates
        total_pulls = sum(self.counts.values()) + 1

        def bandit_score(candidate: CandidatePlacement) -> float:
            key = (candidate.cluster_id, candidate.pool_id)
            mean_reward = self.value[key]
            pulls = self.counts[key]
            exploration = self.exploration_bonus / (1 + pulls)
            heuristic_hint = (
                candidate.expected_cache_hit_ratio * 120.0
                + candidate.topology_affinity * 60.0
                - candidate.queue_delay_ms * 0.08
                - candidate.accelerator_cost_per_1m_tokens * 0.08
            )
            return mean_reward + heuristic_hint + exploration

        return max(usable, key=bandit_score)

    def observe_result(self, result: RequestResult) -> None:
        key = (result.decision.cluster_id, result.decision.pool_id)
        reward = (
            (1.0 if result.sla_met else -0.9) * 120.0
            + result.cache_hit_ratio * 60.0
            - result.total_latency_ms * 0.08
            - result.cost_usd * 9.0
        )
        self.counts[key] += 1
        alpha = 1.0 / self.counts[key]
        self.value[key] = ((1 - alpha) * self.value[key]) + (alpha * reward)

