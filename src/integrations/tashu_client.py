from __future__ import annotations

import os
import time
import random
from typing import Dict


def _clamp(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))


async def fetch_live_status() -> Dict[str, dict]:
    """
    Mock live status generator.
    - station_id별 bikes를 0~capacity 범위에서 랜덤/시간변동으로 생성
    - capacity는 여기서 안 주고(혹은 줘도 됨), CSV capacity를 쓰게 해도 됨
    """
    mode = os.getenv("LIVE_MODE", "mock").lower()
    if mode != "mock":
        # 실데이터 모드(나중에 붙일 때) 대비: 지금은 비워두기
        return {}

    # 시간에 따라 조금씩 바뀌게 seed를 흔들기
    t = int(time.time() // 20)  # 20초마다 패턴 변화
    rnd = random.Random(t)

    # NOTE: 여기서는 station_id만 필요하므로,
    # 실제 사용은 public.py에서 list_stations() 돌면서 station_id 기준으로 참조하게 됨.
    # 그래서 여기서는 "모든 station_id에 대한 dict"를 만들 수 없고,
    # public.py에서 station_id를 넣어 생성하는 방식이 더 깔끔함.
    #
    # => 그래서 public.py에서 "mock_live_for(station)"을 쓰는 방식을 추천함.
    return {}
