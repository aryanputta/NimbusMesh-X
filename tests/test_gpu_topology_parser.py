from pathlib import Path

from topology.gpu_topology_parser import GpuTopologySnapshot


ROOT = Path(__file__).resolve().parents[1]


def test_gpu_topology_parser_extracts_matrix() -> None:
    parsed = GpuTopologySnapshot.from_file(ROOT / "topology" / "sample_nvidia_smi_topo.txt")
    assert parsed.devices == ["GPU0", "GPU1", "GPU2", "GPU3"]
    assert parsed.relations["GPU0"]["GPU1"] == "NV4"
    assert parsed.overall_affinity() > 0.0

