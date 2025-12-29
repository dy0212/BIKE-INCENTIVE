from __future__ import annotations
import time
from src.worker.tasks import recompute_and_cache

INTERVAL_SEC = 60  # 1 minute

def main():
    while True:
        result = recompute_and_cache(ttl_sec=90)
        print("[worker] recomputed:", result, flush=True)
        time.sleep(INTERVAL_SEC)

if __name__ == "__main__":
    main()
