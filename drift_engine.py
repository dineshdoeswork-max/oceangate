import math
from shapely.geometry import Polygon, mapping
from shapely.affinity import translate

def simulate_drift(polygon_coords: list, hours: list = [12, 24, 48]):
    # West India Coastal Current vector + Monsoon Wind component
    current_speed = 0.35
    current_angle = math.radians(160)
    wind_speed = 9.2
    wind_angle = math.radians(135)

    u_drift_x = current_speed * math.sin(current_angle) + 0.03 * wind_speed * math.sin(wind_angle)
    u_drift_y = current_speed * math.cos(current_angle) + 0.03 * wind_speed * math.cos(wind_angle)

    base_poly = Polygon(polygon_coords)
    forecasts = []

    for t in hours:
        displacement_x = u_drift_x * (t * 3600)
        displacement_y = u_drift_y * (t * 3600)

        delta_lat = displacement_y / 111320.0
        mean_lat = base_poly.centroid.y
        delta_lon = displacement_x / (111320.0 * math.cos(math.radians(mean_lat)))

        shifted_poly = translate(base_poly, xoff=delta_lon, yoff=delta_lat)
        diffused_poly = shifted_poly.buffer(0.008 * (t / 12.0))

        forecasts.append({
            "forecast_hour": t,
            "projected_area_km2": round(base_poly.area * 12300 * (1 + (t * 0.02)), 2),
            "geometry": mapping(diffused_poly)
        })

    return forecasts