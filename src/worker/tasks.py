from __future__ import annotations
import json
from time import time

from src.cache.redis_cache import RedisCache
from src.repos.stations_repo import list_stations, touch_update
from src.repos.events_repo import get_window_counts
from src.domain.scoring import StationState, compute_scores
from src.domain.incentives import compute_station_rewards

_cache = RedisCache()

def recompute_and_cache(ttl_sec: int = 30) -> dict:
    """
    Recompute station outputs and optionally cache in Redis.
    """
    updated_at = touch_update()
    payload = []

    for s in list_stations():
        rents, returns = get_window_counts(s.station_id)
        state = StationState(s.capacity, s.bikes, rents, returns)
        shortage_score, congestion_score = compute_scores(state)
        reward_rent, reward_return = compute_station_rewards(shortage_score, congestion_score)

        payload.append({
            "station_id": s.station_id,
            "name": s.name,
            "lat": s.lat,
            "lon": s.lon,
            "region_id": s.region_id,
            "capacity": s.capacity,
            "bikes": s.bikes,
            "shortage_score": shortage_score,
            "congestion_score": congestion_score,
            "reward_return": reward_return,
            "reward_rent": reward_rent,
            "updated_at": updated_at,
        })

    if _cache.is_enabled():
        _cache.set_json("public:stations_cache", json.dumps(payload), ttl_sec=ttl_sec)

    return {"updated_at": updated_at, "stations": len(payload)}
