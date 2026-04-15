#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[1/4] Normalizing workload datasets"
python3 scripts/normalize_workloads.py --config configs/dataset_pipeline.yaml

echo "[2/4] Running baseline benchmark suite"
python3 scripts/run_benchmarks.py --config configs/multi_cluster_long_context.json

echo "[3/4] Running trace replay benchmark"
python3 scripts/run_simulation.py --config configs/trace_sharegpt_replay.json --policy multi_objective

echo "[4/4] Rendering latency plot"
python3 scripts/plot_results.py || true

echo "Pipeline completed. Inspect results/ and logs/."

