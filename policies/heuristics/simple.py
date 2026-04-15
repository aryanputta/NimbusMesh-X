from __future__ import annotations

from collections import defaultdict

from nimbusmesh_x.types import CandidatePlacement, InferenceRequest, RequestResult, SLA_PRIORITY
from policies.heuristics.base import RoutingPolicy


def _available_candidates(candidates: list[CandidatePlacement]) -> list[CandidatePlacement]:
    usable = [candidate for candidate in candidates if candidate.available]
    if usable:
        return usable
    return candidates


class RoundRobinPolicy(RoutingPolicy):
    name = "round_robin"

    def __init__(self) -> None:
        self._cursor = 0

    def choose(self, request: InferenceRequest, candidates: list[CandidatePlacement]) -> CandidatePlacement:
        usable = _available_candidates(candidates)
        choice = usable[self._cursor % len(usable)]
        self._cursor += 1
        return choice


class LeastQueuePolicy(RoutingPolicy):
    name = "least_queue"

    def choose(self, request: InferenceRequest, candidates: list[CandidatePlacement]) -> CandidatePlacement:
        usable = _available_candidates(candidates)
        return min(
            usable,
            key=lambda item: (
                item.queue_delay_ms,
                item.network_cost,
                item.accelerator_cost_per_1m_tokens,
            ),
        )


class TopologyGreedyPolicy(RoutingPolicy):
    name = "topology_greedy"

    def choose(self, request: InferenceRequest, candidates: list[CandidatePlacement]) -> CandidatePlacement:
        usable = _available_candidates(candidates)
        return min(
            usable,
            key=lambda item: (
                item.queue_delay_ms
                + (item.network_cost * 14.0)
                - (item.topology_affinity * 110.0)
                + (item.congestion_score * 80.0)
            ),
        )


class CacheAwarePolicy(RoutingPolicy):
    name = "cache_aware"

    def choose(self, request: InferenceRequest, candidates: list[CandidatePlacement]) -> CandidatePlacement:
        usable = _available_candidates(candidates)
        return min(
            usable,
            key=lambda item: (
                -(item.expected_cache_hit_ratio * 1000.0),
                item.queue_delay_ms,
                item.network_cost,
                item.accelerator_cost_per_1m_tokens,
            ),
        )


class MultiObjectivePolicy(RoutingPolicy):
    name = "multi_objective"

    def choose(self, request: InferenceRequest, candidates: list[CandidatePlacement]) -> CandidatePlacement:
        usable = _available_candidates(candidates)
        sla_priority = SLA_PRIORITY[request.sla_class]
        def objective(item: CandidatePlacement) -> float:
            latency_weight = 1.4 if sla_priority == 3 else 1.1 if sla_priority == 2 else 0.75
            cost_weight = 0.25 if sla_priority == 3 else 0.55
            premium_penalty = 0.0
            if request.sla_class == "best_effort" and item.premium:
                premium_penalty = 70.0
            if request.sla_class == "realtime" and not item.premium:
                premium_penalty = 25.0
            return (
                item.estimated_total_latency_ms * latency_weight
                + item.network_cost * 18.0
                + item.accelerator_cost_per_1m_tokens * cost_weight
                + item.congestion_score * 90.0
                - item.expected_cache_hit_ratio * 450.0
                - item.topology_affinity * 85.0
                + item.fairness_penalty * 110.0
                - item.score_breakdown.get("cuda_cache_bonus", 0.0) * 70.0
                + item.score_breakdown.get("cuda_topology_penalty", 0.0) * 65.0
                + item.score_breakdown.get("cuda_load_penalty", 0.0) * 55.0
                + premium_penalty
            )
        return min(usable, key=objective)


class FailureAwareSpreadPolicy(RoutingPolicy):
    name = "spread"

    def __init__(self) -> None:
        self._pool_counts = defaultdict(int)

    def choose(self, request: InferenceRequest, candidates: list[CandidatePlacement]) -> CandidatePlacement:
        usable = _available_candidates(candidates)
        choice = min(
            usable,
            key=lambda item: (
                self._pool_counts[(item.cluster_id, item.pool_id)],
                item.queue_delay_ms,
                item.network_cost,
            ),
        )
        self._pool_counts[(choice.cluster_id, choice.pool_id)] += 1
        return choice

    def observe_result(self, result: RequestResult) -> None:
        key = (result.decision.cluster_id, result.decision.pool_id)
        self._pool_counts[key] = max(0, self._pool_counts[key] - 1)
