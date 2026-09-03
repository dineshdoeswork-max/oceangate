import random
from datetime import datetime, timedelta, timezone
from shapely.geometry import Point, LineString
from database import SessionLocal, Vessel, Incident, SpatialData, Base, engine

# Reset tables cleanly before populating seed data
print("Resetting database tables...")
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

LOCATIONS = [
    ("Mumbai High Offshore", "Indian EEZ", 19.35, 71.35, "MT Swarna Godavari", "Crude Tanker"),
    ("JNPT Approach Channel", "Indian Territorial Waters", 18.85, 72.50, "MV MSC Mumbai", "Cargo"),
    ("Ratnagiri Coastal Offing", "Indian EEZ", 16.98, 72.95, "MT Ratna", "Chemical Tanker"),
    ("Sindhudurg Marine Zone", "Indian EEZ", 16.15, 73.18, "MV Konkan Pearl", "Bulk Carrier"),
    ("Tarapur Offshore", "Indian EEZ", 19.82, 72.35, "MT Desh Bhakta", "Crude Tanker"),
    ("Alibaug Coastal Limits", "Indian Territorial Waters", 18.60, 72.75, "MV Alibaug Express", "Cargo"),
    ("Vasai-Virar Offing", "Indian EEZ", 19.38, 72.58, "MT Surya", "Oil Products Tanker"),
    ("Murud-Janjira Approach", "Indian EEZ", 18.32, 72.80, "MV Sea Fortune", "Cargo"),
    ("Gulf of Khambhat", "Indian EEZ", 20.55, 72.05, "MT Gujarat Glory", "Crude Tanker"),
    ("Goa Maritime Boundary", "Indian EEZ", 15.52, 73.45, "MV Mandovi", "Bulk Carrier"),
    ("Mangalore Port Limits", "Indian Territorial Waters", 12.85, 74.65, "MT Nethravathi", "Chemical Tanker"),
    ("Kochi Offshore Basin", "Indian EEZ", 9.95, 75.92, "MV Kerala Star", "Container"),
    ("Chennai Coastal Zone", "Indian EEZ", 13.15, 80.45, "MT Coromandel", "Crude Tanker"),
    ("Visakhapatnam Offing", "Indian EEZ", 17.65, 83.48, "MV Vizag Pride", "Cargo"),
    ("Gulf of Kutch", "Indian EEZ", 22.55, 69.05, "MT Kutch Energy", "Oil Products Tanker"),
    ("Gulf of Mexico - Louisiana", "US EEZ", 28.55, -90.05, "MT Pelican State", "Crude Tanker"),
    ("Gulf of Mexico - Texas", "US EEZ", 27.85, -93.55, "MV Lone Star", "Bulk Carrier"),
    ("Galveston Bay Approach", "US Territorial Waters", 29.15, -94.65, "MT Houston Pride", "Chemical Tanker"),
    ("Santa Barbara Channel", "US EEZ", 34.25, -120.15, "MV Pacific Trader", "Cargo"),
    ("Prince William Sound", "US Territorial Waters", 60.65, -147.05, "MT Valdez Spirit", "Crude Tanker"),
    ("Strait of Hormuz", "Oman EEZ", 26.55, 56.25, "MT Gulf Horizon", "Crude Tanker"),
    ("Malacca Strait", "Malaysia EEZ", 2.55, 101.55, "MV Asian Pearl", "Container"),
    ("English Channel", "UK EEZ", 50.15, -1.05, "MT Channel Navigator", "Chemical Tanker"),
    ("Niger Delta Offshore", "Nigeria EEZ", 4.15, 5.55, "MT Delta Star", "Crude Tanker"),
    ("Mediterranean Sea", "Libya EEZ", 33.25, 13.25, "MV Adriatic Pioneer", "Cargo")
]

db = SessionLocal()

for idx, (loc_name, eez, lat, lon, v_name, v_type) in enumerate(LOCATIONS, start=1):
    sim_date = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 60))
    
    center = Point(lon, lat)
    poly = center.buffer(random.uniform(0.04, 0.08)) 
    track = LineString([(lon - 0.2, lat - 0.2), (lon, lat), (lon + 0.1, lat + 0.1)])
    
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
        location=loc_name, area_km2=round(random.uniform(10.5, 45.0), 1),
        length_km=round(random.uniform(15.0, 60.0), 1), eez=eez,
        status=random.choice(["Confirmed", "Under Investigation"]),
        satellite=random.choice(["Sentinel-1A", "Sentinel-1B"]),
        orbit_pass=f"Pass #{random.randint(10000, 99999)}", confidence=random.randint(82, 98)
    )
    db.add(incident)
    db.flush()

    spatial = SpatialData(
        incident_id=incident.id, geometry=poly_wkt, ship_track=track_wkt,
        center_lon=lon, center_lat=lat, ship_pos_lon=lon + 0.1, ship_pos_lat=lat + 0.1
    )
    db.add(spatial)

db.commit()
db.close()
print("Success: 3-Table Normalized Schema Populated with 25 Incidents.")