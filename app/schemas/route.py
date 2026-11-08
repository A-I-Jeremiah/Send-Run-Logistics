import uuid
from pydantic import BaseModel, Field


class RouteCreate(BaseModel):
    origin: str
    destination: str
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float
    distance_km: float = Field(gt=0)
    estimated_duration_mins: int = Field(gt=0)
    risk_level: int = Field(ge=1, le=5)


class RouteResponse(BaseModel):
    id: uuid.UUID
    origin: str
    destination: str
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float
    distance_km: float
    estimated_duration_mins: int
    risk_level: int

    class Config:
        from_attributes = True


class AvailableDestinations(BaseModel):
    origin: str
    destinations: list[RouteResponse]