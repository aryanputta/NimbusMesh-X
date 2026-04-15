from __future__ import annotations

from collections import defaultdict

from cache_directory.directory import KVCacheDirectory
from cluster_scheduler.local_scheduler import LocalClusterScheduler
from cuda_kernels.runtime import CudaScoringEngine
from grpc_layer.client import GrpcSchedulerClient
from nimbusmesh_x.config import ExperimentConfig
from nimbusmesh_x.types import (
    CandidatePlacement,
    ClusterRuntime,
    InferenceRequest,
    PoolRuntime,
    RoutingDecision,
    TenantStats,
    estimate_request_memory_gb,
)
from policies.gnn.placeholder import GNNPlaceholderPolicy
from policies.gnn.pyg_policy import PyGGNNPolicy
from policies.heuristics.base import RoutingPolicy
from policies.heuristics.simple import (
    CacheAwarePolicy,
    FailureAwareSpreadPolicy,
    LeastQueuePolicy,
    MultiObjectivePolicy,
    RoundRobinPolicy,
    TopologyGreedyPolicy,
)
from policies.rl.contextual_bandit import ContextualBanditPolicy
from policies.rl.sb3_policy import SB3Policy
from scheduler_core.cpp_bridge import CppSchedulerCore
from serving_backends.base import BackendAdapter
from serving_backends.mock_backend import MockBackend
from serving_backends.triton_backend import TritonBackend
from serving_backends.vllm_backend import VLLMBackend
from topology_service.graph import TopologyService


