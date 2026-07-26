"""
Weather scraper using Open-Meteo (https://open-meteo.com/).
Completely free, no API key required.

Two modes:
  - Historical: fetch conditions for a past match date
  - Current/forecast: fetch live conditions for a venue right now
"""

import logging
import requests
from datetime import date, datetime, timedelta
from venue_coordinates import get_venue_coords

logger = logging.getLogger(__name__)

# Open-Meteo endpoints
_ARCHIVE_URL  = "https://archive-api.open-meteo.com/v1/archive"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Variables we want for cricket relevance
_HOURLY_VARS = ",".join([
    "temperature_2m",
    "relativehumidity_2m",
    "dewpoint_2m",
    "precipitation",
    "precipitation_probability",
    "cloudcover",
    "windspeed_10m",
    "winddirection_10m",
])

_CURRENT_VARS = ",".join([
    "temperature_2m",
    "relativehumidity_2m",
    "dewpoint_2m",
    "precipitation",
    "cloudcover",
    "windspeed_10m",
    "winddirection_10m",
    "weathercode",
])

# WMO weather code → human description
WMO_CODES: dict[int, str] = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    77: "Snow grains",
    80: "Slight showers", 81: "Moderate showers", 82: "Heavy showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


def get_match_weather(venue: str, match_date: date | None = None) -> dict | None:
    """
    Fetch weather for a venue on a given date (or today if None).

    Returns a dict with cricket-relevant fields, or None on failure.
    Keys: temp_c, humidity_pct, dewpoint_c, precip_mm, cloud_pct,
          wind_kph, wind_dir, description, rain_risk, dew_risk, source_date.
    """
    coords = get_venue_coords(venue)
    if coords is None:
        logger.debug(f"No coordinates for venue: {venue!r}")
        return None

    lat, lon = coords
    target_date = match_date or date.today()
    today = date.today()

    try:
        if target_date < today - timedelta(days=1):
            return _fetch_historical(lat, lon, target_date)
        else:
            return _fetch_current(lat, lon)
    except Exception as exc:
        logger.warning(f"Weather fetch failed for {venue} on {target_date}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Internal fetchers
# ---------------------------------------------------------------------------

def _fetch_historical(lat: float, lon: float, match_date: date) -> dict | None:
    """Fetch daily-average conditions from Open-Meteo Archive API."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": match_date.isoformat(),
        "end_date": match_date.isoformat(),
        "hourly": _HOURLY_VARS,
        "timezone": "UTC",
    }
    resp = requests.get(_ARCHIVE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    hourly = data.get("hourly", {})
    if not hourly:
        return None

    # Use afternoon hours (12:00–18:00 UTC) as representative of match time
    times = hourly.get("time", [])
    idx_range = [i for i, t in enumerate(times) if "T12" <= t[-5:] <= "T18"]
    if not idx_range:
        idx_range = list(range(len(times)))

    def avg(key):
        vals = [hourly[key][i] for i in idx_range if hourly.get(key) and hourly[key][i] is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    def total(key):
        vals = [hourly[key][i] for i in idx_range if hourly.get(key) and hourly[key][i] is not None]
        return round(sum(vals), 1) if vals else None

    temp      = avg("temperature_2m")
    humidity  = avg("relativehumidity_2m")
    dewpoint  = avg("dewpoint_2m")
    precip    = total("precipitation")
    cloud     = avg("cloudcover")
    wind      = avg("windspeed_10m")

    return _build_result(temp, humidity, dewpoint, precip, None, cloud, wind, None, match_date)


def _fetch_current(lat: float, lon: float) -> dict | None:
    """Fetch current conditions from Open-Meteo Forecast API."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": _CURRENT_VARS,
        "hourly": "precipitation_probability",
        "forecast_hours": 6,
        "timezone": "UTC",
    }
    resp = requests.get(_FORECAST_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    cur = data.get("current", {})
    if not cur:
        return None

    # Rain probability — take max over next 6 hours
    hourly = data.get("hourly", {})
    rain_prob_vals = hourly.get("precipitation_probability", [])
    rain_prob = max(rain_prob_vals) if rain_prob_vals else None

    wmo  = cur.get("weathercode")
    desc = WMO_CODES.get(wmo, f"Code {wmo}") if wmo is not None else None

    return _build_result(
        temp=cur.get("temperature_2m"),
        humidity=cur.get("relativehumidity_2m"),
        dewpoint=cur.get("dewpoint_2m"),
        precip=cur.get("precipitation"),
        rain_prob=rain_prob,
        cloud=cur.get("cloudcover"),
        wind=cur.get("windspeed_10m"),
        wind_dir=cur.get("winddirection_10m"),
        source_date=date.today(),
        description=desc,
    )


def _build_result(temp, humidity, dewpoint, precip, rain_prob,
                  cloud, wind, wind_dir, source_date, description=None) -> dict:
    """Assemble the standardised weather dict."""
    # Dew risk: dewpoint within 3°C of temperature → high dew likely
    dew_risk = "High" if (temp is not None and dewpoint is not None
                          and (temp - dewpoint) <= 3) else \
               "Medium" if (temp is not None and dewpoint is not None
                            and (temp - dewpoint) <= 6) else "Low"

    rain_risk = "High" if (precip and precip > 2) or (rain_prob and rain_prob > 60) else \
                "Medium" if (precip and precip > 0.5) or (rain_prob and rain_prob > 30) else "Low"

    if description is None:
        if precip and precip > 2:
            description = "Rain"
        elif cloud and cloud > 70:
            description = "Overcast"
        elif cloud and cloud > 30:
            description = "Partly cloudy"
        else:
            description = "Clear"

    return {
        "temp_c":      temp,
        "humidity_pct": humidity,
        "dewpoint_c":  dewpoint,
        "precip_mm":   precip,
        "rain_prob_pct": rain_prob,
        "cloud_pct":   cloud,
        "wind_kph":    wind,
        "wind_dir":    wind_dir,
        "description": description,
        "rain_risk":   rain_risk,
        "dew_risk":    dew_risk,
        "source_date": source_date.isoformat() if source_date else None,
    }
