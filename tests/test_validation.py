import pytest

from nimbusmesh_x.types import InferenceRequest


def test_invalid_requests_raise() -> None:
    with pytest.raises(ValueError):
        InferenceRequest(
            request_id="bad",
            tenant_id="tenant-a",
            model_id="llama-3-8b",
            prompt_tokens=0,
            generation_tokens=10,
            arrival_ts=0.0,
        )

