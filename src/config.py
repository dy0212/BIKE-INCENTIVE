from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "unjirohmoohyun"
    ALLOWED_ORIGINS: str = "http://127.0.0.1:8000,http://localhost:8000"
    ADMIN_API_KEY: str = "ehdduf0625!"
    REDIS_URL: str | None = None

    # scoring
    F_LOW: float = 0.20
    F_HIGH: float = 0.80
    WINDOW_MIN: int = 10
    PRED_MIN: int = 15

    # incentives
    MAX_FREE_MIN: int = 15
    ALPHA: float = 18.0
    BETA: float = 18.0
    ROUTE_K: float = 14.0
    DIST_PENALTY_KM: float = 8.0

    # rate limit
    PUBLIC_RATE_LIMIT: str = "60/minute"
    ADMIN_RATE_LIMIT: str = "20/minute"


settings = Settings()