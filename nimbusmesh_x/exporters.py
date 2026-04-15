from __future__ import annotations

import csv
from pathlib import Path


class ResultCSVExporter:
    def __init__(self, base_dir: str = "results") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def export_summary(self, report: dict[str, object]) -> None:
        self._append(
            self.base_dir / "latency.csv",
            ["config_name", "policy_name", "p50_latency_ms", "p95_latency_ms", "p99_latency_ms", "mean_absolute_latency_error_ms"],
            {
                "config_name": report["config_name"],
                "policy_name": report["policy_name"],
                "p50_latency_ms": report["p50_latency_ms"],
                "p95_latency_ms": report["p95_latency_ms"],
                "p99_latency_ms": report["p99_latency_ms"],
                "mean_absolute_latency_error_ms": report["mean_absolute_latency_error_ms"],
            },
        )
        self._append(
            self.base_dir / "throughput.csv",
            ["config_name", "policy_name", "throughput_tokens_per_s", "throughput_requests_per_s"],
            {
                "config_name": report["config_name"],
                "policy_name": report["policy_name"],
                "throughput_tokens_per_s": report["throughput_tokens_per_s"],
                "throughput_requests_per_s": report["throughput_requests_per_s"],
            },
        )
        self._append(
            self.base_dir / "gpu_utilization.csv",
            ["config_name", "policy_name", "gpu_utilization_proxy", "memory_utilization_proxy", "energy_proxy_total"],
            {
                "config_name": report["config_name"],
                "policy_name": report["policy_name"],
                "gpu_utilization_proxy": report["gpu_utilization_proxy"],
                "memory_utilization_proxy": report["memory_utilization_proxy"],
                "energy_proxy_total": report["energy_proxy_total"],
            },
        )
        self._append(
            self.base_dir / "cost_analysis.csv",
            ["config_name", "policy_name", "cost_per_1m_tokens_usd", "network_cost_total", "fairness_index"],
            {
                "config_name": report["config_name"],
                "policy_name": report["policy_name"],
                "cost_per_1m_tokens_usd": report["cost_per_1m_tokens_usd"],
                "network_cost_total": report["network_cost_total"],
                "fairness_index": report["fairness_index"],
            },
        )
        self._append(
            self.base_dir / "cache_hit_ratio.csv",
            ["config_name", "policy_name", "cache_hit_ratio", "cache_saved_tokens_total", "sla_miss_rate"],
            {
                "config_name": report["config_name"],
                "policy_name": report["policy_name"],
                "cache_hit_ratio": report["cache_hit_ratio"],
                "cache_saved_tokens_total": report["cache_saved_tokens_total"],
                "sla_miss_rate": report["sla_miss_rate"],
            },
        )

    def _append(self, path: Path, fieldnames: list[str], row: dict[str, object]) -> None:
        write_header = not path.exists()
        with path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerow(row)

