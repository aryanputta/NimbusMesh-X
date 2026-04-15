#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise SystemExit("matplotlib is required for plotting. Install with `pip install matplotlib`.")

    results_dir = Path("results")
    latency_path = results_dir / "latency.csv"
    if not latency_path.exists():
        raise SystemExit("results/latency.csv not found. Run simulations first.")

    rows = list(csv.DictReader(latency_path.open()))
    labels = [f"{row['config_name']}:{row['policy_name']}" for row in rows]
    p95 = [float(row["p95_latency_ms"]) for row in rows]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(labels, p95)
    ax.set_ylabel("p95 latency (ms)")
    ax.set_title("NimbusMesh-X Policy Comparison")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    output = results_dir / "latency_comparison.png"
    fig.savefig(output)
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
