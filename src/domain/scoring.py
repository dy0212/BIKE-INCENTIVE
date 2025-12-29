from __future__ import annotations
from dataclasses import dataclass
from src.config import settings


@dataclass
class StationState:
    capacity: int
    bikes: int
    rent_count_w: int
    return_count_w: int


def compute_predicted_bikes(state: StationState) -> float:
    # simple drift model
    w = max(settings.WINDOW_MIN, 1)
    drift_per_min = (state.rent_count_w - state.return_count_w) / w
    return state.bikes - drift_per_min * settings.PRED_MIN


def compute_scores(state: StationState) -> tuple[float, float]:
    """
    Returns (shortage_score, congestion_score) normalized by capacity: 0..~1
    """
    cap = max(state.capacity, 1)
    bikes_pred = compute_predicted_bikes(state)

    target_low = settings.F_LOW * cap
    target_high = settings.F_HIGH * cap

    shortage = max(0.0, target_low - bikes_pred)
    congestion = max(0.0, bikes_pred - target_high)

    return (shortage / cap, congestion / cap)
