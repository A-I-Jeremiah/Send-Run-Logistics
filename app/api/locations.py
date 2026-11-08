from fastapi import APIRouter, HTTPException
from app.data.states import NIGERIA_STATES

router = APIRouter(prefix="/locations", tags=["Locations"])


@router.get("/states")
def get_states():
    return {
        "count": len(NIGERIA_STATES),
        "states": NIGERIA_STATES
    }
