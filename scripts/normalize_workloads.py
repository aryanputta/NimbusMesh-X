#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import yaml
except ImportError:
    yaml = None

from data_pipeline.normalizers import NORMALIZER_REGISTRY
from data_pipeline.utils import write_normalized_rows


def _load_pipeline_config(path: str | Path) -> dict[str, object]:
    if yaml is None:
        raise RuntimeError("PyYAML is required for pipeline config parsing.")
    payload = yaml.safe_load(Path(path).read_text())
    if not isinstance(payload, dict):
        raise ValueError("Pipeline config must be a YAML mapping.")
    return payload


def run_pipeline(config_path: str | Path) -> list[dict[str, object]]:
    payload = _load_pipeline_config(config_path)
    jobs = payload.get("jobs", [])
    if not isinstance(jobs, list):
        raise ValueError("`jobs` must be a list.")
    outputs: list[dict[str, object]] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        normalizer_name = str(job["normalizer"])
        input_path = str(job["input"])
        output_path = str(job["output"])
        limit = int(job["limit"]) if job.get("limit") is not None else None
        default_model = str(job.get("default_model", "llama-3-8b"))
        normalizer = NORMALIZER_REGISTRY[normalizer_name]
        rows = normalizer(input_path, limit=limit, default_model=default_model)
        write_normalized_rows(output_path, rows)
        outputs.append(
            {
                "normalizer": normalizer_name,
                "input": input_path,
                "output": output_path,
                "rows": len(rows),
            }
        )
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize raw datasets into /data/workloads schema.")
    parser.add_argument("--config", default="configs/dataset_pipeline.yaml")
    args = parser.parse_args()
    outputs = run_pipeline(args.config)
    print(json.dumps(outputs, indent=2))


if __name__ == "__main__":
    main()

