from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.config import settings
from src.middleware.cors import add_cors
from src.middleware.security_headers import SecurityHeadersMiddleware
from src.middleware.rate_limit import init_rate_limiter, add_rate_limit_exception_handler

from src.api.public import router as public_router
from src.api.admin import router as admin_router

from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

def create_app() -> FastAPI:
    app = FastAPI(title="Bike Incentive System")

    # CORS (restrict to your domain in production)
    add_cors(app)

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware, app_env=settings.APP_ENV)

    # Rate limiter (slowapi)
    limiter = init_rate_limiter(app)
    add_rate_limit_exception_handler(app, limiter)

    # Static
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # Routes
    app.include_router(public_router)
    app.include_router(admin_router)

    # Static (절대경로로 고정: Render에서도 안 깨짐)
    BASE_DIR = Path(__file__).resolve().parents[1]   # 프로젝트 루트(bike-incentive)
    STATIC_DIR = BASE_DIR / "static"

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def root():
        return FileResponse(str(STATIC_DIR / "map.html"))

    @app.get("/health", tags=["health"])
    def health():
        return {"ok": True, "env": settings.APP_ENV}

    return app
