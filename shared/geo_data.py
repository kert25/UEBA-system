"""Static country/city → coordinates lookup and haversine distance."""

from __future__ import annotations

import math

# Format: {country: {city: (lat, lon)}}
GEO_COORDS: dict[str, dict[str, tuple[float, float]]] = {
    "Russia": {
        "Moscow": (55.7558, 37.6173),
        "Saint Petersburg": (59.9343, 30.3351),
        "Novosibirsk": (55.0084, 82.9357),
        "Yekaterinburg": (56.8389, 60.6057),
        "Kazan": (55.7961, 49.1064),
        "Vladivostok": (43.1155, 131.8855),
    },
    "United States": {
        "New York": (40.7128, -74.0060),
        "Los Angeles": (34.0522, -118.2437),
        "Chicago": (41.8781, -87.6298),
        "San Francisco": (37.7749, -122.4194),
    },
    "United Kingdom": {
        "London": (51.5074, -0.1278),
        "Manchester": (53.4808, -2.2426),
    },
    "Germany": {
        "Berlin": (52.5200, 13.4050),
        "Munich": (48.1351, 11.5820),
    },
    "China": {
        "Beijing": (39.9042, 116.4074),
        "Shanghai": (31.2304, 121.4737),
    },
    "Japan": {
        "Tokyo": (35.6762, 139.6503),
    },
    "France": {
        "Paris": (48.8566, 2.3522),
    },
    "India": {
        "Mumbai": (19.0760, 72.8777),
        "New Delhi": (28.6139, 77.2090),
    },
    "Brazil": {
        "Sao Paulo": (-23.5505, -46.6333),
    },
    "Australia": {
        "Sydney": (-33.8688, 151.2093),
    },
    "Unknown": {
        "Unknown": (0.0, 0.0),
    },
}


def get_coordinates(country: str, city: str | None = None) -> tuple[float, float]:
    """Return (lat, lon) for country/city. Fallback to (0.0, 0.0)."""
    country_data = GEO_COORDS.get(country, GEO_COORDS.get("Unknown"))
    if city and city in country_data:
        return country_data[city]
    first_city = next(iter(country_data.values()))
    return first_city


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance between two points in km using the haversine formula."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))
