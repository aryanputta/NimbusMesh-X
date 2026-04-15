from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from data_pipeline.schema import NormalizedWorkloadRow
from data_pipeline.utils import approx_token_length, clamp_priority


def normalize_alibaba_cluster_trace(
    input_csv: str | Path,
    limit: int | None = None,
    default_model: str = "llama-3-8b",
) -> list[NormalizedWorkloadRow]:
    path = Path(input_csv)
    rows: list[NormalizedWorkloadRow] = []
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader):
            if limit is not None and len(rows) >= limit:
                break
            start_time = float(row.get("start_time", index))
            duration = float(row.get("task_duration", row.get("duration", 1.0)))
            cpu = float(row.get("cpu_usage", row.get("plan_cpu", 1.0)))
            memory = float(row.get("memory_usage", row.get("plan_mem", 1.0)))
            prompt_length = max(32, int((cpu * 220.0) + (memory * 100.0)))
            expected_output_length = max(16, int(duration * 40.0))
            machine_id = row.get("machine_id", "machine-unknown")
            tenant_id = f"tenant-{machine_id}"
            rows.append(
                NormalizedWorkloadRow(
                    timestamp=start_time,
                    request_id=row.get("task_id", f"alibaba-{index:07d}"),
                    prompt_length=prompt_length,
                    expected_output_length=expected_output_length,
                    tenant_id=tenant_id,
                    priority_class=clamp_priority(row.get("priority", "interactive")),
                    model_id=default_model,
                    session_id=f"{tenant_id}-session-{index // 4}",
                )
            )
    return rows


def normalize_sharegpt_dataset(
    input_json: str | Path,
    limit: int | None = None,
    default_model: str = "llama-3-70b",
) -> list[NormalizedWorkloadRow]:
    path = Path(input_json)
    payload = json.loads(path.read_text())
    records = payload if isinstance(payload, list) else payload.get("data", [])
    rows: list[NormalizedWorkloadRow] = []
    for index, record in enumerate(records):
        if limit is not None and len(rows) >= limit:
            break
        conversations = record.get("conversations") or record.get("conversation") or []
        if not conversations:
            continue
        prompt = ""
        response = ""
        for turn in conversations:
            role = (turn.get("from") or turn.get("role") or "").lower()
            value = turn.get("value") or turn.get("content") or ""
            if not prompt and role in {"human", "user"}:
                prompt = value
            elif not response and role in {"gpt", "assistant"}:
                response = value
            if prompt and response:
                break
        prompt_length = approx_token_length(prompt)
        output_length = approx_token_length(response)
        conv_id = record.get("id", f"sharegpt-{index:06d}")
        tenant_id = f"sharegpt-{hash(conv_id) % 1000:03d}"
        rows.append(
            NormalizedWorkloadRow(
                timestamp=float(index),
                request_id=str(conv_id),
                prompt_length=prompt_length,
                expected_output_length=max(16, output_length),
                tenant_id=tenant_id,
                priority_class="interactive",
                model_id=default_model,
                session_id=f"{tenant_id}-session-{index // 6}",
            )
        )
    return rows


def normalize_lmsys_dataset(
    input_path: str | Path,
    limit: int | None = None,
    default_model: str = "mixtral-8x7b",
) -> list[NormalizedWorkloadRow]:
    path = Path(input_path)
    rows: list[NormalizedWorkloadRow] = []
    if path.suffix.lower() == ".json":
        records = json.loads(path.read_text())
    else:
        records = []
        with path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            records.extend(reader)
    iterable = records if isinstance(records, list) else records.get("data", [])
    for index, record in enumerate(iterable):
        if limit is not None and len(rows) >= limit:
            break
        prompt = (
            record.get("prompt")
            or record.get("conversation_a")
            or record.get("input")
            or record.get("question")
            or ""
        )
        output = (
            record.get("response")
            or record.get("conversation_b")
            or record.get("output")
            or record.get("answer")
            or ""
        )
        prompt_length = approx_token_length(str(prompt))
        output_length = approx_token_length(str(output))
        model_id = record.get("model") or record.get("model_a") or default_model
        tenant = record.get("user_id") or f"arena-{index % 64:03d}"
        priority = "realtime" if index % 5 == 0 else "interactive"
        rows.append(
            NormalizedWorkloadRow(
                timestamp=float(index),
                request_id=str(record.get("id", f"lmsys-{index:06d}")),
                prompt_length=prompt_length,
                expected_output_length=max(16, output_length),
                tenant_id=str(tenant),
                priority_class=priority,
                model_id=str(model_id),
                session_id=f"{tenant}-session-{index // 8}",
            )
        )
    return rows


def normalize_instruction_dataset(
    input_path: str | Path,
    limit: int | None = None,
    default_model: str = "llama-3-8b",
) -> list[NormalizedWorkloadRow]:
    path = Path(input_path)
    records = json.loads(path.read_text())
    iterable = records if isinstance(records, list) else records.get("data", [])
    rows: list[NormalizedWorkloadRow] = []
    for index, record in enumerate(iterable):
        if limit is not None and len(rows) >= limit:
            break
        instruction = record.get("instruction") or record.get("prompt") or record.get("query") or ""
        context = record.get("context") or ""
        output = record.get("output") or record.get("response") or record.get("answer") or ""
        prompt_length = approx_token_length(f"{instruction}\n{context}".strip())
        output_length = approx_token_length(str(output))
        tenant = f"open-llm-{index % 48:02d}"
        rows.append(
            NormalizedWorkloadRow(
                timestamp=float(index),
                request_id=str(record.get("id", f"open-llm-{index:07d}")),
                prompt_length=prompt_length,
                expected_output_length=max(16, output_length),
                tenant_id=tenant,
                priority_class="interactive",
                model_id=default_model,
                session_id=f"{tenant}-session-{index // 5}",
            )
        )
    return rows


def normalize_generic_workload_csv(
    input_csv: str | Path,
    limit: int | None = None,
    default_model: str = "llama-3-8b",
) -> list[NormalizedWorkloadRow]:
    path = Path(input_csv)
    rows: list[NormalizedWorkloadRow] = []
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader):
            if limit is not None and len(rows) >= limit:
                break
            rows.append(
                NormalizedWorkloadRow(
                    timestamp=float(row.get("timestamp", index)),
                    request_id=row.get("request_id", f"generic-{index:07d}"),
                    prompt_length=max(1, int(float(row.get("prompt_length", 1)))),
                    expected_output_length=max(1, int(float(row.get("expected_output_length", 1)))),
                    tenant_id=row.get("tenant_id", f"tenant-{index % 16}"),
                    priority_class=clamp_priority(row.get("priority_class", "interactive")),
                    model_id=row.get("model_id", default_model),
                    session_id=row.get("session_id", f"session-{index // 4}"),
                )
            )
    return rows


NORMALIZER_REGISTRY = {
    "alibaba": normalize_alibaba_cluster_trace,
    "sharegpt": normalize_sharegpt_dataset,
    "lmsys": normalize_lmsys_dataset,
    "openorca": normalize_instruction_dataset,
    "ultrachat": normalize_instruction_dataset,
    "dolly": normalize_instruction_dataset,
    "mlperf": normalize_generic_workload_csv,
    "azure_retail": normalize_generic_workload_csv,
    "generic_csv": normalize_generic_workload_csv,
}
