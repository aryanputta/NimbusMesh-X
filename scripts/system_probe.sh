#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="${LOG_DIR:-logs}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/system_metrics.log}"
INTERVAL="${INTERVAL:-5}"
ONCE="${1:-}"

mkdir -p "$LOG_DIR"
touch "$LOG_FILE"

capture_cmd() {
  local label="$1"
  shift
  {
    echo "===== ${label} ====="
    echo "timestamp=$(date -Iseconds)"
    if command -v "$1" >/dev/null 2>&1; then
      "$@" 2>&1 || true
    else
      echo "missing-command: $1"
    fi
    echo
  } >>"$LOG_FILE"
}

capture_interactive() {
  local label="$1"
  local command_name="$2"
  shift 2
  {
    echo "===== ${label} ====="
    echo "timestamp=$(date -Iseconds)"
    if command -v "$command_name" >/dev/null 2>&1; then
      "$@" 2>&1 || true
    else
      echo "missing-command: ${command_name}"
    fi
    echo
  } >>"$LOG_FILE"
}

probe_once() {
  capture_cmd "nvidia-smi" nvidia-smi
  capture_cmd "nvidia-smi topo -m" nvidia-smi topo -m
  capture_interactive "nvtop" nvtop timeout 2 nvtop
  capture_interactive "htop" htop htop -b -n 1
  capture_cmd "iostat" iostat
  capture_cmd "vmstat" vmstat
  capture_cmd "free -m" free -m
  capture_cmd "df -h" df -h
  capture_cmd "netstat -i" netstat -i
  capture_cmd "ss -tulnp" ss -tulnp
  capture_cmd "active processes" ps aux
}

if [[ "$ONCE" == "--once" ]]; then
  probe_once
  exit 0
fi

while true; do
  probe_once
  sleep "$INTERVAL"
done

