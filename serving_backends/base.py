from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from nimbusmesh_x.types import InferenceRequest, PoolRuntime


class BackendAdapter(ABC):
    def __init__(self, name: str, latency_factor: float = 1.0) -> None:
        self.name = name
        self.latency_factor = latency_factor

    @abstractmethod
    def estimate_latency_ms(
        self,
        request: InferenceRequest,
        pool: PoolRuntime,
        cache_hit_ratio: float,
        topology_affinity: float,
        network_cost: float,
        congestion_score: float,
    ) -> tuple[float, float]:
        raise NotImplementedError

    @abstractmethod
    def invoke(self, endpoint: str, payload: dict[str, Any], timeout_s: float = 30.0) -> dict[str, Any]:
        raise NotImplementedError


class HTTPBackendMixin:
    def post_json(self, endpoint: str, payload: dict[str, Any], timeout_s: float = 30.0) -> dict[str, Any]:
        with httpx.Client(timeout=timeout_s) as client:
            response = client.post(endpoint, json=payload)
            response.raise_for_status()
            return response.json()

