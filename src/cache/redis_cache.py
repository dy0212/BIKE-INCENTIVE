from __future__ import annotations
from typing import Optional
import redis
from src.config import settings


class RedisCache:
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        if settings.REDIS_URL:
            self.client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    def is_enabled(self) -> bool:
        return self.client is not None

    def incr_with_ttl(self, key: str, ttl_sec: int) -> None:
        if not self.client:
            return
        pipe = self.client.pipeline()
        pipe.incr(key, 1)
        pipe.expire(key, ttl_sec)
        pipe.execute()

    def get_int(self, key: str) -> int:
        if not self.client:
            return 0
        v = self.client.get(key)
        return int(v) if v else 0

    def set_json(self, key: str, value: str, ttl_sec: int) -> None:
        if not self.client:
            return
        self.client.set(key, value, ex=ttl_sec)
