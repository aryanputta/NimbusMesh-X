from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import blake2b
from typing import Any

SLA_PRIORITY = {
    "realtime": 3,
    "interactive": 2,
    "best_effort": 1,
}

TOPOLOGY_TIER_SCORE = {
    "nvlink-mesh": 1.0,
    "nvlink-ring": 0.92,
    "pcie-fabric": 0.72,
    "ethernet": 0.55,
    "cpu-fallback": 0.2,
}

MODEL_SCALE_HINTS = {
    "llama-3-70b": 1.35,
    "mixtral-8x7b": 1.2,
    "mistral-7b": 0.75,
    "llama-3-8b": 0.6,
    "deepseek-v2-lite": 0.95,
    "maia-sim": 0.8,
}


def stable_prefix_signature(tenant_id: str, model_id: str, session_id: str | None, salt: str) -> str:
    base = f"{tenant_id}:{model_id}:{session_id or 'anon'}:{salt}"
    return blake2b(base.encode("utf-8"), digest_size=8).hexdigest()


def normalize_sla_class(sla_class: str) -> str:
    if sla_class not in SLA_PRIORITY:
        raise ValueError(f"Unsupported SLA class: {sla_class}")
    return sla_class


def model_scale(model_id: str) -> float:
    return MODEL_SCALE_HINTS.get(model_id, 1.0)


def estimate_request_memory_gb(
    prompt_tokens: int,
    generation_tokens: int,
    model_id: str,
    cache_saved_tokens: int = 0,
) -> float:
    effective_tokens = max(1, prompt_tokens + generation_tokens - cache_saved_tokens)
    return (effective_tokens / 2048.0) * 1.15 * model_scale(model_id)


@dataclass(frozen=True)
class InferenceRequest:
    request_id: str
    tenant_id: str
    model_id: str
    prompt_tokens: int
    generation_tokens: int
    arrival_ts: float
    sla_class: str = "interactive"
    session_id: str | None = None
    prefix_signature: str | None = None
    max_latency_ms: float = 1800.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalize_sla_class(self.sla_class)
        if self.prompt_tokens <= 0 or self.generation_tokens <= 0:
            raise ValueError("Token counts must be positive.")
        if self.arrival_ts < 0:
            raise ValueError("arrival_ts must be non-negative.")
        if self.max_latency_ms <= 0:
            raise ValueError("max_latency_ms must be positive.")
        if self.prefix_signature is None:
            derived = stable_prefix_signature(
                self.tenant_id,
                self.model_id,
                self.session_id,
                salt=f"{self.prompt_tokens // 128}:{self.generation_tokens // 64}",
            )
            object.__setattr__(self, "prefix_signature", derived)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.generation_tokens


@dataclass
class PoolRuntime:
    cluster_id: str
    zone: str
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
    congestion_score: float = 0.0
    slot_available_at: list[float] = field(default_factory=list)
    active_memory_gb: float = 0.0
    cache_reserved_gb: float = 0.0
    decision_count: int = 0
    completed_count: int = 0
    inflight_memory: list[tuple[float, float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.slot_available_at:
            self.slot_available_at = [0.0 for _ in range(self.parallel_slots)]

    def refresh(self, now: float) -> None:
        still_inflight: list[tuple[float, float]] = []
        active_memory = 0.0
        for finish_ts, memory_gb in self.inflight_memory:
            if finish_ts > now:
                still_inflight.append((finish_ts, memory_gb))
                active_memory += memory_gb
        self.inflight_memory = still_inflight
        self.active_memory_gb = active_memory

    def inflight_count(self, now: float) -> int:
        return sum(1 for ts in self.slot_available_at if ts > now)

    def queue_delay_ms(self, now: float) -> float:
        earliest = min(self.slot_available_at)
        return max(0.0, earliest - now) * 1000.0

    def memory_headroom_gb(self) -> float:
        return max(0.0, self.memory_gb - self.active_memory_gb - self.cache_reserved_gb)


@dataclass
class ClusterRuntime:
    cluster_id: str
    zone: str
    ingress_cost: float
    network_costs: dict[str, float]
    base_congestion: float
    failure_windows: list[tuple[float, float]] = field(default_factory=list)
    congestion_windows: list[tuple[float, float, float]] = field(default_factory=list)
    pools: dict[str, PoolRuntime] = field(default_factory=dict)

    def effective_congestion(self, now: float) -> float:
        congestion = self.base_congestion
        for start, end, multiplier in self.congestion_windows:
            if start <= now <= end:
                congestion *= multiplier
        return congestion

    def unavailable(self, now: float) -> bool:
        return any(start <= now <= end for start, end in self.failure_windows)


@dataclass(frozen=True)
class TopologyNode:
    node_id: str
    kind: str
    cluster_id: str
    zone: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TopologyLink:
    source: str
    target: str
    bandwidth_gbps: float
    latency_us: float
    cost: float


@dataclass(frozen=True)
class CandidatePlacement:
    cluster_id: str
    pool_id: str
    backend_name: str
    accelerator_type: str
    queue_delay_ms: float
    projected_prefill_ms: float
    projected_decode_ms: float
    expected_cache_hit_ratio: float
    expected_cache_saved_tokens: int
    topology_affinity: float
    network_cost: float
    congestion_score: float
    memory_headroom_gb: float
    accelerator_cost_per_1m_tokens: float
    fairness_penalty: float
    premium: bool
    available: bool
    rejection_reason: str | None = None
    score_breakdown: dict[str, float] = field(default_factory=dict)

    @property
    def estimated_total_latency_ms(self) -> float:
        return self.queue_delay_ms + self.projected_prefill_ms + self.projected_decode_ms


@dataclass(frozen=True)
class RoutingDecision:
    request_id: str
    policy_name: str
    cluster_id: str
    pool_id: str
    backend_name: str
    estimated_latency_ms: float
    estimated_queue_delay_ms: float
    estimated_cache_hit_ratio: float
    topology_affinity: float
    network_cost: float
    accelerator_cost_per_1m_tokens: float
    fairness_penalty: float
    score_breakdown: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class RequestResult:
    request: InferenceRequest
    decision: RoutingDecision
    admitted: bool
    actual_start_ts: float
    completion_ts: float
    queue_delay_ms: float
    prefill_latency_ms: float
    decode_latency_ms: float
    total_latency_ms: float
    cache_hit_ratio: float
    cache_saved_tokens: int
    memory_gb: float
    cost_usd: float
    energy_proxy: float
    network_cost: float
    sla_met: bool
    rejection_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["request"]["metadata"] = dict(self.request.metadata)
        return payload


@dataclass
class TenantStats:
    submitted: int = 0
    completed: int = 0
    total_latency_ms: float = 0.0
    sla_misses: int = 0

