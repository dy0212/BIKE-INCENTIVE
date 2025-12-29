from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, app_env: str = "development"):
        super().__init__(app)
        self.app_env = app_env

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Basic hardening
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # CSP: in production you can tighten; Leaflet loads from unpkg + OSM tiles
        # Keep it permissive enough for MVP.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' https://unpkg.com https://{s}.tile.openstreetmap.org; "
            "script-src 'self' 'unsafe-inline' https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://unpkg.com; "
            "img-src 'self' data: https://*.tile.openstreetmap.org; "
            "connect-src 'self';"
        )
        return response
