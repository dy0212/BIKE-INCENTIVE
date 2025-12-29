from __future__ import annotations
from dataclasses import dataclass
from time import time
from typing import Dict, Optional


@dataclass
class ClaimRecord:
    last_claim_ts: float
    total_claims: int


class AntiAbuseGuard:
    """
    MVP anti-abuse.
    Real-world: store in Redis/Postgres keyed by user_id / ride_id.
    """
    def __init__(self, cooldown_sec: int = 300):
        self.cooldown_sec = cooldown_sec
        self._claims: Dict[str, ClaimRecord] = {}

    def can_claim(self, key: str) -> bool:
        now = time()
        rec = self._claims.get(key)
        if rec is None:
            return True
        return (now - rec.last_claim_ts) >= self.cooldown_sec

    def mark_claimed(self, key: str) -> None:
        now = time()
        rec = self._claims.get(key)
        if rec is None:
            self._claims[key] = ClaimRecord(last_claim_ts=now, total_claims=1)
        else:
            rec.last_claim_ts = now
            rec.total_claims += 1
