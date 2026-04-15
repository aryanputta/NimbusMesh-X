from __future__ import annotations

import os
from pathlib import Path

try:  # pragma: no cover - optional dependency path
    import numpy as np
    import pycuda.autoinit  # noqa: F401
    import pycuda.driver as cuda
    from pycuda.compiler import SourceModule
except Exception:  # pragma: no cover - optional dependency path
    np = None
    cuda = None
    SourceModule = None


class CudaScoringEngine:
    def __init__(self, kernel_dir: str | Path = "cuda_kernels") -> None:
        self.kernel_dir = Path(kernel_dir)
        self.enabled = os.getenv("NIMBUS_USE_CUDA", "0") == "1"
        self.available = bool(self.enabled and np is not None and SourceModule is not None)
        self.modules: dict[str, object] = {}
        if self.available:
            self._compile_modules()

    def _compile_modules(self) -> None:  # pragma: no cover - hardware dependent
        for file_name in [
            "cache_score_kernel.cu",
            "topology_cost_kernel.cu",
            "load_balance_kernel.cu",
        ]:
            source = (self.kernel_dir / file_name).read_text()
            self.modules[file_name] = SourceModule(source)

    def enrich_candidates(self, candidates) -> None:
        cache_hits = [candidate.expected_cache_hit_ratio for candidate in candidates]
        saved_tokens = [float(candidate.expected_cache_saved_tokens) for candidate in candidates]
        network_costs = [candidate.network_cost for candidate in candidates]
        topology_affinity = [candidate.topology_affinity for candidate in candidates]
        queue_delay = [candidate.queue_delay_ms for candidate in candidates]
        congestion = [candidate.congestion_score for candidate in candidates]
        memory_headroom = [candidate.memory_headroom_gb for candidate in candidates]

        if self.available:
            cache_bonus = self._gpu_cache_bonus(cache_hits, saved_tokens)
            topology_penalty = self._gpu_topology_penalty(topology_affinity, network_costs)
            load_penalty = self._gpu_load_penalty(queue_delay, congestion, memory_headroom)
        else:
            cache_bonus = [
                round(hit * (1.0 + (saved / 8192.0)), 4) for hit, saved in zip(cache_hits, saved_tokens)
            ]
            topology_penalty = [
                round(max(0.0, net - affinity), 4) for affinity, net in zip(topology_affinity, network_costs)
            ]
            load_penalty = [
                round((queue / 1000.0) + cong + max(0.0, 1.0 - (mem / 64.0)), 4)
                for queue, cong, mem in zip(queue_delay, congestion, memory_headroom)
            ]

        for candidate, cache_value, topo_value, load_value in zip(
            candidates, cache_bonus, topology_penalty, load_penalty
        ):
            candidate.score_breakdown["cuda_cache_bonus"] = cache_value
            candidate.score_breakdown["cuda_topology_penalty"] = topo_value
            candidate.score_breakdown["cuda_load_penalty"] = load_value

    def _gpu_cache_bonus(self, cache_hits, saved_tokens):  # pragma: no cover - hardware dependent
        module = self.modules["cache_score_kernel.cu"]
        func = module.get_function("cache_score_kernel")
        count = len(cache_hits)
        hits = np.array(cache_hits, dtype=np.float32)
        saved = np.array(saved_tokens, dtype=np.float32)
        out = np.zeros(count, dtype=np.float32)
        func(
            cuda.In(hits),
            cuda.In(saved),
            cuda.Out(out),
            np.int32(count),
            block=(256, 1, 1),
            grid=((count + 255) // 256, 1),
        )
        return out.tolist()

    def _gpu_topology_penalty(self, topology_affinity, network_costs):  # pragma: no cover - hardware dependent
        module = self.modules["topology_cost_kernel.cu"]
        func = module.get_function("topology_cost_kernel")
        count = len(topology_affinity)
        affinity = np.array(topology_affinity, dtype=np.float32)
        network = np.array(network_costs, dtype=np.float32)
        out = np.zeros(count, dtype=np.float32)
        func(
            cuda.In(affinity),
            cuda.In(network),
            cuda.Out(out),
            np.int32(count),
            block=(256, 1, 1),
            grid=((count + 255) // 256, 1),
        )
        return out.tolist()

    def _gpu_load_penalty(self, queue_delay, congestion, memory_headroom):  # pragma: no cover - hardware dependent
        module = self.modules["load_balance_kernel.cu"]
        func = module.get_function("load_balance_kernel")
        count = len(queue_delay)
        queue = np.array(queue_delay, dtype=np.float32)
        cong = np.array(congestion, dtype=np.float32)
        memory = np.array(memory_headroom, dtype=np.float32)
        out = np.zeros(count, dtype=np.float32)
        func(
            cuda.In(queue),
            cuda.In(cong),
            cuda.In(memory),
            cuda.Out(out),
            np.int32(count),
            block=(256, 1, 1),
            grid=((count + 255) // 256, 1),
        )
        return out.tolist()

