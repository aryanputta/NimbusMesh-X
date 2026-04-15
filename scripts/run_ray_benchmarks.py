#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulators.ray_engine import run_ray_sweep


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NimbusMesh-X policy sweeps on Ray.")
    parser.add_argument("--config", default="configs/multi_cluster_long_context.json")
    parser.add_argument(
        "--policies",
        nargs="+",
        default=["round_robin", "least_queue", "topology_greedy", "cache_aware", "multi_objective", "contextual_bandit"],
    )
    parser.add_argument("--seeds", nargs="+", type=int, default=[7, 11, 19])
    parser.add_argument("--ray-address", default=None)
    parser.add_argument("--output", default="experiments/results/ray_benchmark.json")
    args = parser.parse_args()

    reports = run_ray_sweep(
        config_path=args.config,
        policies=args.policies,
        seeds=args.seeds,
        address=args.ray_address,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(reports, indent=2, sort_keys=True))
    print(json.dumps({"output": str(output), "reports": len(reports)}, indent=2))


if __name__ == "__main__":
    main()

