# Live Demo Runbook

This runbook is optimized for a recruiter or systems interview demo.

## 1) Bootstrap the Demo

```bash
bash scripts/live_demo_bootstrap.sh
```

This command:

- installs dependencies
- normalizes real-trace samples into `data/workloads/`
- runs trace replay + baseline comparisons
- writes benchmark outputs to `results/`
- writes structured logs to `logs/`

## 2) Start the Control Plane API

```bash
python scripts/run_api.py
```

Health check:

```bash
curl http://127.0.0.1:8000/healthz
```

## 3) Show Real-Time Terminal View

In a second terminal:

```bash
bash scripts/live_dashboard.sh
```

Optional system probe in parallel:

```bash
bash scripts/system_probe.sh --once
```

## 4) Show Evidence

- `results/latency.csv`
- `results/throughput.csv`
- `results/cost_analysis.csv`
- `results/cache_hit_ratio.csv`
- `results/latency_comparison.png`
- `logs/scheduler.log`
- `logs/topology.log`
- `logs/cache.log`
- `logs/latency.log`

## 5) Talk Track (60-90 seconds)

NimbusMesh-X is a cross-layer inference control plane. It routes requests across multi-cluster heterogeneous accelerators using queue delay, topology affinity, cache locality, congestion, fairness, and cost signals. The benchmark outputs show tradeoffs between heuristic and adaptive policies, and the structured logs provide decision-level traceability for every request.

