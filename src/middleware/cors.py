from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings


def add_cors(app: FastAPI) -> None:
    origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        max_age=600,
    )
