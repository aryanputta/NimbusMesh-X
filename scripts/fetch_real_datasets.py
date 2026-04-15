#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_pipeline.fetchers import FETCH_REGISTRY


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch real-world datasets used by NimbusMesh-X.")
    parser.add_argument("--dataset", required=True, choices=sorted(FETCH_REGISTRY.keys()))
    parser.add_argument("--output-dir", default="data/raw")
    parser.add_argument("--sample-size", type=int, default=10_000)
    args = parser.parse_args()

    fetcher = FETCH_REGISTRY[args.dataset]
    if args.dataset in {"sharegpt", "lmsys"}:
        target = fetcher(args.output_dir, sample_size=args.sample_size)
    else:
        target = fetcher(args.output_dir)
    print(json.dumps({"dataset": args.dataset, "output": str(target)}, indent=2))


if __name__ == "__main__":
    main()

