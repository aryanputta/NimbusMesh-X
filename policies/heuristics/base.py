from __future__ import annotations

from abc import ABC, abstractmethod

from nimbusmesh_x.types import CandidatePlacement, InferenceRequest, RequestResult


class RoutingPolicy(ABC):
    name: str

    @abstractmethod
    def choose(self, request: InferenceRequest, candidates: list[CandidatePlacement]) -> CandidatePlacement:
        raise NotImplementedError

    def observe_result(self, result: RequestResult) -> None:
        return None

