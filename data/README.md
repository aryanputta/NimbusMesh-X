# Data Pipeline

This project supports both synthetic and real workload traces.

Directory contract:

- `data/raw/`: source datasets downloaded from upstream providers
- `data/workloads/`: normalized request traces consumed by `workload_gen/generator.py`

Normalized schema (`CSV`):

- `timestamp`
- `request_id`
- `prompt_length`
- `expected_output_length`
- `tenant_id`
- `priority_class`
- `model_id`
- `session_id`

Reproducible steps:

```bash
python scripts/fetch_real_datasets.py --dataset sharegpt --output-dir data/raw --sample-size 20000
python scripts/fetch_real_datasets.py --dataset lmsys --output-dir data/raw --sample-size 20000
python scripts/fetch_real_datasets.py --dataset openorca --output-dir data/raw --sample-size 20000
python scripts/fetch_real_datasets.py --dataset ultrachat --output-dir data/raw --sample-size 20000
python scripts/fetch_real_datasets.py --dataset dolly --output-dir data/raw --sample-size 20000
python scripts/fetch_real_datasets.py --dataset alibaba --output-dir data/raw
python scripts/normalize_workloads.py --config configs/dataset_pipeline.yaml
```

Then point an experiment config at one of these outputs using:

```json
"trace_path": "data/workloads/sharegpt_workload.csv"
```
