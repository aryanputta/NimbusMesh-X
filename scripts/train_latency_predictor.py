#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.latency_predictor import LatencyPredictor, LatencyPredictorConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a lightweight latency predictor from normalized workload traces.")
    parser.add_argument("--input", default="data/workloads/sample_generic_trace.csv")
    parser.add_argument("--output", default="experiments/models/latency_predictor.pt")
    parser.add_argument("--epochs", type=int, default=20)
    args = parser.parse_args()
    predictor = LatencyPredictor(LatencyPredictorConfig(epochs=args.epochs))
    loss = predictor.train_from_csv(args.input)
    predictor.save(args.output)
    print(json.dumps({"output": args.output, "final_loss": loss}, indent=2))


if __name__ == "__main__":
    main()

