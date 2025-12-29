from pydantic import BaseModel


class StationOut(BaseModel):
    station_id: str
    name: str
    lat: float
    lon: float
    region_id: str
    capacity: int
    bikes: int

    # computed
    shortage_score: float
    congestion_score: float
    reward_return: int   # free minutes
    reward_rent: int     # free minutes
    updated_at: str


class RegionOut(BaseModel):
    region_id: str
    shortage: float
    congestion: float
    stations: int


class RouteIncentiveOut(BaseModel):
    from_station_id: str
    to_station_id: str
    km: float
    free_minutes: int
    reason: str
