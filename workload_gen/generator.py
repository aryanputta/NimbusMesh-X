from __future__ import annotations

import csv
import math
import random
from collections import defaultdict
from pathlib import Path

from nimbusmesh_x.config import DistributionConfig, WorkloadConfig
from nimbusmesh_x.types import InferenceRequest, stable_prefix_signature


class WorkloadGenerator:
    def __init__(self, config: WorkloadConfig, seed: int) -> None:
        self.config = config
        self.random = random.Random(seed)
        self.seed = seed
        self.sessions: dict[tuple[str, str], list[str]] = defaultdict(list)

    def generate_requests(self) -> list[InferenceRequest]:
        if self.config.trace_path:
            return self._generate_requests_from_trace(Path(self.config.trace_path))
        arrivals = self._generate_arrivals()
        requests: list[InferenceRequest] = []
        for index, arrival_ts in enumerate(arrivals):
            tenant_id = self._weighted_choice(self.config.tenant_weights)
            model_id = self._weighted_choice(self.config.model_mix)
            sla_class = self._weighted_choice(self.config.sla_mix)
            session_id = self._pick_session(tenant_id, model_id)
            prompt_tokens = self._sample_tokens(self.config.prompt_tokens)
            generation_tokens = self._sample_tokens(self.config.generation_tokens)
            if self.random.random() < self.config.cache_hostility:
                prefix_signature = stable_prefix_signature(tenant_id, model_id, None, salt=f"hostile-{index}")
            else:
                prefix_signature = stable_prefix_signature(
                    tenant_id,
                    model_id,
                    session_id,
                    salt=f"{prompt_tokens // 256}:{generation_tokens // 128}",
                )
            max_latency_ms = {
                "realtime": 900.0,
                "interactive": 1800.0,
                "best_effort": 4200.0,
            }[sla_class]
            requests.append(
                InferenceRequest(
                    request_id=f"req-{index:06d}",
                    tenant_id=tenant_id,
                    model_id=model_id,
                    prompt_tokens=prompt_tokens,
                    generation_tokens=generation_tokens,
                    arrival_ts=round(arrival_ts, 4),
                    sla_class=sla_class,
                    session_id=session_id,
                    prefix_signature=prefix_signature,
                    max_latency_ms=max_latency_ms,
                    metadata={"seed": self.seed},
                )
            )
        return requests

    def _generate_requests_from_trace(self, trace_path: Path) -> list[InferenceRequest]:
        if not trace_path.exists():
            raise FileNotFoundError(f"Trace file not found: {trace_path}")
        rows: list[dict[str, str]] = []
        with trace_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            required = {
                "timestamp",
                "request_id",
                "prompt_length",
                "expected_output_length",
                "tenant_id",
                "priority_class",
            }
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"Trace file is missing required columns: {sorted(missing)}")
            for row in reader:
                rows.append(row)
        if self.config.trace_limit is not None:
            rows = rows[: self.config.trace_limit]

        requests: list[InferenceRequest] = []
        first_ts = float(rows[0]["timestamp"]) if rows else 0.0
        for index, row in enumerate(rows):
            raw_ts = float(row["timestamp"])
            arrival_ts = max(0.0, (raw_ts - first_ts) / max(1e-9, self.config.trace_replay_speed))
            prompt_tokens = max(1, int(float(row["prompt_length"])))
            generation_tokens = max(1, int(float(row["expected_output_length"])))
            tenant_id = row["tenant_id"] or "tenant-unknown"
            sla_class = row.get("priority_class", self.config.trace_default_sla) or self.config.trace_default_sla
            model_id = row.get("model_id", self.config.trace_default_model) or self.config.trace_default_model
            session_id = row.get("session_id") or self._pick_session(tenant_id, model_id)
            prefix_signature = stable_prefix_signature(
                tenant_id,
                model_id,
                session_id,
                salt=f"{prompt_tokens // 256}:{generation_tokens // 128}",
            )
            max_latency_ms = {
                "realtime": 900.0,
                "interactive": 1800.0,
                "best_effort": 4200.0,
            }.get(sla_class, 1800.0)
            requests.append(
                InferenceRequest(
                    request_id=row.get("request_id", f"trace-{index:06d}"),
                    tenant_id=tenant_id,
                    model_id=model_id,
                    prompt_tokens=prompt_tokens,
                    generation_tokens=generation_tokens,
                    arrival_ts=round(arrival_ts, 4),
                    sla_class=sla_class if sla_class in {"realtime", "interactive", "best_effort"} else "interactive",
                    session_id=session_id,
                    prefix_signature=prefix_signature,
                    max_latency_ms=max_latency_ms,
                    metadata={"seed": self.seed, "source": str(trace_path)},
                )
            )
        if self.config.request_count > 0 and len(requests) > self.config.request_count:
            return requests[: self.config.request_count]
        return requests

    def _generate_arrivals(self) -> list[float]:
        request_count = self.config.request_count
        duration = self.config.duration_s
        if self.config.arrival_pattern == "uniform":
            return [i * (duration / max(1, request_count)) for i in range(request_count)]
        if self.config.arrival_pattern == "bursty":
            arrivals: list[float] = []
            burst_windows = [
                (duration * 0.2, duration * 0.3),
                (duration * 0.55, duration * 0.65),
                (duration * 0.8, duration * 0.9),
            ]
            for _ in range(request_count):
                if self.random.random() < min(0.75, 0.35 * self.config.burst_factor):
                    start, end = self.random.choice(burst_windows)
                    arrivals.append(self.random.uniform(start, end))
                else:
                    arrivals.append(self.random.uniform(0.0, duration))
            return sorted(arrivals)
        rate = request_count / max(duration, 1e-9)
        arrivals = []
        now = 0.0
        for _ in range(request_count):
            now += self.random.expovariate(rate)
            arrivals.append(min(duration, now))
        return arrivals

    def _sample_tokens(self, distribution: DistributionConfig) -> int:
        if distribution.distribution == "uniform":
            value = self.random.uniform(distribution.min, distribution.max)
        elif distribution.distribution == "normal":
            value = self.random.gauss(distribution.mean, distribution.sigma * distribution.mean)
        else:
            value = self.random.lognormvariate(math.log(max(1.0, distribution.mean)), distribution.sigma)
        return int(max(distribution.min, min(distribution.max, value)))

    def _weighted_choice(self, weights: dict[str, float]) -> str:
        items = list(weights.items())
        population = [key for key, _ in items]
        probs = [weight for _, weight in items]
        return self.random.choices(population, weights=probs, k=1)[0]

    def _pick_session(self, tenant_id: str, model_id: str) -> str:
        key = (tenant_id, model_id)
        if self.sessions[key] and self.random.random() < self.config.session_reuse_probability:
            return self.random.choice(self.sessions[key])
        session_id = f"{tenant_id}-{model_id}-{len(self.sessions[key]):04d}"
        self.sessions[key].append(session_id)
        return session_id
