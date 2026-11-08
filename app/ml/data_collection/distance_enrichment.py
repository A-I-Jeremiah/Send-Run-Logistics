import requests
from app.config import get_settings


def get_route_distance(origin: str, destination: str) -> dict | None:
    """
    Use Google Maps Distance Matrix API to get actual
    driving distance and duration for a route.
    """
    settings = get_settings()
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"

    params = {
        "origins": f"{origin}, Ondo State, Nigeria",
        "destinations": f"{destination}, Nigeria",
        "key": settings.GOOGLE_MAPS_API_KEY,
        "units": "metric",
    }

    resp = requests.get(url, params=params, timeout=10)
    data = resp.json()

    try:
        element = data["rows"][0]["elements"][0]
        if element["status"] == "OK":
            return {
                "distance_km": element["distance"]["value"] / 1000,
                "duration_mins": element["duration"]["value"] // 60,
            }
    except (KeyError, IndexError):
        pass

    return None