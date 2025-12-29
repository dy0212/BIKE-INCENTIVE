from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.config import settings
from src.security.api_key import require_admin_api_key


router = APIRouter(prefix="/api/admin", tags=["admin"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/config")
@limiter.limit(lambda: settings.ADMIN_RATE_LIMIT)
def admin_config(request: Request, _=Depends(require_admin_api_key)):
    # don't leak secrets
    return {
        "env": settings.APP_ENV,
        "allowed_origins": settings.ALLOWED_ORIGINS,
        "scoring": {
            "F_LOW": settings.F_LOW,
            "F_HIGH": settings.F_HIGH,
            "WINDOW_MIN": settings.WINDOW_MIN,
            "PRED_MIN": settings.PRED_MIN,
        },
        "incentives": {
            "MAX_FREE_MIN": settings.MAX_FREE_MIN,
            "ALPHA": settings.ALPHA,
            "BETA": settings.BETA,
            "ROUTE_K": settings.ROUTE_K,
            "DIST_PENALTY_KM": settings.DIST_PENALTY_KM,
        }
    }


@router.post("/recompute")
@limiter.limit(lambda: settings.ADMIN_RATE_LIMIT)
def recompute_now(request: Request, _=Depends(require_admin_api_key)):
    # MVP: real recompute is on-the-fly in /stations.
    # In production: trigger worker job + cache result.
    return {"ok": True, "message": "MVP에서는 /api/public/stations가 실시간 계산합니다."}
