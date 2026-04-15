from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DistributionConfig:
    distribution: str = "lognormal"
    mean: float = 1024.0
    sigma: float = 0.7
    min: int = 32
    max: int = 32768

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DistributionConfig":
        return cls(
            distribution=payload.get("distribution", "lognormal"),
            mean=float(payload.get("mean", 1024.0)),
            sigma=float(payload.get("sigma", 0.7)),
            min=int(payload.get("min", 32)),
            max=int(payload.get("max", 32768)),
        )


@dataclass(frozen=True)
class WorkloadConfig:
    request_count: int
    duration_s: float
    arrival_pattern: str
    prompt_tokens: DistributionConfig
    generation_tokens: DistributionConfig
    tenant_weights: dict[str, float]
    model_mix: dict[str, float]
    sla_mix: dict[str, float]
    trace_path: str | None = None
    trace_replay_speed: float = 1.0
    trace_default_model: str = "llama-3-8b"
    trace_default_sla: str = "interactive"
    trace_limit: int | None = None
    session_reuse_probability: float = 0.4
    burst_factor: float = 1.0
    cache_hostility: float = 0.0

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WorkloadConfig":
        return cls(
            request_count=int(payload["request_count"]),
            duration_s=float(payload.get("duration_s", 60.0)),
            arrival_pattern=payload.get("arrival_pattern", "poisson"),
            prompt_tokens=DistributionConfig.from_dict(payload.get("prompt_tokens", {})),
            generation_tokens=DistributionConfig.from_dict(payload.get("generation_tokens", {})),
            tenant_weights={k: float(v) for k, v in payload.get("tenant_weights", {"tenant-a": 1.0}).items()},
            model_mix={k: float(v) for k, v in payload.get("model_mix", {"llama-3-8b": 1.0}).items()},
            sla_mix={k: float(v) for k, v in payload.get("sla_mix", {"interactive": 1.0}).items()},
            trace_path=payload.get("trace_path"),
            trace_replay_speed=float(payload.get("trace_replay_speed", 1.0)),
            trace_default_model=payload.get("trace_default_model", "llama-3-8b"),
            trace_default_sla=payload.get("trace_default_sla", "interactive"),
            trace_limit=int(payload["trace_limit"]) if payload.get("trace_limit") is not None else None,
            session_reuse_probability=float(payload.get("session_reuse_probability", 0.4)),
            burst_factor=float(payload.get("burst_factor", 1.0)),
            cache_hostility=float(payload.get("cache_hostility", 0.0)),
        )


@dataclass(frozen=True)
class PoolSpec:
    pool_id: str
    backend_name: str
    accelerator_type: str
    supported_models: tuple[str, ...]
    prefill_tps: float
    decode_tps: float
    memory_gb: float
    gpu_count: int
    parallel_slots: int
    cost_per_1m_tokens: float
    energy_proxy: float
    topology_tier: str
    premium: bool = False
    queue_limit: int = 1024

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PoolSpec":
        models = payload.get("supported_models")
        if models is None:
            supported_models = tuple()
        else:
            supported_models = tuple(str(item) for item in models)
        return cls(
            pool_id=payload["pool_id"],
            backend_name=payload.get("backend_name", "mock"),
            accelerator_type=payload["accelerator_type"],
            supported_models=supported_models,
            prefill_tps=float(payload["prefill_tps"]),
            decode_tps=float(payload["decode_tps"]),
            memory_gb=float(payload["memory_gb"]),
            gpu_count=int(payload["gpu_count"]),
            parallel_slots=int(payload.get("parallel_slots", payload["gpu_count"])),
            cost_per_1m_tokens=float(payload["cost_per_1m_tokens"]),
            energy_proxy=float(payload.get("energy_proxy", 1.0)),
            topology_tier=payload.get("topology_tier", "pcie-fabric"),
            premium=bool(payload.get("premium", False)),
            queue_limit=int(payload.get("queue_limit", 1024)),
        )


@dataclass(frozen=True)
class ClusterSpec:
    cluster_id: str
    zone: str
    ingress_cost: float
    network_costs: dict[str, float]
    base_congestion: float
    pools: tuple[PoolSpec, ...]
    gpu_topology_file: str | None = None
    failure_windows: tuple[tuple[float, float], ...] = field(default_factory=tuple)
    congestion_windows: tuple[tuple[float, float, float], ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ClusterSpec":
        return cls(
            cluster_id=payload["cluster_id"],
            zone=payload["zone"],
            ingress_cost=float(payload.get("ingress_cost", 1.0)),
            network_costs={k: float(v) for k, v in payload.get("network_costs", {}).items()},
            base_congestion=float(payload.get("base_congestion", 0.0)),
            pools=tuple(PoolSpec.from_dict(item) for item in payload["pools"]),
            gpu_topology_file=payload.get("gpu_topology_file"),
            failure_windows=tuple((float(s), float(e)) for s, e in payload.get("failure_windows", [])),
            congestion_windows=tuple(
                (float(s), float(e), float(m)) for s, e, m in payload.get("congestion_windows", [])
            ),
        )


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    seed: int
    policy: str
    workload: WorkloadConfig
    clusters: tuple[ClusterSpec, ...]
    decision_log_path: str | None = None
    metrics_output_path: str | None = None
    fairness_strength: float = 0.25
    target_fairness: float = 0.95

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ExperimentConfig":
        return cls(
            name=payload.get("name", "nimbusmesh-x-experiment"),
            seed=int(payload.get("seed", 7)),
            policy=payload.get("policy", "multi_objective"),
            workload=WorkloadConfig.from_dict(payload["workload"]),
            clusters=tuple(ClusterSpec.from_dict(item) for item in payload["clusters"]),
            decision_log_path=payload.get("decision_log_path"),
            metrics_output_path=payload.get("metrics_output_path"),
            fairness_strength=float(payload.get("fairness_strength", 0.25)),
            target_fairness=float(payload.get("target_fairness", 0.95)),
        )

    def with_policy(self, policy: str) -> "ExperimentConfig":
        return replace(self, policy=policy)

    def with_seed(self, seed: int) -> "ExperimentConfig":
        return replace(self, seed=seed)


def load_config(path: str | Path) -> ExperimentConfig:
    raw = json.loads(Path(path).read_text())
    return ExperimentConfig.from_dict(raw)
