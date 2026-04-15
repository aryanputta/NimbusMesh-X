from __future__ import annotations

from concurrent import futures

import grpc

from grpc_layer.stub_loader import load_stubs


class SchedulerServicer:
    def __init__(self) -> None:
        self.scheduler_pb2, self.scheduler_pb2_grpc = load_stubs()

    def ChoosePlacement(self, request, context):  # noqa: N802 - grpc naming
        if not request.candidates:
            return self.scheduler_pb2.PlacementResponse(chosen_index=-1, reason="no-candidates")
        sla = request.sla_class
        latency_weight = 1.5 if sla == "realtime" else 1.1 if sla == "interactive" else 0.8
        cost_weight = 0.2 if sla == "realtime" else 0.6
        best_index = 0
        best_score = float("inf")
        for index, candidate in enumerate(request.candidates):
            if not candidate.available:
                continue
            score = (
                (candidate.estimated_latency_ms * latency_weight)
                + (candidate.queue_delay_ms * 0.1)
                + (candidate.network_cost * 18.0)
                + (candidate.accelerator_cost_per_1m_tokens * cost_weight)
                + (candidate.fairness_penalty * 110.0)
                - (candidate.cache_hit_ratio * 450.0)
                - (candidate.topology_affinity * 85.0)
            )
            if score < best_score:
                best_score = score
                best_index = index
        return self.scheduler_pb2.PlacementResponse(chosen_index=best_index, reason="grpc-score")


def serve(host: str = "0.0.0.0", port: int = 50051) -> None:
    scheduler_pb2, scheduler_pb2_grpc = load_stubs()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=16))
    servicer = SchedulerServicer()
    scheduler_pb2_grpc.add_SchedulerServiceServicer_to_server(servicer, server)
    server.add_insecure_port(f"{host}:{port}")
    server.start()
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:  # pragma: no cover - operational path
        server.stop(0)
