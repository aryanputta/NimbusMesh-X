# NimbusMesh-X

NimbusMesh-X is a topology-aware and KV-cache-aware inference control plane for Azure-style multi-cluster AI factories. It targets a real systems gap between hyperscale orchestration and GPU inference efficiency by jointly optimizing cluster routing, accelerator selection, cache locality, topology locality, congestion, and multi-tenant SLA pressure.

This repository is intentionally built as a systems project, not an LLM app shell. The current implementation provides:

- A runnable discrete-event simulation for multi-cluster inference routing
- Topology and fabric-cost modeling across heterogeneous accelerator pools
- KV-cache directory logic with reuse-aware scheduling signals
- Heuristic and learning-inspired routing policies
- A benchmark harness with reproducible workload configs
- FastAPI control-plane endpoints for routing and simulation
- Real backend adapter scaffolding for `vLLM` and `Triton`, plus a live `mock` backend for simulation
- Terminal-level observability scripts and structured JSON logs
- GPU topology parsing from `nvidia-smi topo -m`
- Optional CUDA-backed candidate scoring hooks
- Azure-native AKS and cost-model simulation overlays
- Nsight profiling entrypoints plus deployment assets for Docker and Kubernetes
- Trace-driven workload replay from normalized real datasets in `data/workloads/`
- Optional gRPC service-to-service routing, Ray distributed sweeps, Redis cache metadata, PostgreSQL experiment persistence
- Optional C++ scheduler core for low-latency candidate selection

## Thesis

Modern inference stacks optimize isolated layers: Kubernetes scheduling, GPU allocation, serving runtime internals, or cache management. NimbusMesh-X instead treats inference placement as a cross-layer control-plane problem:

- Which cluster should receive a request
- Which accelerator pool should execute it
- Whether cache locality should beat fabric locality
- When a cheaper accelerator should absorb low-priority load
- How congestion, memory pressure, and fairness should change routing online

## Architecture

The implemented path mirrors the intended full system:

- `workload_gen/`: synthetic workloads with tenant skew, SLA classes, cache reuse, and burst patterns
- `data_pipeline/`: dataset fetchers + normalizers for Alibaba, ShareGPT, LMSYS, and generic traces
- `topology_service/`: graph-based cluster and pool connectivity plus affinity scoring
- `cache_directory/`: in-memory KV-cache directory with reuse scoring and offload hints
- `control_plane/`: candidate generation, multi-objective routing, and API surface
- `cluster_scheduler/`: local placement onto pool slots with queue and memory accounting
- `serving_backends/`: `mock`, `vllm`, and `triton` adapters
- `policies/`: round-robin, least-queue, topology-aware, cache-aware, multi-objective, and contextual-bandit routing
- `simulators/`: deterministic simulation engine
- `simulators/ray_engine.py`: distributed policy sweeps using Ray
- `benchmarks/`: batch comparison harness for baseline policies
- `scheduler_core_cpp/`: low-latency C++ candidate selector
- `grpc_layer/`: gRPC proto, stub generation, scheduler server/client
- `storage/`: Redis and PostgreSQL persistence adapters

## Quick Start

Create a virtual environment, install the package, and run a simulation:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,data,runtime]"
python scripts/run_simulation.py --config configs/multi_cluster_long_context.json
```

Run the benchmark suite:

```bash
python scripts/run_benchmarks.py --config configs/multi_cluster_long_context.json
```

Collect host-level metrics during a run:

```bash
bash scripts/system_probe.sh --once
```

Profile with Nsight:

```bash
bash profiling/run_nsight.sh
```

Normalize datasets into workload traces:

```bash
python scripts/normalize_workloads.py --config configs/dataset_pipeline.yaml
python scripts/run_simulation.py --config configs/trace_sharegpt_replay.json
```

Prepare all live-demo artifacts in one command:

```bash
bash scripts/live_demo_bootstrap.sh
```

Run distributed benchmark sweeps with Ray:

```bash
python scripts/run_benchmarks.py --config configs/multi_cluster_long_context.json --distributed
```

Build and enable the C++ scheduler core:

```bash
bash scripts/build_cpp_core.sh
export NIMBUS_USE_CPP_CORE=1
python scripts/run_simulation.py --config configs/multi_cluster_long_context.json
```

Enable gRPC routing:

```bash
python scripts/run_grpc_server.py --port 50051
export NIMBUS_USE_GRPC_ROUTER=1
export NIMBUS_GRPC_TARGET=127.0.0.1:50051
python scripts/run_simulation.py --config configs/multi_cluster_long_context.json
```

Start the API:

```bash
python scripts/run_api.py
```

Then query the router:

```bash
curl -X POST http://127.0.0.1:8000/v1/route \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "demo-1",
    "tenant_id": "copilot",
    "model_id": "llama-3-70b",
    "prompt_tokens": 8192,
    "generation_tokens": 1024,
    "arrival_ts": 0.0,
    "sla_class": "realtime",
    "session_id": "copilot-session-1"
  }'
```

## Benchmark Modes

Shipped configs cover the major modes from the project thesis:

- `configs/single_cluster_baseline.json`
- `configs/multi_cluster_long_context.json`
- `configs/cache_friendly_sessions.json`
- `configs/failure_congestion.json`
- `configs/heterogeneous_accelerators.json`
- `configs/trace_sharegpt_replay.json`

## Policy Baselines

Implemented now:

- `round_robin`
- `least_queue`
- `spread`
- `topology_greedy`
- `cache_aware`
- `multi_objective`
- `contextual_bandit`
- `gnn_placeholder`

Planned next:

- PPO / DQN training loops
- graph neural network encoders over the topology graph
- exact or near-exact solvers for micro-instance comparisons

## What Is Real Today

Implemented and measurable:

- deterministic workload generation with fixed seeds
- trace replay from normalized datasets in `data/workloads`
- topology graph shortest-path cost
- cache reuse scoring and cache-visibility timing
- queue-delay estimation and pool-level placement
- SLA, fairness, cost, and throughput accounting
- benchmark repeatability tests
- CSV result export (`results/*.csv`) and JSON structured log fanout (`logs/*.log`)

Intentionally scaffolded rather than overstated:

- live Triton / vLLM adapters exist, but the repository does not claim integrated production deployments until wired to real endpoints
- RL and GNN folders are present, but only the lightweight contextual bandit is productionized in this revision
- Redis / Postgres / Ray / gRPC / C++ integrations are optional and env-gated for local portability

## Deliverables in Repo

- [System Design](docs/system_design.md)
- [Failure Analysis](docs/failure_analysis.md)
- [Demo Playbook](docs/demo_playbook.md)
- [Live Demo Runbook](docs/live_demo.md)
- [Stack and Datasets](docs/stack_and_datasets.md)
- [Papers and Context](papers/README.md)
- [Grafana Dashboard Stub](dashboards/grafana-dashboard.json)
- [Azure Cluster Overlay](configs/azure_cluster.yaml)

## Recruiter Framing

Use this line:

> I built a control plane for AI inference factories that improves request placement by jointly optimizing GPU topology, memory-local KV-cache reuse, and multi-cluster latency-cost tradeoffs under realistic serving conditions.

That is the real point of the project. Everything in the repository is aimed at making that statement defendable with code, logs, and benchmark results.
