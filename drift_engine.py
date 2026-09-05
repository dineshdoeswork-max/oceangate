"""
drift_engine.py — Real-time Oil Spill Drift & Hindcast Engine.

Data Sources (Open-Meteo Free APIs, No Key / No Signup Needed):
1. Marine API: Ocean current velocity (m/s) & direction (deg)
   https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&hourly=ocean_current_velocity,ocean_current_direction
2. Forecast API: 10m Wind speed (km/h -> m/s) & direction (deg)
   https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=windspeed_10m,winddirection_10m

Drift & Leeway Physics Formulation:
----------------------------------
Total Drift Vector:
  U_total = U_current + (0.03 * U_wind)

Coriolis Deflection:
  - North of Equator (lat >= 0): Wind component rotated +20° clockwise.
  - South of Equator (lat < 0):  Wind component rotated -20° counterclockwise.

Projection & Spreading:
  - Vector addition of current + leeway to integrate hourly displacement.
  - Forward forecast: predicts future trajectory (+24h, +48h).
  - Backward hindcast: traces back where oil slick originated for vessel attribution.
  - Viscous turbulent expansion buffer based on elapsed hours.
"""

from __future__ import annotations

import json
import logging
import math
import urllib.request
from functools import lru_cache
from typing import List, Tuple

from shapely.affinity import translate
from shapely.geometry import Polygon, mapping

logger = logging.getLogger(__name__)

KM2_PER_DEG2 = 12_321.0  # (111 km/deg)^2 conversion


def _centroid_of(polygon_coords: list) -> Tuple[float, float]:
    """Return (lon, lat) centroid of a polygon given as a list of coordinate pairs."""
    poly = Polygon(polygon_coords)
    return poly.centroid.x, poly.centroid.y


@lru_cache(maxsize=128)
def _fetch_openmeteo_feeds(round_lat: float, round_lon: float) -> Tuple[dict, dict]:
    """
    Query Open-Meteo Marine API and Weather Forecast API for live current and wind vectors.
    Cached by 1 decimal place coordinate (~11 km grid resolution).
    """
    marine_url = (
        f"https://marine-api.open-meteo.com/v1/marine?"
        f"latitude={round_lat}&longitude={round_lon}&"
        f"hourly=ocean_current_velocity,ocean_current_direction"
    )
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={round_lat}&longitude={round_lon}&"
        f"hourly=windspeed_10m,winddirection_10m"
    )
    headers = {"User-Agent": "MiniCerulean-DriftEngine/2.0"}

    try:
        req_m = urllib.request.Request(marine_url, headers=headers)
        with urllib.request.urlopen(req_m, timeout=4) as resp_m:
            marine_data = json.loads(resp_m.read().decode())
    except Exception as exc:
        logger.warning("Marine API fetch failed for (%s, %s): %s", round_lat, round_lon, exc)
        marine_data = {}

    try:
        req_w = urllib.request.Request(weather_url, headers=headers)
        with urllib.request.urlopen(req_w, timeout=4) as resp_w:
            weather_data = json.loads(resp_w.read().decode())
    except Exception as exc:
        logger.warning("Weather API fetch failed for (%s, %s): %s", round_lat, round_lon, exc)
        weather_data = {}

    return marine_data.get("hourly", {}), weather_data.get("hourly", {})


def compute_hourly_drift_vector(
    lat: float, lon: float, hour_offset: int = 0
) -> Tuple[float, float, float, float, float, float]:
    """
    Calculates total drift velocity vector (u_x, u_y) in m/s:
      u_x = c_x + w_x
      u_y = c_y + w_y

    Where:
      - Current vector (c_x, c_y):
          c_x = c_speed * sin(rad(c_dir))
          c_y = c_speed * cos(rad(c_dir))
      - Wind leeway vector (w_x, w_y):
          leeway = 0.03 * w_speed
          rot_angle = +20 deg (lat >= 0) or -20 deg (lat < 0)
          w_x = leeway * sin(rad(w_dir + rot_angle))
          w_y = leeway * cos(rad(w_dir + rot_angle))

    Returns:
      (u_x, u_y, current_speed, current_dir, wind_speed, wind_dir)
    """
    r_lat = round(lat, 1)
    r_lon = round(lon, 1)

    m_hourly, w_hourly = _fetch_openmeteo_feeds(r_lat, r_lon)

    c_vel_list = m_hourly.get("ocean_current_velocity", [])
    c_dir_list = m_hourly.get("ocean_current_direction", [])
    w_spd_list = w_hourly.get("windspeed_10m", [])
    w_dir_list = w_hourly.get("winddirection_10m", [])

    idx = min(max(0, hour_offset), len(c_vel_list) - 1) if c_vel_list else 0

    # Ocean current: velocity in m/s, direction in degrees
    if c_vel_list and c_vel_list[idx] is not None:
        c_speed = float(c_vel_list[idx])
    else:
        c_speed = 0.25  # climatological fallback ~0.5 knots

    if c_dir_list and c_dir_list[idx] is not None:
        c_dir = float(c_dir_list[idx])
    else:
        c_dir = 45.0

    # Wind speed from Open-Meteo is km/h -> convert to m/s
    if w_spd_list and w_spd_list[idx] is not None:
        w_speed_ms = float(w_spd_list[idx]) / 3.6
    else:
        w_speed_ms = 5.0  # ~10 knots

    if w_dir_list and w_dir_list[idx] is not None:
        w_dir = float(w_dir_list[idx])
    else:
        w_dir = 225.0

    # 1. Ocean current vector
    c_rad = math.radians(c_dir)
    c_x = c_speed * math.sin(c_rad)
    c_y = c_speed * math.cos(c_rad)

    # 2. Wind leeway (3%) + Coriolis rotation (+20° NH, -20° SH)
    leeway_speed = 0.03 * w_speed_ms
    coriolis_deflection = 20.0 if lat >= 0 else -20.0
    drift_w_dir = (w_dir + coriolis_deflection) % 360.0

    w_rad = math.radians(drift_w_dir)
    w_x = leeway_speed * math.sin(w_rad)
    w_y = leeway_speed * math.cos(w_rad)

    # Total drift vector
    u_x = c_x + w_x
    u_y = c_y + w_y

    return u_x, u_y, c_speed, c_dir, w_speed_ms, w_dir


