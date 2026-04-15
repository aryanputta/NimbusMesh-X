from __future__ import annotations

import json
from pathlib import Path

from nimbusmesh_x.types import RequestResult


class StructuredLogFanout:
    def __init__(self, base_dir: str = "logs") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.scheduler_log_v2 = self.base_dir / "scheduler.log"
        self.cache_log_v2 = self.base_dir / "cache.log"
        self.topology_log_v2 = self.base_dir / "topology.log"
        self.latency_log_v2 = self.base_dir / "latency.log"
        self.scheduler_log = self.base_dir / "scheduler_decisions.log"
        self.cache_log = self.base_dir / "cache_hits.log"
        self.topology_log = self.base_dir / "topology_scores.log"
        self.latency_log = self.base_dir / "latency_metrics.log"
        self.failure_log = self.base_dir / "failure_events.log"
        for path in [
            self.scheduler_log,
            self.cache_log,
            self.topology_log,
            self.latency_log,
            self.failure_log,
            self.scheduler_log_v2,
            self.cache_log_v2,
            self.topology_log_v2,
            self.latency_log_v2,
        ]:
            if not path.exists():
                path.write_text("")

    def emit_result(self, result: RequestResult) -> None:
        base = {
            "timestamp": result.request.arrival_ts,
            "request_id": result.request.request_id,
            "tenant_id": result.request.tenant_id,
            "model_id": result.request.model_id,
            "chosen_cluster": result.decision.cluster_id,
            "gpu_id": result.decision.pool_id,
            "backend": result.decision.backend_name,
            "latency_estimate_ms": result.decision.estimated_latency_ms,
            "actual_latency_ms": result.total_latency_ms,
            "cache_hit": result.cache_hit_ratio > 0.0,
            "cache_hit_ratio": result.cache_hit_ratio,
            "cost_usd": result.cost_usd,
        }
        self._append(self.scheduler_log, base | {"type": "scheduler_decision"})
        self._append(self.scheduler_log_v2, base | {"type": "scheduler_decision"})
        self._append(
            self.topology_log,
            base
            | {
                "type": "topology_score",
                "topology_affinity": result.decision.topology_affinity,
                "network_cost": result.network_cost,
            },
        )
        self._append(
            self.topology_log_v2,
            base
            | {
                "type": "topology_score",
                "topology_affinity": result.decision.topology_affinity,
                "network_cost": result.network_cost,
            },
        )
        self._append(
            self.latency_log,
            base
            | {
                "type": "latency_metric",
                "queue_delay_ms": result.queue_delay_ms,
                "prefill_latency_ms": result.prefill_latency_ms,
                "decode_latency_ms": result.decode_latency_ms,
                "sla_met": result.sla_met,
            },
        )
        self._append(
            self.latency_log_v2,
            base
            | {
                "type": "latency_metric",
                "queue_delay_ms": result.queue_delay_ms,
                "prefill_latency_ms": result.prefill_latency_ms,
                "decode_latency_ms": result.decode_latency_ms,
                "sla_met": result.sla_met,
            },
        )
        if result.cache_hit_ratio > 0.0:
            self._append(
                self.cache_log,
                base
                | {
                    "type": "cache_hit",
                    "cache_saved_tokens": result.cache_saved_tokens,
                },
            )
            self._append(
                self.cache_log_v2,
                base
                | {
                    "type": "cache_hit",
                    "cache_saved_tokens": result.cache_saved_tokens,
                },
            )

    def emit_failure_event(self, payload: dict[str, object]) -> None:
        self._append(self.failure_log, payload)

    def _append(self, path: Path, payload: dict[str, object]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
