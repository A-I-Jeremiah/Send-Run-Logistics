from pydantic import BaseModel, Field


class GPSUpdate(BaseModel):
    order_id: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy: float = Field(ge=0)
    timestamp: int


class LocationResponse(BaseModel):
    driver_id: str
    lat: float
    lng: float
    accuracy: float
    updated_at: int