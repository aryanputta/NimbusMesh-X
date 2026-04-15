from pathlib import Path

from data_pipeline.normalizers import normalize_generic_workload_csv
from data_pipeline.utils import write_normalized_rows
from nimbusmesh_x.config import WorkloadConfig
from scheduler_core.cpp_bridge import CppSchedulerCore
from workload_gen.generator import WorkloadGenerator


ROOT = Path(__file__).resolve().parents[1]


def test_generic_trace_normalizer_outputs_rows(tmp_path: Path) -> None:
    rows = normalize_generic_workload_csv(ROOT / "data" / "raw" / "sample_generic_trace.csv")
    assert len(rows) == 4
    out = tmp_path / "normalized.csv"
    write_normalized_rows(out, rows)
    assert out.exists()


def test_workload_generator_trace_mode() -> None:
    cfg = WorkloadConfig.from_dict(
        {
            "request_count": 10,
            "duration_s": 10,
            "arrival_pattern": "poisson",
            "trace_path": str(ROOT / "data" / "raw" / "sample_generic_trace.csv"),
            "trace_replay_speed": 1.0,
            "prompt_tokens": {"distribution": "uniform", "min": 1, "max": 2},
            "generation_tokens": {"distribution": "uniform", "min": 1, "max": 2},
            "tenant_weights": {"tenant-a": 1.0},
            "model_mix": {"llama-3-8b": 1.0},
            "sla_mix": {"interactive": 1.0},
        }
    )
    requests = WorkloadGenerator(cfg, seed=7).generate_requests()
    assert len(requests) == 4
    assert requests[0].request_id == "req-000001"
    assert requests[1].arrival_ts >= requests[0].arrival_ts


def test_cpp_core_bridge_fallback_when_library_missing(monkeypatch) -> None:
    monkeypatch.setenv("NIMBUS_USE_CPP_CORE", "1")
    bridge = CppSchedulerCore(library_path="/tmp/does-not-exist.so")
    assert bridge.available is False

