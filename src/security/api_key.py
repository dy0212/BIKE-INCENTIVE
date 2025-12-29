from fastapi import Header, HTTPException
from src.config import settings


def require_admin_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    if not x_api_key or x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True
