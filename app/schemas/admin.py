from pydantic import BaseModel
from datetime import datetime


class DashboardStats(BaseModel):
    total_orders: int
    pending_orders: int
    in_transit_orders: int
    delivered_orders: int
    total_senders: int
    total_drivers: int
    verified_drivers: int
    average_predicted_price: float | None
    total_revenue_predicted: float
    model_accuracy: dict | None  # {"mae": ..., "rmse": ...}


class OrderVolumePoint(BaseModel):
    date: str
    count: int


class RouteActivity(BaseModel):
    origin: str
    destination: str
    order_count: int
    avg_price: float