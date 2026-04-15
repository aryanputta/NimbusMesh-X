from storage.postgres_store import PostgresExperimentStore
from storage.redis_store import RedisDecisionStore


def test_redis_store_disabled_without_url(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUS_REDIS_URL", raising=False)
    store = RedisDecisionStore(redis_url="")
    assert store.enabled is False
    store.write_decision({"request": {"request_id": "r1"}})


def test_postgres_store_disabled_without_dsn(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUS_POSTGRES_DSN", raising=False)
    store = PostgresExperimentStore(dsn="")
    assert store.enabled is False

