from __future__ import annotations

import ctypes
import os
from pathlib import Path

from nimbusmesh_x.types import CandidatePlacement, InferenceRequest, SLA_PRIORITY


class CppSchedulerCore:
    def __init__(self, library_path: str | None = None) -> None:
        self.library_path = library_path or os.getenv("NIMBUS_CPP_CORE_PATH", "")
        if not self.library_path:
            root = Path(__file__).resolve().parents[1]
            default_candidates = [
                root / "scheduler_core_cpp" / "build" / "libscheduler_core.dylib",
                root / "scheduler_core_cpp" / "build" / "libscheduler_core.so",
            ]
            for candidate in default_candidates:
                if candidate.exists():
                    self.library_path = str(candidate)
                    break
        self.enabled = os.getenv("NIMBUS_USE_CPP_CORE", "0") == "1"
        self.available = self.enabled and bool(self.library_path) and Path(self.library_path).exists()
        self.lib = None
        if self.available:
            self.lib = ctypes.CDLL(self.library_path)
            self.lib.choose_candidate.argtypes = [
                ctypes.POINTER(ctypes.c_double),
                ctypes.POINTER(ctypes.c_double),
                ctypes.POINTER(ctypes.c_double),
                ctypes.POINTER(ctypes.c_double),
                ctypes.POINTER(ctypes.c_double),
                ctypes.POINTER(ctypes.c_double),
                ctypes.POINTER(ctypes.c_double),
                ctypes.POINTER(ctypes.c_int),
                ctypes.c_int,
                ctypes.c_int,
            ]
            self.lib.choose_candidate.restype = ctypes.c_int

    def choose(self, request: InferenceRequest, candidates: list[CandidatePlacement]) -> int | None:
        if not self.available or not self.lib or not candidates:
            return None
        count = len(candidates)
        latency = (ctypes.c_double * count)(*[item.estimated_total_latency_ms for item in candidates])
        queue_delay = (ctypes.c_double * count)(*[item.queue_delay_ms for item in candidates])
        cache_hit = (ctypes.c_double * count)(*[item.expected_cache_hit_ratio for item in candidates])
        topology_affinity = (ctypes.c_double * count)(*[item.topology_affinity for item in candidates])
        network_cost = (ctypes.c_double * count)(*[item.network_cost for item in candidates])
        accel_cost = (ctypes.c_double * count)(*[item.accelerator_cost_per_1m_tokens for item in candidates])
        fairness_penalty = (ctypes.c_double * count)(*[item.fairness_penalty for item in candidates])
        available = (ctypes.c_int * count)(*[1 if item.available else 0 for item in candidates])
        sla_priority = SLA_PRIORITY.get(request.sla_class, 2)
        chosen = self.lib.choose_candidate(
            latency,
            queue_delay,
            cache_hit,
            topology_affinity,
            network_cost,
            accel_cost,
            fairness_penalty,
            available,
            count,
            sla_priority,
        )
        if chosen < 0 or chosen >= count:
            return None
        return int(chosen)

