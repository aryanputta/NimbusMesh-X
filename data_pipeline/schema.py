from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedWorkloadRow:
    timestamp: float
    request_id: str
    prompt_length: int
    expected_output_length: int
    tenant_id: str
    priority_class: str
    model_id: str
    session_id: str

