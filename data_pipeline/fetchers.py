from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def _maybe_import_datasets():
    try:
        from datasets import load_dataset  # type: ignore
    except Exception:
        return None
    return load_dataset


def fetch_sharegpt(output_dir: str | Path, sample_size: int = 10_000) -> Path:
    load_dataset = _maybe_import_datasets()
    if load_dataset is None:
        raise RuntimeError("`datasets` package is required for Hugging Face dataset download.")
    dataset = load_dataset("ShareGPT_Vicuna_unfiltered", split="train")
    records = []
    for row in dataset.take(sample_size):
        records.append({k: row[k] for k in row.keys()})
    target = Path(output_dir) / "sharegpt_raw.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(records))
    return target


def fetch_lmsys(output_dir: str | Path, sample_size: int = 10_000) -> Path:
    load_dataset = _maybe_import_datasets()
    if load_dataset is None:
        raise RuntimeError("`datasets` package is required for Hugging Face dataset download.")
    dataset = load_dataset("lmsys/chatbot_arena_conversations", split="train")
    records = []
    for row in dataset.take(sample_size):
        records.append({k: row[k] for k in row.keys()})
    target = Path(output_dir) / "lmsys_raw.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(records))
    return target


def fetch_openorca(output_dir: str | Path, sample_size: int = 10_000) -> Path:
    load_dataset = _maybe_import_datasets()
    if load_dataset is None:
        raise RuntimeError("`datasets` package is required for Hugging Face dataset download.")
    dataset = load_dataset("Open-Orca/OpenOrca", split="train")
    records = []
    for row in dataset.take(sample_size):
        records.append({k: row[k] for k in row.keys()})
    target = Path(output_dir) / "openorca_raw.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(records))
    return target


def fetch_ultrachat(output_dir: str | Path, sample_size: int = 10_000) -> Path:
    load_dataset = _maybe_import_datasets()
    if load_dataset is None:
        raise RuntimeError("`datasets` package is required for Hugging Face dataset download.")
    dataset = load_dataset("HuggingFaceH4/ultrachat_200k", split="train_sft")
    records = []
    for row in dataset.take(sample_size):
        records.append({k: row[k] for k in row.keys()})
    target = Path(output_dir) / "ultrachat_raw.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(records))
    return target


def fetch_dolly(output_dir: str | Path, sample_size: int = 10_000) -> Path:
    load_dataset = _maybe_import_datasets()
    if load_dataset is None:
        raise RuntimeError("`datasets` package is required for Hugging Face dataset download.")
    dataset = load_dataset("databricks/databricks-dolly-15k", split="train")
    records = []
    for row in dataset.take(sample_size):
        records.append({k: row[k] for k in row.keys()})
    target = Path(output_dir) / "dolly_raw.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(records))
    return target


def fetch_alibaba_cluster_trace(output_dir: str | Path, repo_url: str = "https://github.com/alibaba/clusterdata") -> Path:
    target_root = Path(output_dir) / "alibaba_clusterdata"
    if target_root.exists():
        return target_root
    target_root.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, str(target_root)],
        check=True,
    )
    return target_root


def fetch_azure_retail_prices(output_dir: str | Path) -> Path:
    target = Path(output_dir) / "azure_retail_prices.json"
    if target.exists():
        return target
    raise RuntimeError(
        "Azure Retail Prices should be fetched from Microsoft's AzureRetailPrices repo/API and stored as JSON."
    )


def fetch_mlperf_reference(output_dir: str | Path) -> Path:
    target = Path(output_dir) / "mlperf_reference.txt"
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "Download MLPerf inference benchmark artifacts from https://mlcommons.org/en/inference-datacenter/ "
        "and place normalized CSV in data/raw/mlperf.csv for ingestion with generic_csv normalizer.\n"
    )
    return target


FETCH_REGISTRY = {
    "sharegpt": fetch_sharegpt,
    "lmsys": fetch_lmsys,
    "openorca": fetch_openorca,
    "ultrachat": fetch_ultrachat,
    "dolly": fetch_dolly,
    "alibaba": fetch_alibaba_cluster_trace,
    "azure_retail": fetch_azure_retail_prices,
    "mlperf": fetch_mlperf_reference,
}