def get_current_metocean(lat: float, lon: float) -> dict:
    """
    Returns live oceanographic and atmospheric vectors for a specific coordinate:
    - Ocean Current Velocity (m/s & knots) and Direction (deg)
    - Surface Wind Speed (m/s & km/h) and Direction (deg)
    - Net Drift Speed (m/s & knots) and Heading (deg)
    """
    u_x, u_y, c_speed, c_dir, w_speed_ms, w_dir = compute_hourly_drift_vector(lat, lon, hour_offset=0)
    drift_speed = math.sqrt(u_x * u_x + u_y * u_y)
    drift_dir = (math.degrees(math.atan2(u_x, u_y)) + 360.0) % 360.0

    return {
        "ocean_current": {
            "velocity_ms": round(c_speed, 2),
            "velocity_knots": round(c_speed * 1.94384, 2),
            "direction_deg": round(c_dir, 1),
        },
        "wind": {
            "speed_ms": round(w_speed_ms, 2),
            "speed_kmh": round(w_speed_ms * 3.6, 1),
            "direction_deg": round(w_dir, 1),
        },
        "net_drift": {
            "speed_ms": round(drift_speed, 2),
            "speed_knots": round(drift_speed * 1.94384, 2),
            "direction_deg": round(drift_dir, 1),
        }
    }


def simulate_drift(
    polygon_coords: list,
    hours: list = None,
    mode: str = "forecast",
) -> List[dict]:
    """
    Computes oil slick drift using live Open-Meteo ocean currents and 10m wind.

    Parameters:
      polygon_coords : list of (lon, lat) tuples defining the detected slick.
      hours : list of forecast intervals, e.g. [24, 48].
      mode : 'forecast' (forward in time) or 'hindcast' (backward in time for origin attribution).

    Returns:
      List of dicts matching the API contract expected by app.py and map.js:
      {
          "forecast_hour": int,
          "region": str,
          "projected_area_km2": float,
          "geometry": dict  # GeoJSON mapping
      }
    """
    if hours is None:
        hours = [24, 48]

    hours = sorted(set(hours))
    center_lon, center_lat = _centroid_of(polygon_coords)
    base_poly = Polygon(polygon_coords)

    sign = -1.0 if mode == "hindcast" else 1.0
    forecasts = []

    # Step hour by hour to integrate displacement
    cumulative_dx = 0.0  # meters
    cumulative_dy = 0.0  # meters

    max_h = max(hours)
    step_displacements = {}

    for step in range(1, max_h + 1):
        ux, uy, _, _, _, _ = compute_hourly_drift_vector(
            center_lat, center_lon, hour_offset=step - 1
        )
        cumulative_dx += sign * ux * 3600.0
        cumulative_dy += sign * uy * 3600.0

        if step in hours:
            step_displacements[step] = (cumulative_dx, cumulative_dy)

    for h in hours:
        dx, dy = step_displacements.get(h, (cumulative_dx, cumulative_dy))

        # Convert meters displacement to degrees lat/lon
        d_lat = dy / 111_320.0
        cos_lat = math.cos(math.radians(center_lat))
        d_lon = dx / (111_320.0 * (cos_lat if abs(cos_lat) > 0.01 else 1.0))

        # Translate slick polygon along trajectory
        shifted = translate(base_poly, xoff=d_lon, yoff=d_lat)

        # Turbulent diffusion & spreading (Fay's gravity-viscous regime expansion)
        spread_deg = 0.005 * math.pow(h / 12.0, 0.6)
        diffused = shifted.buffer(spread_deg)

        # Surface area expansion over time
        area_growth = 1.0 + 0.16 * math.pow(h, 0.62)
        projected_area = round(base_poly.area * KM2_PER_DEG2 * area_growth, 2)

        mode_title = "Hindcast" if mode == "hindcast" else "Forecast"
        forecasts.append({
            "forecast_hour": h,
            "region": f"Live Open-Meteo Current + Wind ({mode_title})",
            "projected_area_km2": projected_area,
            "geometry": mapping(diffused),
        })

    return forecasts


def _physics_fallback(polygon_coords: list, hours: list) -> List[dict]:
    """Safety fallback returning same schema if network is completely disabled."""
    return simulate_drift(polygon_coords, hours, mode="forecast")
