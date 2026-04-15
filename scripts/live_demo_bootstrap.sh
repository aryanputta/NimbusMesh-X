#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[NimbusMesh-X] Live demo bootstrap started"

if [[ ! -d ".venv" ]]; then
  echo "[setup] Creating virtual environment"
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "[setup] Installing dependencies"
pip install -q -e ".[dev,data,runtime,viz]" || pip install -q -e ".[dev]"

echo "[demo] Normalizing sample workloads"
python scripts/normalize_workloads.py --config configs/dataset_pipeline.yaml

echo "[demo] Running trace replay benchmark"
python scripts/run_simulation.py --config configs/trace_sharegpt_replay.json --policy multi_objective

echo "[demo] Running baseline benchmark suite (single seed)"
python scripts/run_benchmarks.py \
  --config configs/multi_cluster_long_context.json \
  --policies least_queue multi_objective contextual_bandit \
  --seeds 19

echo "[demo] Rendering plot"
python scripts/plot_results.py || true

echo
echo "[NimbusMesh-X] Live demo artifacts ready:"
echo "  - results/*.csv"
echo "  - results/latency_comparison.png"
echo "  - logs/scheduler.log"
echo "  - logs/topology.log"
echo "  - logs/cache.log"
echo
echo "Start API:"
echo "  python scripts/run_api.py"
echo
echo "Start terminal dashboard in a second terminal:"
echo "  bash scripts/live_dashboard.sh"

