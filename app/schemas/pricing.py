from pydantic import BaseModel, Field


class PricingRequest(BaseModel):
    package_size: str = Field(pattern="^(envelope|small|medium|large|extra_large)$")
    package_weight: str = Field(pattern="^(very_light|light|medium|heavy|very_heavy)$")
    distance_km: float = Field(gt=0)
    vehicle_type: str = Field(pattern="^(small_car|big_bus)$")
    route_risk: int = Field(ge=1, le=5)
    day_of_week: int = Field(ge=0, le=6)
    is_festive_period: bool = False
    fuel_price_per_litre: float = Field(gt=0)


class PricingResponse(BaseModel):
    price: float
    model_used: str

class PricingInternalResponse(BaseModel):
    predicted_price: float
    price_breakdown: dict
    confidence_band: dict
    model_used: str


class QuickQuoteRequest(BaseModel):
    origin_park: str
    destination: str
    package_size: str = Field(pattern="^(envelope|small|medium|large|extra_large)$")
    package_weight: str = Field(pattern="^(very_light|light|medium|heavy|very_heavy)$")
    vehicle_type: str = Field(pattern="^(small_car|big_bus)$")