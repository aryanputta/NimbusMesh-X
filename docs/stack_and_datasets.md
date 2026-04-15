# Production Stack and Dataset Layer

This document maps NimbusMesh-X implementation choices to production-grade expectations: runnable components, real datasets, reproducible normalization, and benchmarkable outputs.

## Runtime Stack

- `C++`: low-latency candidate selector in `scheduler_core_cpp/`
- `Python`: control plane, simulation orchestration, and data pipeline
- `gRPC`: scheduler service path in `grpc_layer/`
- `FastAPI`: REST control endpoints in `control_plane/api.py`
- `Ray`: distributed benchmark execution in `simulators/ray_engine.py`
- `Redis`: cache metadata and decision mirroring (env-gated)
- `PostgreSQL`: per-request and summary experiment persistence (env-gated)

## NVIDIA and Profiling Stack

- Inference adapters: `serving_backends/{triton,vllm,mock}_backend.py`
- CUDA runtime hooks: `cuda_kernels/runtime.py`
- Custom kernels:
  - `cuda_kernels/cache_score_kernel.cu`
  - `cuda_kernels/topology_cost_kernel.cu`
  - `cuda_kernels/load_balance_kernel.cu`
- Profiling:
  - `profiling/run_nsight.sh`
  - `scripts/system_probe.sh`
  - `scripts/live_dashboard.sh`

## Azure-Style Layer

- Cluster shape simulation: `configs/azure_cluster.yaml`
- Azure queue and monitor overlay: `azure_sim/environment.py`
- Terraform simulation definitions: `terraform/main.tf` and `terraform/terraform.tfvars`
- Kubernetes deployment assets: `k8s/*.yaml`

## Real Dataset Integration

Supported normalizers:

- Alibaba cluster trace style CSV -> `alibaba`
- ShareGPT conversation JSON -> `sharegpt`
- LMSYS Chatbot Arena style JSON/CSV -> `lmsys`
- OpenOrca / UltraChat / Dolly instruction data -> `openorca`, `ultrachat`, `dolly`
- MLPerf and Azure Retail normalized CSV ingestion -> `mlperf`, `azure_retail` via `generic_csv` schema
- Generic normalized CSV -> `generic_csv`

Pipeline files:

- fetch: `scripts/fetch_real_datasets.py`
- normalize: `scripts/normalize_workloads.py`
- config: `configs/dataset_pipeline.yaml`
- output schema: `data/workloads/*.csv`

Normalized columns:

- `timestamp`
- `request_id`
- `prompt_length`
- `expected_output_length`
- `tenant_id`
- `priority_class`
- `model_id`
- `session_id`

## Reproducible Pipeline

```bash
pip install -e ".[dev,data,runtime]"
python scripts/normalize_workloads.py --config configs/dataset_pipeline.yaml
python scripts/run_simulation.py --config configs/trace_sharegpt_replay.json
python scripts/run_benchmarks.py --config configs/multi_cluster_long_context.json --distributed
```

One-shot local run:

```bash
bash scripts/run_repro_pipeline.sh
```

## Measurable Outputs

CSV outputs in `results/`:

- `latency.csv`
- `throughput.csv`
- `gpu_utilization.csv`
- `cost_analysis.csv`
- `cache_hit_ratio.csv`

Structured logs in `logs/`:

- `scheduler.log`
- `cache.log`
- `topology.log`
- `latency.log`
- `failure_events.log`

Legacy detailed logs are also maintained for compatibility (`scheduler_decisions.log`, `cache_hits.log`, and others).
