from __future__ import annotations

from fastapi import APIRouter, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.config import settings
from src.repos.stations_repo import list_stations, get_station, touch_update
from src.repos.events_repo import get_window_counts
from src.domain.scoring import StationState, compute_scores
from src.domain.incentives import compute_station_rewards, haversine_km, compute_route_free_minutes
from src.domain.models import StationOut, RegionOut, RouteIncentiveOut


router = APIRouter(prefix="/api/public", tags=["public"])

limiter = Limiter(key_func=get_remote_address)


@router.get("/stations")
@limiter.limit(lambda: settings.PUBLIC_RATE_LIMIT)
def stations(request: Request):
    out = []
    updated_at = touch_update()

    for s in list_stations():
        rents, returns = get_window_counts(s.station_id)
        state = StationState(
            capacity=s.capacity,
            bikes=s.bikes,
            rent_count_w=rents,
            return_count_w=returns,
        )
        shortage_score, congestion_score = compute_scores(state)
        reward_rent, reward_return = compute_station_rewards(shortage_score, congestion_score)

        out.append(StationOut(
            station_id=s.station_id,
            name=s.name,
            lat=s.lat,
            lon=s.lon,
            region_id=s.region_id,
            capacity=s.capacity,
            bikes=s.bikes,
            shortage_score=shortage_score,
            congestion_score=congestion_score,
            reward_return=reward_return,
            reward_rent=reward_rent,
            updated_at=updated_at,
        ).model_dump())

    return out


# src/api/public.py 상단에 추가(없으면)
from src.integrations.tashu_client import fetch_live_status

@router.get("/stations")
@limiter.limit(lambda: settings.PUBLIC_RATE_LIMIT)
async def stations(request: Request):  # ✅ async로 변경
    live = await fetch_live_status()   # ✅ 여기서 실시간 현황을 가져옴

    out = []
    updated_at = touch_update()

    for s in list_stations():
        # ✅ 여기서 CSV 기반 대여소에 실시간 값 덮어쓰기
        if s.station_id in live:
            s.bikes = int(live[s.station_id].get("bikes", s.bikes))
            s.capacity = int(live[s.station_id].get("capacity", s.capacity))

        rents, returns = get_window_counts(s.station_id)
        state = StationState(
            capacity=s.capacity,
            bikes=s.bikes,
            rent_count_w=rents,
            return_count_w=returns,
        )
        shortage_score, congestion_score = compute_scores(state)
        reward_rent, reward_return = compute_station_rewards(shortage_score, congestion_score)

        out.append(StationOut(
            station_id=s.station_id,
            name=s.name,
            lat=s.lat,
            lon=s.lon,
            region_id=s.region_id,
            capacity=s.capacity,
            bikes=s.bikes,
            shortage_score=shortage_score,
            congestion_score=congestion_score,
            reward_return=reward_return,
            reward_rent=reward_rent,
            updated_at=updated_at,
        ).model_dump())

    return out
