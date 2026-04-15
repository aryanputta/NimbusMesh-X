#!/usr/bin/env bash
set -euo pipefail

REPORT_DIR="${REPORT_DIR:-profiling/reports}"
PROFILE_TARGET="${PROFILE_TARGET:-python scripts/run_simulation.py --config configs/multi_cluster_long_context.json}"
mkdir -p "$REPORT_DIR"

if command -v nsys >/dev/null 2>&1; then
  nsys profile -o "$REPORT_DIR/nsys_report" bash -lc "$PROFILE_TARGET"
else
  echo "nsys not found; skipping Nsight Systems profile"
fi

if command -v ncu >/dev/null 2>&1; then
  ncu --set full --target-processes all --export "$REPORT_DIR/ncu_report" bash -lc "$PROFILE_TARGET" || true
else
  echo "ncu not found; skipping Nsight Compute profile"
fi

