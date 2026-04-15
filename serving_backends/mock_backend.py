from __future__ import annotations

from typing import Any

from nimbusmesh_x.types import InferenceRequest, PoolRuntime
from serving_backends.base import BackendAdapter


class MockBackend(BackendAdapter):
    def __init__(self) -> None:
        super().__init__(name="mock", latency_factor=1.0)

    def estimate_latency_ms(
        self,
        request: InferenceRequest,
        pool: PoolRuntime,
        cache_hit_ratio: float,
        topology_affinity: float,
        network_cost: float,
        congestion_score: float,
    ) -> tuple[float, float]:
        effective_prompt = max(1.0, request.prompt_tokens * (1.0 - (cache_hit_ratio * 0.8)))
        prefill_ms = (effective_prompt / max(pool.prefill_tps, 1.0)) * 1000.0
        decode_ms = (request.generation_tokens / max(pool.decode_tps, 1.0)) * 1000.0
        topology_multiplier = max(0.72, 1.10 - (topology_affinity * 0.22))
        congestion_multiplier = 1.0 + (congestion_score * 0.35)
        network_penalty_ms = network_cost * (5.0 + request.prompt_tokens / 4096.0)
        return (
            round(prefill_ms * topology_multiplier * congestion_multiplier + network_penalty_ms, 4),
            round(decode_ms * congestion_multiplier, 4),
        )

    def invoke(self, endpoint: str, payload: dict[str, Any], timeout_s: float = 30.0) -> dict[str, Any]:
        return {"backend": self.name, "endpoint": endpoint, "payload": payload, "timeout_s": timeout_s}

