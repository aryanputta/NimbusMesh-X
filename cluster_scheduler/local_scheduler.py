from __future__ import annotations

from cache_directory.directory import KVCacheDirectory
from nimbusmesh_x.types import (
    CandidatePlacement,
    InferenceRequest,
    RequestResult,
    RoutingDecision,
    estimate_request_memory_gb,
)
from serving_backends.base import BackendAdapter


class LocalClusterScheduler:
    def __init__(self, cache_directory: KVCacheDirectory) -> None:
        self.cache_directory = cache_directory

    def place_request(
        self,
        request: InferenceRequest,
        candidate: CandidatePlacement,
        decision: RoutingDecision,
        pool,
        backend: BackendAdapter,
        now: float,
    ) -> RequestResult:
        slot_index = min(range(len(pool.slot_available_at)), key=pool.slot_available_at.__getitem__)
        actual_start_ts = max(now, pool.slot_available_at[slot_index])
        queue_delay_ms = max(0.0, actual_start_ts - now) * 1000.0
        prefill_ms, decode_ms = backend.estimate_latency_ms(
            request=request,
            pool=pool,
            cache_hit_ratio=candidate.expected_cache_hit_ratio,
            topology_affinity=candidate.topology_affinity,
            network_cost=candidate.network_cost,
            congestion_score=candidate.congestion_score,
        )
        memory_gb = estimate_request_memory_gb(
            prompt_tokens=request.prompt_tokens,
            generation_tokens=request.generation_tokens,
            model_id=request.model_id,
            cache_saved_tokens=candidate.expected_cache_saved_tokens,
        )
        completion_ts = actual_start_ts + ((prefill_ms + decode_ms) / 1000.0)
        pool.slot_available_at[slot_index] = completion_ts
        pool.inflight_memory.append((completion_ts, memory_gb))
        pool.active_memory_gb += memory_gb
        pool.decision_count += 1

        total_latency_ms = queue_delay_ms + prefill_ms + decode_ms
        cost_usd = pool.cost_per_1m_tokens * (request.total_tokens / 1_000_000.0)
        energy_proxy = pool.energy_proxy * (request.total_tokens / 1000.0)
        sla_met = total_latency_ms <= request.max_latency_ms
        result = RequestResult(
            request=request,
            decision=decision,
            admitted=True,
            actual_start_ts=actual_start_ts,
            completion_ts=completion_ts,
            queue_delay_ms=round(queue_delay_ms, 4),
            prefill_latency_ms=round(prefill_ms, 4),
            decode_latency_ms=round(decode_ms, 4),
            total_latency_ms=round(total_latency_ms, 4),
            cache_hit_ratio=candidate.expected_cache_hit_ratio,
            cache_saved_tokens=candidate.expected_cache_saved_tokens,
            memory_gb=round(memory_gb, 4),
            cost_usd=round(cost_usd, 6),
            energy_proxy=round(energy_proxy, 4),
            network_cost=round(candidate.network_cost, 4),
            sla_met=sla_met,
        )
        self.cache_directory.observe(result)
        return result
