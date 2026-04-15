from __future__ import annotations

from typing import Any

from nimbusmesh_x.types import InferenceRequest, PoolRuntime
from serving_backends.base import BackendAdapter, HTTPBackendMixin


class TritonBackend(HTTPBackendMixin, BackendAdapter):
    def __init__(self) -> None:
        super().__init__(name="triton", latency_factor=0.9)

    def estimate_latency_ms(
        self,
        request: InferenceRequest,
        pool: PoolRuntime,
        cache_hit_ratio: float,
        topology_affinity: float,
        network_cost: float,
        congestion_score: float,
    ) -> tuple[float, float]:
        prompt = max(1.0, request.prompt_tokens * (1.0 - (cache_hit_ratio * 0.75)))
        prefill_ms = (prompt / max(pool.prefill_tps * 1.12, 1.0)) * 1000.0
        decode_ms = (request.generation_tokens / max(pool.decode_tps * 1.03, 1.0)) * 1000.0
        multiplier = (1.0 + congestion_score * 0.24) * max(0.70, 1.05 - topology_affinity * 0.2)
        return (
            round(prefill_ms * multiplier + network_cost * 3.5, 4),
            round(decode_ms * multiplier, 4),
        )

    def invoke(self, endpoint: str, payload: dict[str, Any], timeout_s: float = 30.0) -> dict[str, Any]:
        return self.post_json(endpoint, payload, timeout_s=timeout_s)

