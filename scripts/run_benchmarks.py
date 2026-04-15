#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.harness import BenchmarkHarness
from nimbusmesh_x.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NimbusMesh-X benchmark suite.")
    parser.add_argument("--config", default="configs/multi_cluster_long_context.json")
    parser.add_argument(
        "--policies",
        nargs="+",
        default=["round_robin", "least_queue", "topology_greedy", "cache_aware", "multi_objective", "contextual_bandit"],
    )
    parser.add_argument("--seeds", nargs="+", type=int, default=[7, 11, 19])
    parser.add_argument("--distributed", action="store_true")
    parser.add_argument("--ray-address", default=None)
    args = parser.parse_args()
    config = load_config(args.config)
    harness = BenchmarkHarness(config, config_path=args.config)
    if args.distributed:
        reports = harness.run_distributed(args.policies, args.seeds, ray_address=args.ray_address)
    else:
        reports = harness.run(args.policies, args.seeds)
    print(json.dumps(reports, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
