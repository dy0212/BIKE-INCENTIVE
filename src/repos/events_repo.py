from __future__ import annotations
from src.cache.redis_cache import RedisCache
from src.config import settings

_cache = RedisCache()

def _key(station_id: str, kind: str) -> str:
    # kind: rent / return
    return f"w{settings.WINDOW_MIN}:station:{station_id}:{kind}"

def record_event(station_id: str, kind: str) -> None:
    """
    In real system: ingest actual rent/return events.
    Here: increments rolling-window counters in Redis (if enabled).
    """
    ttl = max(settings.WINDOW_MIN, 1) * 60
    if _cache.is_enabled():
        _cache.incr_with_ttl(_key(station_id, kind), ttl_sec=ttl)

def get_window_counts(station_id: str) -> tuple[int, int]:
    """
    returns (rent_count_w, return_count_w)
    if Redis disabled -> 0,0 (MVP still works)
    """
    if not _cache.is_enabled():
        return 0, 0
    rents = _cache.get_int(_key(station_id, "rent"))
    returns = _cache.get_int(_key(station_id, "return"))
    return rents, returns
