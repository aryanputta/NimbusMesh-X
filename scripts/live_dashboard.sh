#!/usr/bin/env bash
set -euo pipefail

INTERVAL="${INTERVAL:-1}"
LOG_DIR="${LOG_DIR:-logs}"

render_frame() {
  clear
  echo "NimbusMesh-X Live Dashboard"
  echo "timestamp=$(date -Iseconds)"
  echo
  echo "--- GPU ---"
  if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi || true
  else
    echo "nvidia-smi not available"
  fi
  echo
  echo "--- Recent Scheduler Decisions ---"
  tail -n 10 "$LOG_DIR/scheduler_decisions.log" 2>/dev/null || echo "no scheduler_decisions.log yet"
  echo
  echo "--- Recent Latency Metrics ---"
  tail -n 10 "$LOG_DIR/latency_metrics.log" 2>/dev/null || echo "no latency_metrics.log yet"
  echo
  echo "--- Recent Cache Hits ---"
  tail -n 10 "$LOG_DIR/cache_hits.log" 2>/dev/null || echo "no cache_hits.log yet"
}

while true; do
  render_frame
  sleep "$INTERVAL"
done

