from __future__ import annotations

import logging
import os
import time
import random

from fastapi import APIRouter, Query, Request, HTTPException, Header
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

# 실데이터 모드로 갈 수도 있게 import는 남겨둠(지금은 LIVE_MODE=mock면 안 씀)
from src.integrations.tashu_client import fetch_live_status

router = APIRouter(prefix="/api/public", tags=["public"])
limiter = Limiter(key_func=get_remote_address)

logger = logging.getLogger(__name__)


def mock_bikes(station_id: str, capacity: int) -> int:
    """
    대여소별 bikes를 '시간에 따라 조금씩 변하는' 가짜 데이터로 생성.
    - 같은 station_id는 같은 시점에 항상 같은 값(안정적)
    - 20초마다 값이 조금씩 바뀜(실시간 느낌)
    """
    t = int(time.time() // 20)  # 20초 단위로 패턴 변경
    rnd = random.Random(hash(station_id) ^ t)
    return rnd.randint(0, max(0, int(capacity)))


@router.get("/stations")
@limiter.limit(lambda: settings.PUBLIC_RATE_LIMIT)
async def stations(request: Request):
    """
    stations 리스트를 반환.
    - LIVE_MODE=mock (기본): bikes를 mock으로 생성
    - LIVE_MODE=real: fetch_live_status()로 실시간 값 덮어쓰기(나중에 붙일 때)
    """
    live_mode = os.getenv("LIVE_MODE", "mock").lower()

    live = {}
    if live_mode == "real":
        try:
            live = await fetch_live_status()
            if live is None:
                live = {}
        except Exception:
            logger.exception("fetch_live_status failed; falling back to empty live dict")
            live = {}

    out = []
    updated_at = touch_update()

    for s in list_stations():
        # ✅ bikes 채우기: mock 또는 real
        if live_mode == "mock":
            s.bikes = mock_bikes(s.station_id, s.capacity)
        else:
            # real 모드: 실시간 값 덮어쓰기(매칭 되는 것만)
            if s.station_id in live:
                s.bikes = int(live[s.station_id].get("bikes", s.bikes))
                # capacity는 실시간이 없으면 CSV를 유지하는 게 보통 더 안전
                if "capacity" in live[s.station_id]:
                    s.capacity = int(live[s.station_id].get("capacity", s.capacity))

        # 최근 대여/반납 카운트(window)
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
    s_from = get_station(from_station_id)
    s_to = get_station(to_station_id)
    if not s_from or not s_to:
        raise HTTPException(status_code=404, detail="Station not found")

    live_mode = os.getenv("LIVE_MODE", "mock").lower()

    # route에서도 stations와 동일한 bikes 기준을 사용(중요)
    if live_mode == "mock":
        s_from.bikes = mock_bikes(s_from.station_id, s_from.capacity)
        s_to.bikes = mock_bikes(s_to.station_id, s_to.capacity)
    else:
        try:
            live = await fetch_live_status()
            if live is None:
                live = {}
        except Exception:
            logger.exception("fetch_live_status failed (route); using empty live dict")
            live = {}

        if s_from.station_id in live:
            s_from.bikes = int(live[s_from.station_id].get("bikes", s_from.bikes))
        if s_to.station_id in live:
            s_to.bikes = int(live[s_to.station_id].get("bikes", s_to.bikes))

    # 출발 대여소 보상(빌려가기 유도)
    rents_f, returns_f = get_window_counts(s_from.station_id)
    st_f = StationState(
        capacity=s_from.capacity,
        bikes=s_from.bikes,
        rent_count_w=rents_f,
        return_count_w=returns_f,
    )
    sh_f, co_f = compute_scores(st_f)
    reward_rent_f, _ = compute_station_rewards(sh_f, co_f)

    # 도착 대여소 보상(반납 유도)
    rents_t, returns_t = get_window_counts(s_to.station_id)
    st_f = StationState(
        capacity=s_from.capacity,
        bikes=s_from.bikes,
        rent_count_w=rents_f,
        return_count_w=returns_f,
    )
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


@router.get("/debug/live")
async def debug_live(
    request: Request,
    x_api_key: str = Header(default="", alias="X-API-Key"),
):
    """
    연동/매칭 상태 확인용(관리자 키 필요)
    - LIVE_MODE=mock이면 "mock" 통계
    - LIVE_MODE=real이면 live_keys/matched 확인
    """
    if x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    live_mode = os.getenv("LIVE_MODE", "mock").lower()
    stations = list_stations()

    if live_mode == "mock":
        return {
            "ok": True,
            "mode": "mock",
            "stations": len(stations),
            "sample_station_ids": [s.station_id for s in stations[:10]],
        }

    # real 모드
    try:
        live = await fetch_live_status()
        if live is None:
            live = {}
    except Exception as e:
        logger.exception("fetch_live_status failed (debug)")
        return {"ok": False, "mode": "real", "error": str(e)}

    matched = sum(1 for s in stations if s.station_id in live)

    return {
        "ok": True,
        "mode": "real",
        "live_keys": len(live),
        "stations": len(stations),
        "matched": matched,
        "sample_live_keys": list(live.keys())[:10],
        "sample_station_ids": [s.station_id for s in stations[:10]],
    }
