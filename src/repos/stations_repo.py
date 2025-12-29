from __future__ import annotations

import csv
import datetime
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class Station:
    station_id: str
    name: str
    lat: float
    lon: float
    capacity: int
    bikes: int
    region_id: str


# ===== CSV path resolution (local + Render secret) =====
BASE_DIR = Path(__file__).resolve().parents[2]  # bike-incentive/

DEFAULT_CSV = BASE_DIR / "data" / "tashu_stations.csv"
SECRET_CSV = Path("/etc/secrets/tashu_stations.csv")

# Optional override (ex: STATIONS_CSV_PATH=/etc/secrets/tashu_stations.csv)
CSV_PATH = Path(os.getenv("STATIONS_CSV_PATH", str(DEFAULT_CSV)))

# If local path doesn't exist but Render secret file exists, use it
if not CSV_PATH.exists() and SECRET_CSV.exists():
    CSV_PATH = SECRET_CSV


def _open_csv() -> tuple[str, object]:
    """
    Try common encodings (utf-8-sig first for Excel BOM),
    fallback to cp949 for Korean Windows CSV exports.
    Returns (encoding_used, file_object).
    """
    last_err: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            f = open(CSV_PATH, encoding=enc, newline="")
            return enc, f
        except Exception as e:
            last_err = e
    raise last_err  # type: ignore[misc]


def _read_csv_stations() -> List[Station]:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    stations: List[Station] = []

    enc, f = _open_csv()
    with f:
        reader = csv.DictReader(f)

        required = {"station_id", "name", "lat", "lon", "capacity", "region_id"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"CSV header must include: {sorted(required)}. got: {reader.fieldnames} (encoding={enc})"
            )

        for row in reader:
            # Safety: skip duplicated header rows accidentally included as data
            if row.get("lat", "").strip().lower() == "lat":
                continue

            station_id = (row.get("station_id") or "").strip()
            name = (row.get("name") or "").strip()

            if not station_id or not name:
                # Skip bad/empty rows
                continue

            lat_str = (row.get("lat") or "").strip()
            lon_str = (row.get("lon") or "").strip()
            cap_str = (row.get("capacity") or "").strip()
            region_id = (row.get("region_id") or "").strip() or "R1"

            try:
                lat = float(lat_str)
                lon = float(lon_str)
            except ValueError as e:
                raise ValueError(f"Invalid lat/lon for station_id={station_id}: lat='{lat_str}', lon='{lon_str}'") from e

            # capacity can be empty; allow 0
            capacity = int(float(cap_str)) if cap_str else 0

            stations.append(
                Station(
                    station_id=station_id,
                    name=name,
                    lat=lat,
                    lon=lon,
                    capacity=capacity,
                    bikes=0,  # live API will overwrite later
                    region_id=region_id,
                )
            )

    return stations


# Simple cache to avoid re-reading file on every request
_STATIONS_CACHE: Optional[List[Station]] = None


def list_stations() -> List[Station]:
    global _STATIONS_CACHE
    if _STATIONS_CACHE is None:
        _STATIONS_CACHE = _read_csv_stations()

    # Return copies so runtime mutations (live overwrite) won't pollute cache
    return [Station(**s.__dict__) for s in _STATIONS_CACHE]


def get_station(station_id: str) -> Optional[Station]:
    for s in list_stations():
        if s.station_id == station_id:
            return s
    return None


def touch_update() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
