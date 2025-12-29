from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import datetime


@dataclass
class Station:
    station_id: str
    name: str
    lat: float
    lon: float
    capacity: int
    bikes: int
    region_id: str


# ✅ 프로젝트 루트(bike-incentive/) 기준으로 data 파일 찾기
BASE_DIR = Path(__file__).resolve().parents[2]
CSV_PATH = BASE_DIR / "data" / "tashu_stations.csv"


def _read_csv_stations() -> List[Station]:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    stations: List[Station] = []

    # ✅ 엑셀 저장 CSV는 종종 utf-8-sig(BOM)라서 이게 안전
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"station_id", "name", "lat", "lon", "capacity", "region_id"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(f"CSV header must include: {sorted(required)}. got: {reader.fieldnames}")

        for row in reader:
            stations.append(Station(
                station_id=row["station_id"].strip(),
                name=row["name"].strip(),
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                capacity=int(float(row["capacity"])) if row["capacity"] else 0,
                bikes=0,  # 실시간 API로 나중에 덮어쓸 값
                region_id=row["region_id"].strip() or "R1",
            ))

    return stations


# 간단 캐시(서버가 /stations를 자주 호출하니까 매번 파일 읽지 않도록)
_STATIONS_CACHE: Optional[List[Station]] = None


def list_stations() -> List[Station]:
    global _STATIONS_CACHE
    if _STATIONS_CACHE is None:
        _STATIONS_CACHE = _read_csv_stations()
    # 객체를 그대로 리턴하면 bikes/capacity를 덮어쓸 때 캐시가 오염될 수 있어서 복사본 리턴
    return [Station(**s.__dict__) for s in _STATIONS_CACHE]


def get_station(station_id: str) -> Optional[Station]:
    for s in list_stations():
        if s.station_id == station_id:
            return s
    return None


def touch_update() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
