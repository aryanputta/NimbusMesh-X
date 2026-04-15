#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nimbusmesh_x.config import load_config
from simulators.engine import SimulationEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a NimbusMesh-X simulation.")
    parser.add_argument("--config", default="configs/multi_cluster_long_context.json")
    parser.add_argument("--policy", default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    if args.policy:
        config = config.with_policy(args.policy)
    report = SimulationEngine(config).run()
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