class NimbusMeshControlPlane:
    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config
        self.topology = TopologyService(config)
        self.cache_directory = KVCacheDirectory()
        self.scheduler = LocalClusterScheduler(self.cache_directory)
        self.backends: dict[str, BackendAdapter] = {
            "mock": MockBackend(),
            "vllm": VLLMBackend(),
            "triton": TritonBackend(),
        }
        self.cuda_engine = CudaScoringEngine()
        self.grpc_client = GrpcSchedulerClient()
        self.cpp_core = CppSchedulerCore()
        self.clusters = self._build_runtime_clusters(config)
        self.tenant_stats: dict[str, TenantStats] = defaultdict(TenantStats)
        self.tenant_weights = config.workload.tenant_weights
        self.policy = self._build_policy(config.policy)

    def _build_policy(self, name: str) -> RoutingPolicy:
        registry: dict[str, RoutingPolicy] = {
            "round_robin": RoundRobinPolicy(),
            "least_queue": LeastQueuePolicy(),
            "topology_greedy": TopologyGreedyPolicy(),
            "cache_aware": CacheAwarePolicy(),
            "multi_objective": MultiObjectivePolicy(),
            "contextual_bandit": ContextualBanditPolicy(),
            "sb3_placeholder": SB3Policy(),
            "spread": FailureAwareSpreadPolicy(),
            "gnn_placeholder": GNNPlaceholderPolicy(),
            "pyg_placeholder": PyGGNNPolicy(),
        }
        if name not in registry:
            raise ValueError(f"Unknown policy: {name}")
        return registry[name]

    def _build_runtime_clusters(self, config: ExperimentConfig) -> dict[str, ClusterRuntime]:
        clusters: dict[str, ClusterRuntime] = {}
        for cluster_spec in config.clusters:
            cluster = ClusterRuntime(
                cluster_id=cluster_spec.cluster_id,
                zone=cluster_spec.zone,
                ingress_cost=cluster_spec.ingress_cost,
                network_costs=cluster_spec.network_costs,
                base_congestion=cluster_spec.base_congestion,
                failure_windows=list(cluster_spec.failure_windows),
                congestion_windows=list(cluster_spec.congestion_windows),
            )
            for pool_spec in cluster_spec.pools:
                cluster.pools[pool_spec.pool_id] = PoolRuntime(
                    cluster_id=cluster.cluster_id,
                    zone=cluster.zone,
                    pool_id=pool_spec.pool_id,
                    backend_name=pool_spec.backend_name,
                    accelerator_type=pool_spec.accelerator_type,
                    supported_models=pool_spec.supported_models,
                    prefill_tps=pool_spec.prefill_tps,
                    decode_tps=pool_spec.decode_tps,
                    memory_gb=pool_spec.memory_gb,
                    gpu_count=pool_spec.gpu_count,
                    parallel_slots=pool_spec.parallel_slots,
                    cost_per_1m_tokens=pool_spec.cost_per_1m_tokens,
                    energy_proxy=pool_spec.energy_proxy,
                    topology_tier=pool_spec.topology_tier,
                    premium=pool_spec.premium,
                    queue_limit=pool_spec.queue_limit,
                )
            clusters[cluster.cluster_id] = cluster
        return clusters

    def refresh(self, now: float) -> None:
        for cluster in self.clusters.values():
            cluster_congestion = cluster.effective_congestion(now)
            for pool in cluster.pools.values():
                pool.congestion_score = cluster_congestion
                pool.refresh(now)
                pool.cache_reserved_gb = self.cache_directory.reserved_gb(cluster.cluster_id, pool.pool_id, now)

    def note_submission(self, request: InferenceRequest) -> None:
        self.tenant_stats[request.tenant_id].submitted += 1

    def build_candidates(self, request: InferenceRequest, now: float) -> list[CandidatePlacement]:
        candidates: list[CandidatePlacement] = []
        for cluster in self.clusters.values():
            cluster_down = cluster.unavailable(now)
            for pool in cluster.pools.values():
                model_supported = not pool.supported_models or request.model_id in pool.supported_models
                available = True
                rejection_reason = None
                memory_headroom = pool.memory_headroom_gb()
                cache_hit_ratio, cache_saved_tokens = self.cache_directory.score(
                    request=request,
                    cluster_id=cluster.cluster_id,
                    pool_id=pool.pool_id,
                    now=now,
                )
                needed_memory = estimate_request_memory_gb(
                    prompt_tokens=request.prompt_tokens,
                    generation_tokens=request.generation_tokens,
                    model_id=request.model_id,
                    cache_saved_tokens=cache_saved_tokens,
                )
                if cluster_down:
                    available = False
                    rejection_reason = "cluster-unavailable"
                elif not model_supported:
                    available = False
                    rejection_reason = "unsupported-model"
                elif pool.inflight_count(now) >= pool.queue_limit:
                    available = False
                    rejection_reason = "queue-limit"
                elif memory_headroom < needed_memory:
                    available = False
                    rejection_reason = "memory-pressure"

                topology_affinity = self.topology.pool_affinity(cluster.cluster_id, pool.pool_id, request.prompt_tokens)
                network_cost = cluster.ingress_cost + self.topology.route_cost(cluster.cluster_id, pool.pool_id)
                backend = self.backends[pool.backend_name]
                projected_prefill_ms, projected_decode_ms = backend.estimate_latency_ms(
                    request=request,
                    pool=pool,
                    cache_hit_ratio=cache_hit_ratio,
                    topology_affinity=topology_affinity,
                    network_cost=network_cost,
                    congestion_score=pool.congestion_score,
                )
                fairness_penalty = self._fairness_penalty(request.tenant_id)
                score_breakdown = {
                    "queue_delay_ms": round(pool.queue_delay_ms(now), 4),
                    "cache_hit_ratio": cache_hit_ratio,
                    "topology_affinity": topology_affinity,
                    "network_cost": round(network_cost, 4),
                    "congestion_score": round(pool.congestion_score, 4),
                    "memory_headroom_gb": round(memory_headroom, 4),
                    "fairness_penalty": round(fairness_penalty, 4),
                }
                candidates.append(
                    CandidatePlacement(
                        cluster_id=cluster.cluster_id,
                        pool_id=pool.pool_id,
                        backend_name=pool.backend_name,
                        accelerator_type=pool.accelerator_type,
                        queue_delay_ms=round(pool.queue_delay_ms(now), 4),
                        projected_prefill_ms=projected_prefill_ms,
                        projected_decode_ms=projected_decode_ms,
                        expected_cache_hit_ratio=cache_hit_ratio,
                        expected_cache_saved_tokens=cache_saved_tokens,
                        topology_affinity=topology_affinity,
                        network_cost=round(network_cost, 4),
                        congestion_score=round(pool.congestion_score, 4),
                        memory_headroom_gb=round(memory_headroom, 4),
                        accelerator_cost_per_1m_tokens=pool.cost_per_1m_tokens,
                        fairness_penalty=fairness_penalty,
                        premium=pool.premium,
                        available=available,
                        rejection_reason=rejection_reason,
                        score_breakdown=score_breakdown,
                    )
                )
        self.cuda_engine.enrich_candidates(candidates)
        return candidates

    def route(self, request: InferenceRequest, now: float) -> tuple[CandidatePlacement, RoutingDecision]:
        candidates = self.build_candidates(request, now)
        choice = self._choose_candidate(request, candidates)
        decision = RoutingDecision(
            request_id=request.request_id,
            policy_name=self.policy.name,
            cluster_id=choice.cluster_id,
            pool_id=choice.pool_id,
            backend_name=choice.backend_name,
            estimated_latency_ms=round(choice.estimated_total_latency_ms, 4),
            estimated_queue_delay_ms=round(choice.queue_delay_ms, 4),
            estimated_cache_hit_ratio=choice.expected_cache_hit_ratio,
            topology_affinity=choice.topology_affinity,
            network_cost=choice.network_cost,
            accelerator_cost_per_1m_tokens=choice.accelerator_cost_per_1m_tokens,
            fairness_penalty=choice.fairness_penalty,
            score_breakdown=choice.score_breakdown,
        )
        return choice, decision

    def _choose_candidate(self, request: InferenceRequest, candidates: list[CandidatePlacement]) -> CandidatePlacement:
        grpc_index = self.grpc_client.choose(request, candidates)
        if grpc_index is not None:
            return candidates[grpc_index]
        cpp_index = self.cpp_core.choose(request, candidates)
        if cpp_index is not None:
            return candidates[cpp_index]
        return self.policy.choose(request, candidates)

    def execute(self, request: InferenceRequest, now: float):
        candidate, decision = self.route(request, now)
        pool = self.clusters[candidate.cluster_id].pools[candidate.pool_id]
        backend = self.backends[candidate.backend_name]
        if not candidate.available:
            from nimbusmesh_x.types import RequestResult

            return RequestResult(
                request=request,
                decision=decision,
                admitted=False,
                actual_start_ts=now,
                completion_ts=now,
                queue_delay_ms=0.0,
                prefill_latency_ms=0.0,
                decode_latency_ms=0.0,
                total_latency_ms=0.0,
                cache_hit_ratio=0.0,
                cache_saved_tokens=0,
                memory_gb=0.0,
                cost_usd=0.0,
                energy_proxy=0.0,
                network_cost=candidate.network_cost,
                sla_met=False,
                rejection_reason=candidate.rejection_reason,
            )
        result = self.scheduler.place_request(
            request=request,
            candidate=candidate,
            decision=decision,
            pool=pool,
            backend=backend,
            now=now,
        )
        self.tenant_stats[request.tenant_id].completed += 1
        self.tenant_stats[request.tenant_id].total_latency_ms += result.total_latency_ms
        self.tenant_stats[request.tenant_id].sla_misses += int(not result.sla_met)
        pool.completed_count += 1
        self.policy.observe_result(result)
        return result

    def _fairness_penalty(self, tenant_id: str) -> float:
        total_completed = sum(item.completed for item in self.tenant_stats.values())
        if total_completed == 0:
            return 0.0
        actual_share = self.tenant_stats[tenant_id].completed / total_completed
        expected_share = self.tenant_weights.get(tenant_id, 1.0) / max(1e-9, sum(self.tenant_weights.values()))
        return max(0.0, actual_share - expected_share) * self.config.fairness_strength

    def topology_snapshot(self) -> dict[str, object]:
        return self.topology.snapshot()

    def cache_snapshot(self, now: float) -> dict[str, object]:
        return self.cache_directory.snapshot(now)
