from cache_directory.directory import KVCacheDirectory
from nimbusmesh_x.types import InferenceRequest, RequestResult, RoutingDecision


def _result(now: float, completion_ts: float) -> RequestResult:
    request = InferenceRequest(
        request_id="r1",
        tenant_id="tenant-a",
        model_id="llama-3-8b",
        prompt_tokens=2048,
        generation_tokens=512,
        arrival_ts=now,
        session_id="s1",
    )
    decision = RoutingDecision(
        request_id="r1",
        policy_name="cache_aware",
        cluster_id="c1",
        pool_id="p1",
        backend_name="mock",
        estimated_latency_ms=100.0,
        estimated_queue_delay_ms=10.0,
        estimated_cache_hit_ratio=0.0,
        topology_affinity=0.8,
        network_cost=1.0,
        accelerator_cost_per_1m_tokens=1.0,
        fairness_penalty=0.0,
    )
    return RequestResult(
        request=request,
        decision=decision,
        admitted=True,
        actual_start_ts=now,
        completion_ts=completion_ts,
        queue_delay_ms=10.0,
        prefill_latency_ms=50.0,
        decode_latency_ms=40.0,
        total_latency_ms=100.0,
        cache_hit_ratio=0.0,
        cache_saved_tokens=0,
        memory_gb=4.0,
        cost_usd=0.01,
        energy_proxy=1.0,
        network_cost=1.0,
        sla_met=True,
    )


def test_cache_entry_not_visible_until_completion() -> None:
    directory = KVCacheDirectory()
    result = _result(now=0.0, completion_ts=5.0)
    directory.observe(result)
    ratio_before, _ = directory.score(result.request, "c1", "p1", now=2.0)
    ratio_after, _ = directory.score(result.request, "c1", "p1", now=5.1)
    assert ratio_before == 0.0
    assert ratio_after > 0.0

