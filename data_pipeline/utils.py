from __future__ import annotations

import csv
from pathlib import Path

from data_pipeline.schema import NormalizedWorkloadRow


NORMALIZED_COLUMNS = [
    "timestamp",
    "request_id",
    "prompt_length",
    "expected_output_length",
    "tenant_id",
    "priority_class",
    "model_id",
    "session_id",
]


def write_normalized_rows(path: str | Path, rows: list[NormalizedWorkloadRow]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=NORMALIZED_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "timestamp": round(row.timestamp, 6),
                    "request_id": row.request_id,
                    "prompt_length": row.prompt_length,
                    "expected_output_length": row.expected_output_length,
                    "tenant_id": row.tenant_id,
                    "priority_class": row.priority_class,
                    "model_id": row.model_id,
                    "session_id": row.session_id,
                }
            )


def clamp_priority(raw: str) -> str:
    value = (raw or "").strip().lower()
    if value in {"realtime", "interactive", "best_effort"}:
        return value
    if value in {"high", "p0", "critical"}:
        return "realtime"
    if value in {"low", "p2", "batch"}:
        return "best_effort"
    return "interactive"


def approx_token_length(text: str) -> int:
    stripped = (text or "").strip()
    if not stripped:
        return 1
    # Lightweight tokenizer approximation; deterministic and portable.
    return max(1, int(len(stripped.split()) * 1.33))

