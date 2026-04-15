from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from nimbusmesh_x.types import InferenceRequest, RequestResult
from storage.redis_store import RedisDecisionStore


@dataclass
class CacheEntry:
    key: str
    cluster_id: str
    pool_id: str
    size_tokens: int
    size_gb: float
    available_ts: float
    last_touched: float
    hit_count: int = 0


class KVCacheDirectory:
    def __init__(self, ttl_s: float = 180.0, max_entries: int = 20_000) -> None:
        self.ttl_s = ttl_s
        self.max_entries = max_entries
        self.entries: dict[str, list[CacheEntry]] = defaultdict(list)
        self.redis_store = RedisDecisionStore()

    @staticmethod
    def _key(request: InferenceRequest) -> str:
        return f"{request.model_id}:{request.tenant_id}:{request.prefix_signature}"

    def evict_stale(self, now: float) -> None:
        for key, bucket in list(self.entries.items()):
            survivors = [entry for entry in bucket if now - entry.last_touched <= self.ttl_s]
            if survivors:
                self.entries[key] = survivors
            else:
                del self.entries[key]

    def score(self, request: InferenceRequest, cluster_id: str, pool_id: str, now: float) -> tuple[float, int]:
        self.evict_stale(now)
        if not self.entries.get(self._key(request)):
            self._hydrate_from_redis(request)
        best_ratio = 0.0
        best_saved_tokens = 0
        for entry in self.entries.get(self._key(request), []):
            if entry.available_ts > now:
                continue
            freshness = max(0.1, 1.0 - ((now - entry.last_touched) / self.ttl_s))
            if entry.cluster_id == cluster_id and entry.pool_id == pool_id:
                location_bonus = 1.0
            elif entry.cluster_id == cluster_id:
                location_bonus = 0.7
            else:
                location_bonus = 0.35
            hit_ratio = min(0.95, freshness * location_bonus)
            saved_tokens = int(min(entry.size_tokens, request.prompt_tokens) * hit_ratio)
            if hit_ratio > best_ratio:
                best_ratio = hit_ratio
                best_saved_tokens = saved_tokens
        return round(best_ratio, 4), best_saved_tokens

    def observe(self, result: RequestResult) -> None:
        if not result.admitted:
            return
        key = self._key(result.request)
        bucket = self.entries[key]
        matched = False
        for entry in bucket:
            if entry.cluster_id == result.decision.cluster_id and entry.pool_id == result.decision.pool_id:
                entry.size_tokens = max(entry.size_tokens, result.request.prompt_tokens)
                entry.size_gb = max(entry.size_gb, result.memory_gb * 0.55)
                entry.available_ts = result.completion_ts
                entry.last_touched = result.completion_ts
                entry.hit_count += int(result.cache_hit_ratio > 0.0)
                matched = True
                break
        if not matched:
            bucket.append(
                CacheEntry(
                    key=key,
                    cluster_id=result.decision.cluster_id,
                    pool_id=result.decision.pool_id,
                    size_tokens=result.request.prompt_tokens,
                    size_gb=result.memory_gb * 0.55,
                    available_ts=result.completion_ts,
                    last_touched=result.completion_ts,
                    hit_count=int(result.cache_hit_ratio > 0.0),
                )
            )
        if len(bucket) > 4:
            bucket.sort(key=lambda item: (item.hit_count, item.last_touched), reverse=True)
            del bucket[4:]
        self._persist_to_redis(key)
        self._trim()

    def reserved_gb(self, cluster_id: str, pool_id: str, now: float) -> float:
        self.evict_stale(now)
        total = 0.0
        for bucket in self.entries.values():
            for entry in bucket:
                if entry.cluster_id == cluster_id and entry.pool_id == pool_id:
                    total += entry.size_gb
        return total

    def offload_recommendation(self, cluster_id: str, pool_id: str, memory_pressure: float, now: float) -> str:
        reserved = self.reserved_gb(cluster_id, pool_id, now)
        if memory_pressure > 0.85 and reserved > 8.0:
            return "offload-cold-cache"
        if memory_pressure > 0.7:
            return "replicate-hot-prefix-only"
        return "retain"

    def snapshot(self, now: float) -> dict[str, object]:
        self.evict_stale(now)
        return {
            "entries": {
                key: [
                    {
                        "cluster_id": entry.cluster_id,
                        "pool_id": entry.pool_id,
                        "size_tokens": entry.size_tokens,
                        "size_gb": round(entry.size_gb, 4),
                        "available_ts": entry.available_ts,
                        "last_touched": entry.last_touched,
                        "hit_count": entry.hit_count,
                    }
                    for entry in bucket
                ]
                for key, bucket in self.entries.items()
            }
        }

    def _trim(self) -> None:
        total_entries = sum(len(bucket) for bucket in self.entries.values())
        if total_entries <= self.max_entries:
            return
        items = []
        for key, bucket in self.entries.items():
            for entry in bucket:
                items.append((entry.hit_count, entry.last_touched, key, entry))
        items.sort()
        while total_entries > self.max_entries and items:
            _, _, key, victim = items.pop(0)
            bucket = self.entries[key]
            if victim in bucket:
                bucket.remove(victim)
                total_entries -= 1
            if not bucket:
                del self.entries[key]

    def _persist_to_redis(self, key: str) -> None:
        if not self.redis_store.enabled:
            return
        payload = {
            "entries": [
                {
                    "cluster_id": entry.cluster_id,
                    "pool_id": entry.pool_id,
                    "size_tokens": entry.size_tokens,
                    "size_gb": entry.size_gb,
                    "available_ts": entry.available_ts,
                    "last_touched": entry.last_touched,
                    "hit_count": entry.hit_count,
                }
                for entry in self.entries.get(key, [])
            ]
        }
        self.redis_store.write_cache_affinity(key, payload)

    def _hydrate_from_redis(self, request: InferenceRequest) -> None:
        if not self.redis_store.enabled:
            return
        key = self._key(request)
        payload = self.redis_store.fetch_cache_affinity(key)
        if not payload:
            return
        entries_payload = payload.get("entries", [])
        if not isinstance(entries_payload, list):
            return
        hydrated = []
        for item in entries_payload:
            if not isinstance(item, dict):
                continue
            hydrated.append(
                CacheEntry(
                    key=key,
                    cluster_id=str(item.get("cluster_id", "")),
                    pool_id=str(item.get("pool_id", "")),
                    size_tokens=int(item.get("size_tokens", 0)),
                    size_gb=float(item.get("size_gb", 0.0)),
                    available_ts=float(item.get("available_ts", 0.0)),
                    last_touched=float(item.get("last_touched", 0.0)),
                    hit_count=int(item.get("hit_count", 0)),
                )
            )
        if hydrated:
            self.entries[key] = hydrated
