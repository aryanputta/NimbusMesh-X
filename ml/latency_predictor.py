from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

try:  # pragma: no cover - optional dependency path
    import torch
    from torch import nn
except Exception:  # pragma: no cover - optional dependency path
    torch = None
    nn = None


@dataclass
class LatencyPredictorConfig:
    epochs: int = 20
    learning_rate: float = 1e-3
    hidden_size: int = 32


class LatencyPredictor:
    def __init__(self, config: LatencyPredictorConfig) -> None:
        if torch is None or nn is None:  # pragma: no cover - dependency path
            raise RuntimeError("PyTorch is required for LatencyPredictor.")
        self.config = config
        self.model = nn.Sequential(
            nn.Linear(5, config.hidden_size),
            nn.ReLU(),
            nn.Linear(config.hidden_size, config.hidden_size),
            nn.ReLU(),
            nn.Linear(config.hidden_size, 1),
        )

    def train_from_csv(self, path: str | Path) -> float:
        if torch is None or nn is None:  # pragma: no cover - dependency path
            raise RuntimeError("PyTorch is required for LatencyPredictor.")
        rows = list(csv.DictReader(Path(path).open("r", encoding="utf-8")))
        if not rows:
            raise ValueError("No rows found for training.")
        features = []
        labels = []
        for row in rows:
            features.append(
                [
                    float(row.get("prompt_length", 0)),
                    float(row.get("expected_output_length", 0)),
                    1.0 if row.get("priority_class") == "realtime" else 0.0,
                    1.0 if row.get("priority_class") == "best_effort" else 0.0,
                    float(len(row.get("tenant_id", ""))),
                ]
            )
            labels.append(float(row.get("observed_latency_ms", row.get("latency_ms", 0))))
        x = torch.tensor(features, dtype=torch.float32)
        y = torch.tensor(labels, dtype=torch.float32).unsqueeze(1)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.config.learning_rate)
        loss_fn = nn.MSELoss()
        final_loss = 0.0
        for _ in range(self.config.epochs):
            preds = self.model(x)
            loss = loss_fn(preds, y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            final_loss = float(loss.item())
        return final_loss

    def save(self, path: str | Path) -> None:
        if torch is None:  # pragma: no cover - dependency path
            raise RuntimeError("PyTorch is required for LatencyPredictor.")
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.model.state_dict(), target)

