from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


BANDWIDTH_TIERS = {
    "X": 0.0,
    "NV1": 1.0,
    "NV2": 1.2,
    "NV4": 1.4,
    "NV8": 1.8,
    "NV12": 2.0,
    "NV16": 2.2,
    "NV18": 2.3,
    "NVSW": 2.5,
    "PIX": 0.65,
    "PXB": 0.45,
    "PHB": 0.35,
    "NODE": 0.28,
    "SYS": 0.18,
    "SOC": 0.12,
}

LATENCY_WEIGHTS = {
    "X": 0.0,
    "NV1": 0.15,
    "NV2": 0.12,
    "NV4": 0.1,
    "NV8": 0.08,
    "NV12": 0.07,
    "NV16": 0.06,
    "NV18": 0.05,
    "NVSW": 0.04,
    "PIX": 0.4,
    "PXB": 0.55,
    "PHB": 0.72,
    "NODE": 0.88,
    "SYS": 1.0,
    "SOC": 1.1,
}


@dataclass
class GpuTopologySnapshot:
    devices: list[str]
    relations: dict[str, dict[str, str]]
    adjacency_matrix: list[list[float]]
    latency_weights: list[list[float]]
    bandwidth_tiers: list[list[float]]

    @classmethod
    def from_text(cls, text: str) -> "GpuTopologySnapshot":
        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        header_line = next(line for line in lines if "GPU" in line and "CPU Affinity" in line)
        devices = re.findall(r"(GPU\d+|NIC\d+)", header_line)
        relations: dict[str, dict[str, str]] = {}
        for line in lines:
            if line.startswith("Legend"):
                break
            if not re.match(r"^(GPU\d+|NIC\d+)\s", line):
                continue
            parts = line.split()
            source = parts[0]
            edges = parts[1 : 1 + len(devices)]
            if source.startswith("GPU"):
                relations[source] = {target: edge for target, edge in zip(devices, edges)}
        matrix = []
        latency = []
        bandwidth = []
        gpu_devices = [device for device in devices if device.startswith("GPU")]
        for source in gpu_devices:
            matrix_row = []
            latency_row = []
            bandwidth_row = []
            for target in gpu_devices:
                relation = relations[source][target]
                bw = BANDWIDTH_TIERS.get(relation, 0.1)
                lat = LATENCY_WEIGHTS.get(relation, 1.2)
                cost = 0.0 if relation == "X" else max(0.01, 1.2 - bw + lat)
                matrix_row.append(round(cost, 4))
                latency_row.append(lat)
                bandwidth_row.append(bw)
            matrix.append(matrix_row)
            latency.append(latency_row)
            bandwidth.append(bandwidth_row)
        return cls(
            devices=gpu_devices,
            relations={source: {target: relation for target, relation in mapping.items() if target in gpu_devices} for source, mapping in relations.items() if source in gpu_devices},
            adjacency_matrix=matrix,
            latency_weights=latency,
            bandwidth_tiers=bandwidth,
        )

    @classmethod
    def from_file(cls, path: str | Path) -> "GpuTopologySnapshot":
        return cls.from_text(Path(path).read_text())

    def overall_affinity(self) -> float:
        values = []
        for row in self.bandwidth_tiers:
            values.extend(value for value in row if value > 0.0)
        if not values:
            return 0.0
        return round(sum(values) / len(values) / max(BANDWIDTH_TIERS.values()), 4)

    def average_cost(self) -> float:
        values = []
        for row in self.adjacency_matrix:
            values.extend(value for value in row if value > 0.0)
        if not values:
            return 1.0
        return round(sum(values) / len(values), 4)

    def to_dict(self) -> dict[str, object]:
        return {
            "devices": self.devices,
            "relations": self.relations,
            "adjacency_matrix": self.adjacency_matrix,
            "latency_weights": self.latency_weights,
            "bandwidth_tiers": self.bandwidth_tiers,
            "overall_affinity": self.overall_affinity(),
            "average_cost": self.average_cost(),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse nvidia-smi topo -m output into structured matrices.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    parsed = GpuTopologySnapshot.from_file(args.input)
    payload = json.dumps(parsed.to_dict(), indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(payload)
    else:
        print(payload)


if __name__ == "__main__":
    main()

