from pathlib import Path

from benchmarks.harness import BenchmarkHarness
from nimbusmesh_x.config import load_config
from nimbusmesh_x.metrics import MetricsCollector
from nimbusmesh_x.types import InferenceRequest, RequestResult, RoutingDecision
from simulators.engine import SimulationEngine


ROOT = Path(__file__).resolve().parents[1]


def _result(latency_ms: float, sla_met: bool) -> RequestResult:
    request = InferenceRequest(
        request_id=f"r-{latency_ms}",
        tenant_id="tenant-a",
        model_id="llama-3-8b",
        prompt_tokens=1024,
        generation_tokens=256,
        arrival_ts=0.0,
        session_id="s1",
    )
    decision = RoutingDecision(
        request_id=request.request_id,
        policy_name="least_queue",
        cluster_id="c1",
        pool_id="p1",
        backend_name="mock",
        estimated_latency_ms=latency_ms,
        estimated_queue_delay_ms=0.0,
        estimated_cache_hit_ratio=0.0,
        topology_affinity=0.5,
        network_cost=1.0,
        accelerator_cost_per_1m_tokens=1.0,
        fairness_penalty=0.0,
    )
    return RequestResult(
        request=request,
        decision=decision,
        admitted=True,
        actual_start_ts=0.0,
        completion_ts=latency_ms / 1000.0,
        queue_delay_ms=0.0,
        prefill_latency_ms=latency_ms / 2,
        decode_latency_ms=latency_ms / 2,
        total_latency_ms=latency_ms,
        cache_hit_ratio=0.0,
        cache_saved_tokens=0,
        memory_gb=2.0,
        cost_usd=0.01,
        energy_proxy=1.0,
        network_cost=1.0,
        sla_met=sla_met,
    )


def test_metrics_sla_accounting() -> None:
    metrics = MetricsCollector()
    metrics.note_submission("tenant-a")
    metrics.note_submission("tenant-a")
    metrics.record(_result(100.0, sla_met=True))
    metrics.record(_result(5000.0, sla_met=False))
    report = metrics.summary(duration_s=1.0, policy_name="least_queue", config_name="unit")
    assert report["sla_miss_rate"] == 0.5


def test_benchmark_repeatability_for_fixed_seed() -> None:
    config = load_config(ROOT / "configs" / "single_cluster_baseline.json")
    first = SimulationEngine(config.with_seed(77)).run()
    second = SimulationEngine(config.with_seed(77)).run()
    assert first == second


def test_benchmark_harness_returns_reports() -> None:
    config = load_config(ROOT / "configs" / "single_cluster_baseline.json")
    harness = BenchmarkHarness(config, output_dir=str(ROOT / "experiments" / "results"))
    reports = harness.run(policies=["round_robin"], seeds=[3])
    assert len(reports) == 1
    assert reports[0]["policy_name"] == "round_robin"

