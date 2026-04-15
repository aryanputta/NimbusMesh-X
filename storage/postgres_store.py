from __future__ import annotations

import json
import os

from nimbusmesh_x.types import RequestResult


def _maybe_import_psycopg():
    try:
        import psycopg  # type: ignore
    except Exception:
        return None
    return psycopg


class PostgresExperimentStore:
    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or os.getenv("NIMBUS_POSTGRES_DSN", "")
        self.psycopg = _maybe_import_psycopg()
        self.enabled = bool(self.dsn and self.psycopg is not None)
        if self.enabled:
            self._ensure_tables()

    def _ensure_tables(self) -> None:
        if not self.enabled:
            return
        with self.psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS experiment_results (
                        id BIGSERIAL PRIMARY KEY,
                        request_id TEXT NOT NULL,
                        config_name TEXT NOT NULL,
                        policy_name TEXT NOT NULL,
                        tenant_id TEXT NOT NULL,
                        model_id TEXT NOT NULL,
                        cluster_id TEXT NOT NULL,
                        pool_id TEXT NOT NULL,
                        total_latency_ms DOUBLE PRECISION NOT NULL,
                        cache_hit_ratio DOUBLE PRECISION NOT NULL,
                        cost_usd DOUBLE PRECISION NOT NULL,
                        payload JSONB NOT NULL
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS experiment_summaries (
                        id BIGSERIAL PRIMARY KEY,
                        config_name TEXT NOT NULL,
                        policy_name TEXT NOT NULL,
                        summary JSONB NOT NULL
                    );
                    """
                )
            conn.commit()

    def write_result(self, config_name: str, result: RequestResult) -> None:
        if not self.enabled:
            return
        payload = result.to_dict()
        with self.psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO experiment_results (
                        request_id, config_name, policy_name, tenant_id, model_id,
                        cluster_id, pool_id, total_latency_ms, cache_hit_ratio, cost_usd, payload
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb);
                    """,
                    (
                        result.request.request_id,
                        config_name,
                        result.decision.policy_name,
                        result.request.tenant_id,
                        result.request.model_id,
                        result.decision.cluster_id,
                        result.decision.pool_id,
                        result.total_latency_ms,
                        result.cache_hit_ratio,
                        result.cost_usd,
                        json.dumps(payload),
                    ),
                )
            conn.commit()

    def write_summary(self, config_name: str, policy_name: str, summary: dict[str, object]) -> None:
        if not self.enabled:
            return
        with self.psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO experiment_summaries (config_name, policy_name, summary)
                    VALUES (%s, %s, %s::jsonb);
                    """,
                    (config_name, policy_name, json.dumps(summary)),
                )
            conn.commit()
