import random
import math
from datetime import datetime, timedelta, timezone
from shapely.geometry import Point, LineString, Polygon
from database import SessionLocal, Vessel, Incident, SpatialData, Base, engine

# Reset tables cleanly before populating seed data
print("Resetting database tables...")
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

def generate_realistic_ais_and_slick(lon: float, lat: float, heading_deg: float, length_km: float):
    """
    Simulates real Cerulean/SAR AIS correlation:
    - The vessel travels along its actual maritime heading (degrees).
    - An AIS track is formed by historical GPS waypoints tracing the ship's course.
    - The oil slick forms an elongated trailing plume behind the vessel along its wake,
      narrowest right at the ship's stern (fresh discharge) and widest at the tail (older, dispersed).
    """
    rad = math.radians(heading_deg)
    ux, uy = math.sin(rad), math.cos(rad) # Ship travel direction unit vector
    nx, ny = -uy, ux                      # Normal (perpendicular) unit vector
    
    # Degrees approximate conversion (1 deg lat ~ 111 km)
    len_deg = length_km / 111.0
    half_l = len_deg * 0.5
    
    # Current vessel position (at the head of the track)
    ship_lon = lon + half_l * ux
    ship_lat = lat + half_l * uy
    
    # AIS track waypoints going backwards along course with slight natural nautical curvature
    w_start = (lon - half_l * ux, lat - half_l * uy)
    w_mid1  = (lon - half_l * 0.35 * ux + 0.004 * nx, lat - half_l * 0.35 * uy + 0.004 * ny)
    w_mid2  = (lon + half_l * 0.35 * ux - 0.002 * nx, lat + half_l * 0.35 * uy - 0.002 * ny)
    w_ship  = (ship_lon, ship_lat)
    
    track = LineString([w_start, w_mid1, w_mid2, w_ship])
    
    # Trailing oil slick polygon trailing behind vessel
    w_head = (ship_lon - 0.015 * ux, ship_lat - 0.015 * uy)
    tail_w = random.uniform(0.012, 0.018) # dispersed tail width
    mid_w  = tail_w * 0.65
    head_w = 0.0035                       # fresh discharge width near vessel
    
    p_tail_tip = (w_start[0] - 0.01 * ux, w_start[1] - 0.01 * uy)
    p_tail_l   = (w_start[0] + tail_w * nx, w_start[1] + tail_w * ny)
    p_mid_l    = (lon + mid_w * nx, lat + mid_w * ny)
    p_head_l   = (w_head[0] + head_w * nx, w_head[1] + head_w * ny)
    p_head_r   = (w_head[0] - head_w * nx, w_head[1] - head_w * ny)
    p_mid_r    = (lon - mid_w * nx, lat - mid_w * ny)
    p_tail_r   = (w_start[0] - tail_w * nx, w_start[1] - tail_w * ny)
    
    poly = Polygon([p_tail_tip, p_tail_l, p_mid_l, p_head_l, w_head, p_head_r, p_mid_r, p_tail_r, p_tail_tip])
    poly = poly.buffer(0.002) # smooth realistic SAR backscatter boundary
    
    return track, poly, ship_lon, ship_lat

