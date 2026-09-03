import math
from shapely.geometry import Polygon, mapping
from shapely.affinity import translate

def get_regional_physics(lon: float, lat: float):
    """Assigns rough regional current and wind vectors based on global coordinates."""
    if 50 < lon < 80 and 0 < lat < 25:
        # Arabian Sea / West India (Monsoon winds, strong current)
        return {"c_speed": 0.35, "c_angle": 160, "w_speed": 9.2, "w_angle": 135}
    elif 80 <= lon < 100 and 5 < lat < 25:
        # Bay of Bengal
        return {"c_speed": 0.28, "c_angle": 210, "w_speed": 7.5, "w_angle": 180}
    elif -10 < lon < 40 and 30 < lat < 45:
        # Mediterranean Sea (Weaker, complex currents)
        return {"c_speed": 0.15, "c_angle": 90, "w_speed": 5.0, "w_angle": 110}
    else:
        # Global Default Average
        return {"c_speed": 0.20, "c_angle": 180, "w_speed": 6.0, "w_angle": 180}

def simulate_drift(polygon_coords: list, hours: list = [12, 24, 48]):
    base_poly = Polygon(polygon_coords)
    center_lon, center_lat = base_poly.centroid.x, base_poly.centroid.y
    
    physics = get_regional_physics(center_lon, center_lat)
    
    c_rad = math.radians(physics["c_angle"])
    w_rad = math.radians(physics["w_angle"])

    u_drift_x = physics["c_speed"] * math.sin(c_rad) + 0.03 * physics["w_speed"] * math.sin(w_rad)
    u_drift_y = physics["c_speed"] * math.cos(c_rad) + 0.03 * physics["w_speed"] * math.cos(w_rad)

    forecasts = []
    for t in hours:
        displacement_x = u_drift_x * (t * 3600)
        displacement_y = u_drift_y * (t * 3600)

        delta_lat = displacement_y / 111320.0
        delta_lon = displacement_x / (111320.0 * math.cos(math.radians(center_lat)))

        shifted_poly = translate(base_poly, xoff=delta_lon, yoff=delta_lat)
        diffused_poly = shifted_poly.buffer(0.008 * (t / 12.0))

        forecasts.append({
            "forecast_hour": t,
            "projected_area_km2": round(base_poly.area * 12300 * (1 + (t * 0.02)), 2),
            "geometry": mapping(diffused_poly)
        })

    return forecasts