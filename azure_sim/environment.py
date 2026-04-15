from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency path
    yaml = None

try:  # pragma: no cover - optional dependency path
    import ray
    from ray.util.queue import Queue as RayQueue
except Exception:  # pragma: no cover - optional dependency path
    ray = None
    RayQueue = None

from nimbusmesh_x.types import InferenceRequest, RequestResult


@dataclass
class AzureNodePool:
    name: str
    gpu_type: str
    memory_gb: float
    network_bandwidth_gbps: float
    cost_per_hour: float
    node_count: int


@dataclass
class AzureAksCluster:
    name: str
    region: str
    zone: str
    node_pools: list[AzureNodePool] = field(default_factory=list)


class AzureInfraSimulator:
    def __init__(self, path: str | Path = "configs/azure_cluster.yaml", log_dir: str = "logs") -> None:
        self.path = Path(path)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.monitor_log = self.log_dir / "azure_monitor.log"
        self.cost_log = self.log_dir / "azure_cost.log"
        self.batch_log = self.log_dir / "azure_batch.log"
        self.monitor_log.write_text("")
        self.cost_log.write_text("")
        self.batch_log.write_text("")
        self.available = yaml is not None and self.path.exists()
        self.resource_groups: dict[str, list[AzureAksCluster]] = {}
        self.submitted = 0
        self.completed = 0
        self.cluster_costs: dict[str, float] = {}
        self.batch_queue = None
        if ray is not None and RayQueue is not None and os.getenv("NIMBUS_USE_RAY_BATCH", "0") == "1":
            ray.init(address=os.getenv("NIMBUS_RAY_ADDRESS"), ignore_reinit_error=True, log_to_driver=False)
            self.batch_queue = RayQueue(maxsize=50000)
        if self.available:
            self._load()

    def _load(self) -> None:
        payload = yaml.safe_load(self.path.read_text())
        for group in payload.get("resource_groups", []):
            clusters: list[AzureAksCluster] = []
            for cluster in group.get("aks_clusters", []):
                node_pools = [
                    AzureNodePool(
                        name=item["name"],
                        gpu_type=item["gpu_type"],
                        memory_gb=float(item["memory_gb"]),
                        network_bandwidth_gbps=float(item["network_bandwidth_gbps"]),
                        cost_per_hour=float(item["cost_per_hour"]),
                        node_count=int(item["node_count"]),
                    )
                    for item in cluster.get("node_pools", [])
                ]
                clusters.append(
                    AzureAksCluster(
                        name=cluster["name"],
                        region=group["region"],
                        zone=cluster["zone"],
                        node_pools=node_pools,
                    )
                )
            self.resource_groups[group["name"]] = clusters

    def note_submission(self, request: InferenceRequest) -> None:
        if not self.available:
            return
        self.submitted += 1
        if self.batch_queue is not None:
            self.batch_queue.put(
                {
                    "request_id": request.request_id,
                    "tenant_id": request.tenant_id,
                    "arrival_ts": request.arrival_ts,
                }
            )
        self._append(
            self.batch_log,
            {
                "event": "batch_submission",
                "request_id": request.request_id,
                "tenant_id": request.tenant_id,
                "submitted_total": self.submitted,
                "ray_queue_enabled": self.batch_queue is not None,
            },
        )

    def record_result(self, result: RequestResult) -> None:
        if not self.available:
            return
        self.completed += int(result.admitted)
        cluster_cost = self.cluster_costs.get(result.decision.cluster_id, 0.0) + result.cost_usd
        self.cluster_costs[result.decision.cluster_id] = cluster_cost
        self._append(
            self.monitor_log,
            {
                "event": "monitor_metric",
                "request_id": result.request.request_id,
                "cluster": result.decision.cluster_id,
                "latency_ms": result.total_latency_ms,
                "cache_hit_ratio": result.cache_hit_ratio,
                "gpu_pool": result.decision.pool_id,
            },
        )
        self._append(
            self.cost_log,
            {
                "event": "cost_metric",
                "request_id": result.request.request_id,
                "cluster": result.decision.cluster_id,
                "request_cost_usd": result.cost_usd,
                "cluster_cost_usd": round(cluster_cost, 6),
            },
        )

    def summary(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "submitted": self.submitted,
            "completed": self.completed,
            "cluster_costs": self.cluster_costs,
        }

    def _append(self, path: Path, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
