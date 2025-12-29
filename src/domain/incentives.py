from __future__ import annotations
from math import radians, sin, cos, sqrt, atan2
from src.config import settings


def clamp_int(v: float, lo: int, hi: int) -> int:
    return int(max(lo, min(hi, round(v))))


def compute_station_rewards(shortage_score: float, congestion_score: float) -> tuple[int, int]:
    """
    reward_return: incentive for returning to shortage stations
    reward_rent:   incentive for renting from congestion stations
    """
    reward_return = clamp_int(settings.ALPHA * shortage_score, 0, settings.MAX_FREE_MIN)
    reward_rent = clamp_int(settings.BETA * congestion_score, 0, settings.MAX_FREE_MIN)
    return reward_rent, reward_return


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    p1, p2 = radians(lat1), radians(lat2)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat / 2) ** 2 + cos(p1) * cos(p2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def compute_route_free_minutes(
    from_congestion_score: float,
    to_shortage_score: float,
    km: float,
) -> tuple[int, str]:
    """
    핵심 요구사항:
    - 강제 재배치 X
    - 이용자가 '과잉(혼잡) 지역 -> 부족 지역'으로 이동하면 무료시간(인센티브) 지급
    """
    # move incentive is high when "from is congested" and "to is shortage"
    signal = max(0.0, from_congestion_score) * max(0.0, to_shortage_score)

    # distance penalty to avoid "just go far for free"
    penalty = max(0.0, (km / max(settings.DIST_PENALTY_KM, 1e-6)))
    raw = settings.ROUTE_K * signal - penalty

    free_min = clamp_int(raw, 0, settings.MAX_FREE_MIN)

    if free_min <= 0:
        return 0, "해당 이동은 과잉→부족 분산 효과가 작아 인센티브가 0분입니다."
    return free_min, "과잉(혼잡) 대여소에서 대여 → 부족 대여소에 반납을 유도하는 인센티브입니다."
