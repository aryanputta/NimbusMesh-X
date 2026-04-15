from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

from nimbusmesh_x.types import RequestResult


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def _jains_index(values: list[float]) -> float:
    if not values:
        return 1.0
    numerator = sum(values) ** 2
    denominator = len(values) * sum(v * v for v in values)
    if denominator == 0:
        return 1.0
    return numerator / denominator


class MetricsCollector:
    def __init__(self) -> None:
        self.results: list[RequestResult] = []
        self.tenant_completed = defaultdict(int)
        self.tenant_submitted = defaultdict(int)

    def note_submission(self, tenant_id: str) -> None:
        self.tenant_submitted[tenant_id] += 1

    def record(self, result: RequestResult) -> None:
        self.results.append(result)
        self.tenant_completed[result.request.tenant_id] += int(result.admitted)

    def summary(
        self,
        duration_s: float,
        policy_name: str,
        config_name: str,
        total_slots: int = 1,
        total_memory_gb: float = 1.0,
    ) -> dict[str, float | int | str]:
        latencies = [item.total_latency_ms for item in self.results if item.admitted]
        prefill = [item.prefill_latency_ms for item in self.results if item.admitted]
        decode = [item.decode_latency_ms for item in self.results if item.admitted]
        total_tokens = sum(item.request.total_tokens for item in self.results if item.admitted)
        total_cost = sum(item.cost_usd for item in self.results if item.admitted)
        total_energy = sum(item.energy_proxy for item in self.results if item.admitted)
        total_network_cost = sum(item.network_cost for item in self.results if item.admitted)
        total_cache_saved_tokens = sum(item.cache_saved_tokens for item in self.results if item.admitted)
        total_busy_s = sum((item.prefill_latency_ms + item.decode_latency_ms) / 1000.0 for item in self.results if item.admitted)
        mean_memory_gb = (
            sum(item.memory_gb for item in self.results if item.admitted) / max(1, len(latencies))
        )
        estimation_error = [
            abs(item.decision.estimated_latency_ms - item.total_latency_ms) for item in self.results if item.admitted
        ]
        cache_hit_ratio = (
            sum(item.cache_hit_ratio for item in self.results if item.admitted) / max(1, len(latencies))
        )
        sla_miss_rate = 1.0 - (
            sum(1 for item in self.results if item.admitted and item.sla_met) / max(1, len(latencies))
        )
        fairness_values = []
        for tenant_id, submitted in self.tenant_submitted.items():
            fairness_values.append(self.tenant_completed[tenant_id] / max(1, submitted))
        report: dict[str, float | int | str] = {
            "config_name": config_name,
            "policy_name": policy_name,
            "requests_total": len(self.results),
            "requests_admitted": len(latencies),
            "p50_latency_ms": round(_quantile(latencies, 0.5), 2),
            "p95_latency_ms": round(_quantile(latencies, 0.95), 2),
            "p99_latency_ms": round(_quantile(latencies, 0.99), 2),
            "p50_prefill_ms": round(_quantile(prefill, 0.5), 2),
            "p95_prefill_ms": round(_quantile(prefill, 0.95), 2),
            "p50_decode_ms": round(_quantile(decode, 0.5), 2),
            "throughput_tokens_per_s": round(total_tokens / max(duration_s, 1e-9), 2),
            "throughput_requests_per_s": round(len(latencies) / max(duration_s, 1e-9), 2),
            "cache_hit_ratio": round(cache_hit_ratio, 4),
            "cache_saved_tokens_total": total_cache_saved_tokens,
            "sla_miss_rate": round(sla_miss_rate, 4),
            "cost_per_1m_tokens_usd": round((total_cost / max(total_tokens, 1)) * 1_000_000, 4),
            "energy_proxy_total": round(total_energy, 4),
            "network_cost_total": round(total_network_cost, 4),
            "gpu_utilization_proxy": round(min(1.0, total_busy_s / max(duration_s * max(1, total_slots), 1e-9)), 4),
            "memory_utilization_proxy": round(min(1.0, mean_memory_gb / max(total_memory_gb, 1e-9)), 4),
            "mean_absolute_latency_error_ms": round(sum(estimation_error) / max(1, len(estimation_error)), 4),
            "fairness_index": round(_jains_index(fairness_values), 4),
        }
        return report

    def render_prometheus(self) -> str:
        latencies = [item.total_latency_ms for item in self.results if item.admitted]
        cache_hit_ratio = (
            sum(item.cache_hit_ratio for item in self.results if item.admitted) / max(1, len(latencies))
        )
        lines = [
            "# HELP nimbusmesh_requests_total Total number of processed requests.",
            "# TYPE nimbusmesh_requests_total counter",
            f"nimbusmesh_requests_total {len(self.results)}",
            "# HELP nimbusmesh_latency_p95_ms Estimated p95 end-to-end latency.",
            "# TYPE nimbusmesh_latency_p95_ms gauge",
            f"nimbusmesh_latency_p95_ms {_quantile(latencies, 0.95):.3f}",
            "# HELP nimbusmesh_cache_hit_ratio Mean cache hit ratio.",
            "# TYPE nimbusmesh_cache_hit_ratio gauge",
            f"nimbusmesh_cache_hit_ratio {cache_hit_ratio:.6f}",
        ]
        return "\n".join(lines) + "\n"

    def write_summary(self, path: str | None, summary: dict[str, float | int | str]) -> None:
        if not path:
            return
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(summary, indent=2, sort_keys=True))
