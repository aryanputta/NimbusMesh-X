from pathlib import Path

from nimbusmesh_x.config import load_config
from workload_gen.generator import WorkloadGenerator


ROOT = Path(__file__).resolve().parents[1]


def test_workload_generator_is_reproducible() -> None:
    config = load_config(ROOT / "configs" / "multi_cluster_long_context.json").workload
    first = WorkloadGenerator(config, seed=123).generate_requests()
    second = WorkloadGenerator(config, seed=123).generate_requests()
    assert [(item.request_id, item.arrival_ts, item.prefix_signature) for item in first] == [
        (item.request_id, item.arrival_ts, item.prefix_signature) for item in second
    ]

