from __future__ import annotations

from fastapi import APIRouter, Query, Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.config import settings
from src.repos.stations_repo import list_stations, get_station, touch_update
from src.repos.events_repo import get_window_counts
from src.domain.scoring import StationState, compute_scores
from src.domain.incentives import (
    compute_station_rewards,
    haversine_km,
    compute_route_free_minutes,
)
from src.domain.models import StationOut, RouteIncentiveOut

from src.integrations.tashu_client import fetch_live_status

router = APIRouter(prefix="/api/public", tags=["public"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/stations")
@limiter.limit(lambda: settings.PUBLIC_RATE_LIMIT)
async def stations(request: Request):
    """
    1) CSV(위치/거치대 등) 기반 station 목록 로드
    2) 실시간 API로 bikes/capacity 덮어쓰기
    3) 최근 대여/반납(윈도우) + 현재 재고로 점수/보상 계산
    """
    # 실시간 현황 가져오기 (실패해도 서비스는 유지되게: 빈 dict 처리)
    try:
        live = await fetch_live_status()  # { "S001": {"bikes": 12, "capacity": 20}, ... }
        if live is None:
            live = {}
    except Exception:
        live = {}

    out = []
    updated_at = touch_update()

    for s in list_stations():
        # ✅ 실시간 값 덮어쓰기
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

        out.append(
            StationOut(
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
            ).model_dump()
        )

    return out


@router.get("/route", response_model=RouteIncentiveOut)
@limiter.limit(lambda: settings.PUBLIC_RATE_LIMIT)
async def route_incentive(
    request: Request,
    from_station_id: str = Query(..., description="출발 대여소 ID"),
    to_station_id: str = Query(..., description="도착 대여소 ID"),
):
    """
    지도에서 두 대여소를 선택했을 때 이동 인센티브(무료 분) 계산
    """
    # station 존재 확인
    s_from = get_station(from_station_id)
    s_to = get_station(to_station_id)
    if not s_from or not s_to:
        raise HTTPException(status_code=404, detail="Station not found")

    # stations와 동일하게 실시간 덮어쓰기 적용(선택)
    try:
        live = await fetch_live_status()
        if live is None:
            live = {}
    except Exception:
        live = {}

    if s_from.station_id in live:
        s_from.bikes = int(live[s_from.station_id].get("bikes", s_from.bikes))
        s_from.capacity = int(live[s_from.station_id].get("capacity", s_from.capacity))
    if s_to.station_id in live:
        s_to.bikes = int(live[s_to.station_id].get("bikes", s_to.bikes))
        s_to.capacity = int(live[s_to.station_id].get("capacity", s_to.capacity))

    # 두 대여소 점수/보상 계산
    rents_f, returns_f = get_window_counts(s_from.station_id)
    st_f = StationState(s_from.capacity, s_from.bikes, rents_f, returns_f)
    sh_f, co_f = compute_scores(st_f)
    reward_rent_f, _ = compute_station_rewards(sh_f, co_f)

    rents_t, returns_t = get_window_counts(s_to.station_id)
    st_t = StationState(s_to.capacity, s_to.bikes, rents_t, returns_t)
    sh_t, co_t = compute_scores(st_t)
    _, reward_return_t = compute_station_rewards(sh_t, co_t)

    # 거리 + 무료분 계산
    dist_km = haversine_km(s_from.lat, s_from.lon, s_to.lat, s_to.lon)
    free_minutes = compute_route_free_minutes(
        dist_km=dist_km,
        reward_rent=reward_rent_f,
        reward_return=reward_return_t,
    )

    return RouteIncentiveOut(
        from_station_id=s_from.station_id,
        to_station_id=s_to.station_id,
        distance_km=dist_km,
        free_minutes=free_minutes,
    )
