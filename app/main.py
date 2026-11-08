from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.ml.predictor import pricing_predictor
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if pricing_predictor.model_available:
        print("ML pricing model loaded")
    else:
        print("ML model not found — baseline formula active")
    yield


app = FastAPI(
    title="Send Run API",
    description="Intelligent courier tracking and pricing for Ondo State",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import auth, orders, pricing, tracking, routes, admin, locations

app.include_router(auth.router)
app.include_router(orders.router)
app.include_router(pricing.router)
app.include_router(tracking.router)
app.include_router(routes.router)
app.include_router(admin.router)
app.include_router(locations.router)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "ml_model": "loaded" if pricing_predictor.model_available else "baseline",
    }