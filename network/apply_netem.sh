#!/usr/bin/env bash
set -euo pipefail

IFACE="${1:-eth0}"
ACTION="${2:-delay}"
VALUE="${3:-50ms}"

if ! command -v tc >/dev/null 2>&1; then
  echo "tc not available"
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "run as root to apply netem rules"
  exit 1
fi

case "$ACTION" in
  delay)
    tc qdisc add dev "$IFACE" root netem delay "$VALUE"
    ;;
  loss)
    tc qdisc add dev "$IFACE" root netem loss "$VALUE"
    ;;
  rate)
    tc qdisc add dev "$IFACE" root tbf rate "$VALUE" burst 32kbit latency 400ms
    ;;
  clear)
    tc qdisc del dev "$IFACE" root || true
    ;;
  *)
    echo "usage: $0 <iface> <delay|loss|rate|clear> [value]"
    exit 1
    ;;
esac

