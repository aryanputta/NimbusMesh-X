#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="${LOG_DIR:-logs}"
mkdir -p "$LOG_DIR"

MODE="${1:-}"
shift || true

timestamp() {
  date -Iseconds
}

append_log() {
  printf '%s\n' "$1" >>"$LOG_DIR/failure_events.log"
}

case "$MODE" in
  gpu-failure)
    CLUSTER="${1:-unknown-cluster}"
    POOL="${2:-unknown-pool}"
    DURATION="${3:-30}"
    append_log "{\"timestamp\":\"$(timestamp)\",\"event\":\"gpu_failure\",\"cluster\":\"${CLUSTER}\",\"pool\":\"${POOL}\",\"duration_s\":${DURATION}}"
    echo "Logged gpu-failure for ${CLUSTER}/${POOL} duration=${DURATION}s"
    ;;
  network-slowdown)
    IFACE="${1:-eth0}"
    DELAY="${2:-50ms}"
    append_log "{\"timestamp\":\"$(timestamp)\",\"event\":\"network_slowdown\",\"interface\":\"${IFACE}\",\"delay\":\"${DELAY}\"}"
    if command -v tc >/dev/null 2>&1 && [[ "$(id -u)" -eq 0 ]]; then
      tc qdisc add dev "$IFACE" root netem delay "$DELAY" || true
      echo "Applied tc qdisc delay ${DELAY} on ${IFACE}"
    else
      echo "tc unavailable or not root; logged slowdown event only"
    fi
    ;;
  memory-pressure)
    TARGET="${1:-scheduler}"
    SIZE_MB="${2:-4096}"
    append_log "{\"timestamp\":\"$(timestamp)\",\"event\":\"memory_pressure\",\"target\":\"${TARGET}\",\"size_mb\":${SIZE_MB}}"
    if command -v stress-ng >/dev/null 2>&1; then
      stress-ng --vm 1 --vm-bytes "${SIZE_MB}M" --timeout 15s >/dev/null 2>&1 || true
      echo "Attempted memory pressure with stress-ng"
    else
      echo "stress-ng unavailable; logged memory pressure event only"
    fi
    ;;
  *)
    echo "usage:"
    echo "  $0 gpu-failure <cluster> <pool> [duration_s]"
    echo "  $0 network-slowdown <iface> [delay]"
    echo "  $0 memory-pressure <target> [size_mb]"
    exit 1
    ;;
esac

