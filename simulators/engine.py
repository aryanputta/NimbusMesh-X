from __future__ import annotations

from nimbusmesh_x.config import ExperimentConfig
from nimbusmesh_x.exporters import ResultCSVExporter
from nimbusmesh_x.logging_utils import StructuredDecisionLogger
from nimbusmesh_x.metrics import MetricsCollector
from nimbusmesh_x.structured_logs import StructuredLogFanout
from azure_sim.environment import AzureInfraSimulator
from control_plane.service import NimbusMeshControlPlane
from storage.postgres_store import PostgresExperimentStore
from storage.redis_store import RedisDecisionStore
from workload_gen.generator import WorkloadGenerator


class SimulationEngine:
    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config
        self.control_plane = NimbusMeshControlPlane(config)
        self.metrics = MetricsCollector()
        self.logger = StructuredDecisionLogger(config.decision_log_path)
        self.log_fanout = StructuredLogFanout()
        self.result_exporter = ResultCSVExporter()
        self.azure = AzureInfraSimulator()
        self.postgres_store = PostgresExperimentStore()
        self.redis_store = RedisDecisionStore()

    def run(self) -> dict[str, object]:
        generator = WorkloadGenerator(self.config.workload, self.config.seed)
        requests = generator.generate_requests()
        for request in requests:
            self.control_plane.refresh(request.arrival_ts)
            self.control_plane.note_submission(request)
            self.metrics.note_submission(request.tenant_id)
            self.azure.note_submission(request)
            result = self.control_plane.execute(request, request.arrival_ts)
            self.metrics.record(result)
            result_payload = result.to_dict()
            self.logger.emit(result_payload)
            self.log_fanout.emit_result(result)
            self.azure.record_result(result)
            self.redis_store.write_decision(result_payload)
            self.postgres_store.write_result(self.config.name, result)
        total_slots = sum(pool.parallel_slots for cluster in self.control_plane.clusters.values() for pool in cluster.pools.values())
        total_memory_gb = sum(pool.memory_gb for cluster in self.control_plane.clusters.values() for pool in cluster.pools.values())
        summary = self.metrics.summary(
            duration_s=self.config.workload.duration_s,
            policy_name=self.control_plane.policy.name,
            config_name=self.config.name,
            total_slots=total_slots,
            total_memory_gb=total_memory_gb,
        )
        summary["azure_summary"] = self.azure.summary()
        self.metrics.write_summary(self.config.metrics_output_path, summary)
        self.result_exporter.export_summary(summary)
        self.postgres_store.write_summary(self.config.name, self.control_plane.policy.name, summary)
        return summary
