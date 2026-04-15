from __future__ import annotations

import os

from nimbusmesh_x.types import CandidatePlacement, InferenceRequest
from grpc_layer.stub_loader import load_stubs

try:  # pragma: no cover - optional dependency path
    import grpc
except Exception:  # pragma: no cover - optional dependency path
    grpc = None


class GrpcSchedulerClient:
    def __init__(self, target: str | None = None) -> None:
        self.target = target or os.getenv("NIMBUS_GRPC_TARGET", "127.0.0.1:50051")
        self.enabled = os.getenv("NIMBUS_USE_GRPC_ROUTER", "0") == "1"
        self.available = False
        self.scheduler_pb2 = None
        self.stub = None
        if self.enabled and grpc is not None:
            self._init_client()

    def _init_client(self) -> None:
        try:
            scheduler_pb2, scheduler_pb2_grpc = load_stubs()
            channel = grpc.insecure_channel(self.target)
            self.stub = scheduler_pb2_grpc.SchedulerServiceStub(channel)
            self.scheduler_pb2 = scheduler_pb2
            self.available = True
        except Exception:
            self.available = False

    def choose(self, request: InferenceRequest, candidates: list[CandidatePlacement]) -> int | None:
        if not self.available or not self.stub or not self.scheduler_pb2:
            return None
        payload_candidates = []
        for candidate in candidates:
            payload_candidates.append(
                self.scheduler_pb2.Candidate(
                    cluster_id=candidate.cluster_id,
                    pool_id=candidate.pool_id,
                    estimated_latency_ms=candidate.estimated_total_latency_ms,
                    queue_delay_ms=candidate.queue_delay_ms,
                    cache_hit_ratio=candidate.expected_cache_hit_ratio,
                    topology_affinity=candidate.topology_affinity,
                    network_cost=candidate.network_cost,
                    accelerator_cost_per_1m_tokens=candidate.accelerator_cost_per_1m_tokens,
                    fairness_penalty=candidate.fairness_penalty,
                    available=candidate.available,
                )
            )
        response = self.stub.ChoosePlacement(
            self.scheduler_pb2.PlacementRequest(
                request_id=request.request_id,
                tenant_id=request.tenant_id,
                model_id=request.model_id,
                sla_class=request.sla_class,
                policy_name="grpc",
                candidates=payload_candidates,
            ),
            timeout=0.05,
        )
        if response.chosen_index < 0 or response.chosen_index >= len(candidates):
            return None
        return int(response.chosen_index)
