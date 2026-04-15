from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StructuredDecisionLogger:
    def __init__(self, path: str | None) -> None:
        self.path = path
        if self.path:
            target = Path(self.path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("")

    def emit(self, payload: dict[str, Any]) -> None:
        if not self.path:
            return
        with Path(self.path).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

