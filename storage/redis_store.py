from __future__ import annotations

import json
import os


def _maybe_import_redis():
    try:
        import redis  # type: ignore
    except Exception:
        return None
    return redis


class RedisDecisionStore:
    def __init__(self, redis_url: str | None = None) -> None:
        self.redis_url = redis_url or os.getenv("NIMBUS_REDIS_URL", "")
        self.redis = _maybe_import_redis()
        self.enabled = bool(self.redis_url and self.redis is not None)
        self.client = self.redis.from_url(self.redis_url) if self.enabled else None

    def write_decision(self, result_dict: dict[str, object]) -> None:
        if not self.enabled or self.client is None:
            return
        request = result_dict.get("request", {})
        if not isinstance(request, dict):
            return
        request_id = request.get("request_id")
        if not isinstance(request_id, str):
            return
        self.client.hset("nimbusmesh:decisions", request_id, json.dumps(result_dict))

    def write_cache_affinity(self, cache_key: str, payload: dict[str, object]) -> None:
        if not self.enabled or self.client is None:
            return
        self.client.hset("nimbusmesh:cache_affinity", cache_key, json.dumps(payload))

    def fetch_cache_affinity(self, cache_key: str) -> dict[str, object] | None:
        if not self.enabled or self.client is None:
            return None
        value = self.client.hget("nimbusmesh:cache_affinity", cache_key)
        if value is None:
            return None
        decoded = value.decode("utf-8") if isinstance(value, bytes) else str(value)
        return json.loads(decoded)