# Realistic maritime heading angles corresponding to real-world shipping channels & TSS routes
LOCATIONS = [
    ("Mumbai High Offshore", "Indian EEZ", 19.35, 71.35, "MT Swarna Godavari", "Crude Tanker", 325),
    ("JNPT Approach Channel", "Indian Territorial Waters", 18.85, 72.50, "MV MSC Mumbai", "Cargo", 75),
    ("Ratnagiri Coastal Offing", "Indian EEZ", 16.98, 72.95, "MT Ratna", "Chemical Tanker", 165),
    ("Sindhudurg Marine Zone", "Indian EEZ", 16.15, 73.18, "MV Konkan Pearl", "Bulk Carrier", 345),
    ("Tarapur Offshore", "Indian EEZ", 19.82, 72.35, "MT Desh Bhakta", "Crude Tanker", 190),
    ("Alibaug Coastal Limits", "Indian Territorial Waters", 18.60, 72.75, "MV Alibaug Express", "Cargo", 280),
    ("Vasai-Virar Offing", "Indian EEZ", 19.38, 72.58, "MT Surya", "Oil Products Tanker", 215),
    ("Murud-Janjira Approach", "Indian EEZ", 18.32, 72.80, "MV Sea Fortune", "Cargo", 150),
    ("Gulf of Khambhat", "Indian EEZ", 20.55, 72.05, "MT Gujarat Glory", "Crude Tanker", 25),
    ("Goa Maritime Boundary", "Indian EEZ", 15.52, 73.45, "MV Mandovi", "Bulk Carrier", 250),
    ("Mangalore Port Limits", "Indian Territorial Waters", 12.85, 74.65, "MT Nethravathi", "Chemical Tanker", 105),
    ("Kochi Offshore Basin", "Indian EEZ", 9.95, 75.92, "MV Kerala Star", "Container", 135),
    ("Chennai Coastal Zone", "Indian EEZ", 13.15, 80.45, "MT Coromandel", "Crude Tanker", 15),
    ("Visakhapatnam Offing", "Indian EEZ", 17.65, 83.48, "MV Vizag Pride", "Cargo", 50),
    ("Gulf of Kutch", "Indian EEZ", 22.55, 69.05, "MT Kutch Energy", "Oil Products Tanker", 85),
    ("Gulf of Mexico - Louisiana", "US EEZ", 28.55, -90.05, "MT Pelican State", "Crude Tanker", 145),
    ("Gulf of Mexico - Texas", "US EEZ", 27.85, -93.55, "MV Lone Star", "Bulk Carrier", 70),
    ("Galveston Bay Approach", "US Territorial Waters", 29.15, -94.65, "MT Houston Pride", "Chemical Tanker", 315),
    ("Santa Barbara Channel", "US EEZ", 34.25, -120.15, "MV Pacific Trader", "Cargo", 120),
    ("Prince William Sound", "US Territorial Waters", 60.65, -147.05, "MT Valdez Spirit", "Crude Tanker", 210),
    ("Strait of Hormuz", "Oman EEZ", 26.55, 56.25, "MT Gulf Horizon", "Crude Tanker", 125),
    ("Malacca Strait", "Malaysia EEZ", 2.55, 101.55, "MV Asian Pearl", "Container", 130),
    ("English Channel", "UK EEZ", 50.15, -1.05, "MT Channel Navigator", "Chemical Tanker", 245),
    ("Niger Delta Offshore", "Nigeria EEZ", 4.15, 5.55, "MT Delta Star", "Crude Tanker", 205),
    ("Mediterranean Sea", "Libya EEZ", 33.25, 13.25, "MV Adriatic Pioneer", "Cargo", 310)
]

db = SessionLocal()

for idx, (loc_name, eez, lat, lon, v_name, v_type, heading) in enumerate(LOCATIONS, start=1):
    sim_date = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 60))
    length_km = round(random.uniform(15.0, 55.0), 1)
    area_km2 = round(random.uniform(10.5, 45.0), 1)
    
    # Generate realistic course-aligned track and trailing slick
    track, poly, ship_lon, ship_lat = generate_realistic_ais_and_slick(lon, lat, heading, length_km)
    
    poly_wkt = f"SRID=4326;{poly.wkt}"
    track_wkt = f"SRID=4326;{track.wkt}"

    vessel = Vessel(
        name=v_name, mmsi=str(random.randint(200000000, 499999999)),
        imo=str(random.randint(9000000, 9999999)), flag=random.choice(["India", "Panama", "Liberia", "Marshall Islands"]),
        vessel_type=v_type, length_m=random.randint(120, 300)
    )
    db.add(vessel)
    db.flush() 

    incident = Incident(
        vessel_id=vessel.id, name=f"{loc_name.split()[0].upper()} INC-{idx:03d}",
        date=sim_date.strftime("%Y-%m-%dT%H:%M:%SZ"), date_display=sim_date.strftime("%d %B %Y   %H:%M UTC"),
        location=loc_name, area_km2=area_km2,
        length_km=length_km, eez=eez,
        status=random.choice(["Confirmed", "Under Investigation"]),
        satellite=random.choice(["Sentinel-1A", "Sentinel-1B"]),
        orbit_pass=f"Pass #{random.randint(10000, 99999)}", confidence=random.randint(82, 98)
    )
    db.add(incident)
    db.flush()

    spatial = SpatialData(
        incident_id=incident.id, geometry=poly_wkt, ship_track=track_wkt,
        center_lon=lon, center_lat=lat, ship_pos_lon=ship_lon, ship_pos_lat=ship_lat
    )
    db.add(spatial)

db.commit()
db.close()
print("Success: 3-Table Normalized Schema Populated with 25 Incidents (Realistic AIS Tracks & Slicks).")