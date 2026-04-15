from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from nimbusmesh_x.config import load_config
from simulators.engine import SimulationEngine

try:  # pragma: no cover - optional dependency path
    import ray
except Exception:  # pragma: no cover - optional dependency path
    ray = None


def _run_single(config_path: str, policy: str, seed: int) -> dict[str, Any]:
    config = load_config(config_path).with_policy(policy).with_seed(seed)
    return SimulationEngine(config).run() | {"seed": seed, "policy_name": policy}


def run_ray_sweep(
    config_path: str,
    policies: list[str],
    seeds: list[int],
    address: str | None = None,
) -> list[dict[str, Any]]:
    if ray is None:
        reports = []
        for policy in policies:
            for seed in seeds:
                reports.append(_run_single(config_path, policy, seed))
        return reports

    runtime_address = address or os.getenv("NIMBUS_RAY_ADDRESS")
    ray.init(address=runtime_address, ignore_reinit_error=True, log_to_driver=False)

    @ray.remote
    def remote_run(config_path: str, policy: str, seed: int) -> dict[str, Any]:
        return _run_single(config_path, policy, seed)

    futures = []
    for policy in policies:
        for seed in seeds:
            futures.append(remote_run.remote(config_path, policy, seed))
    reports = ray.get(futures)
    reports.sort(key=lambda item: (item["policy_name"], item["seed"]))
    return reports

