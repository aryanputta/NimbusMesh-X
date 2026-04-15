from __future__ import annotations

import json
from pathlib import Path

from nimbusmesh_x.config import ExperimentConfig, load_config
from simulators.engine import SimulationEngine
from simulators.ray_engine import run_ray_sweep


class BenchmarkHarness:
    def __init__(self, config: ExperimentConfig, output_dir: str = "experiments/results", config_path: str | None = None) -> None:
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = config_path

    def run(self, policies: list[str], seeds: list[int]) -> list[dict[str, object]]:
        reports: list[dict[str, object]] = []
        for seed in seeds:
            for policy in policies:
                config = self.config.with_policy(policy).with_seed(seed)
                engine = SimulationEngine(config)
                report = engine.run()
                report["seed"] = seed
                reports.append(report)
        self._write_reports(reports)
        return reports

    def run_distributed(self, policies: list[str], seeds: list[int], ray_address: str | None = None) -> list[dict[str, object]]:
        if self.config_path is None:
            # Fallback to local execution if the config was created in-memory.
            return self.run(policies=policies, seeds=seeds)
        reports = run_ray_sweep(config_path=self.config_path, policies=policies, seeds=seeds, address=ray_address)
        self._write_reports(reports)
        return reports

    def _write_reports(self, reports: list[dict[str, object]]) -> None:
        target = self.output_dir / f"{self.config.name}-benchmark.json"
        target.write_text(json.dumps(reports, indent=2, sort_keys=True))


def run_benchmark_suite(config_path: str, policies: list[str], seeds: list[int]) -> list[dict[str, object]]:
    config = load_config(config_path)
    harness = BenchmarkHarness(config, config_path=config_path)
    return harness.run(policies=policies, seeds=seeds)
