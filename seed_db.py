from database import SessionLocal, SpillIncident
from shapely.geometry import shape

RAW_SPILLS = [
    {
        "id": 1,
        "name": "Mediterranean Incident MC-2024-001",
        "date": "2024-03-15T02:47:00Z",
        "date_display": "15 March 2024   02:47 UTC",
        "location": "Mediterranean Sea, Libya Coast",
        "area_km2": 28.4,
        "length_km": 41.2,
        "eez": "International Waters (Libya EEZ border)",
        "status": "Confirmed",
        "satellite": "Sentinel-1A",
        "orbit_pass": "Ascending Pass #033541",
        "confidence": 94,
        "vessel": {
            "name": "MV Adriatic Pioneer",
            "mmsi": "247456123",
            "flag": "Panama",
            "type": "Chemical Tanker",
            "length_m": 186,
            "imo": "9512847"
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [12.85, 33.18], [12.95, 33.21], [13.10, 33.25],
                [13.28, 33.29], [13.45, 33.31], [13.60, 33.27],
                [13.58, 33.20], [13.42, 33.16], [13.25, 33.13],
                [13.08, 33.12], [12.92, 33.13], [12.85, 33.18]
            ]]
        },
        "ship_track": {
            "type": "LineString",
            "coordinates": [
                [12.10, 33.50], [12.40, 33.40],
                [12.75, 33.30], [13.20, 33.28],
                [13.65, 33.22], [14.05, 33.10]
            ]
        },
        "ship_position": [14.05, 33.10],
        "center": [13.22, 33.22]
    },
    {
        "id": 2,
        "name": "Arabian Sea Incident AS-2024-047",
        "date": "2024-07-22T17:12:00Z",
        "date_display": "22 July 2024   17:12 UTC",
        "location": "Arabian Sea, Oman Coastal Zone",
        "area_km2": 15.7,
        "length_km": 23.8,
        "eez": "Oman Exclusive Economic Zone",
        "status": "Under Investigation",
        "satellite": "Sentinel-1B",
        "orbit_pass": "Descending Pass #041892",
        "confidence": 87,
        "vessel": {
            "name": "MT Gulf Horizon",
            "mmsi": "403789456",
            "flag": "Liberia",
            "type": "Crude Oil Tanker",
            "length_m": 243,
            "imo": "9678341"
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [58.85, 22.08], [58.95, 22.13], [59.08, 22.16],
                [59.22, 22.17], [59.38, 22.14], [59.50, 22.09],
                [59.46, 22.02], [59.30, 21.99], [59.14, 21.98],
                [58.98, 22.01], [58.85, 22.08]
            ]]
        },
        "ship_track": {
            "type": "LineString",
            "coordinates": [
                [59.10, 20.75], [59.11, 21.05],
                [59.12, 21.35], [59.14, 21.65],
                [59.16, 21.95], [59.18, 22.30]
            ]
        },
        "ship_position": [59.18, 22.30],
        "center": [59.17, 22.08]
    },
    {
        "id": 3,
        "name": "Bay of Bengal Incident BB-2024-089",
        "date": "2024-08-14T09:30:00Z",
        "date_display": "14 August 2024   09:30 UTC",
        "location": "Bay of Bengal, East Coast Offing",
        "area_km2": 32.1,
        "length_km": 47.8,
        "eez": "Indian Exclusive Economic Zone",
        "status": "Confirmed",
        "satellite": "Sentinel-1A",
        "orbit_pass": "Descending Pass #045102",
        "confidence": 91,
        "vessel": {
            "name": "MT Ocean Venture",
            "mmsi": "419001234",
            "flag": "India",
            "type": "Crude Oil Tanker",
            "length_m": 274,
            "imo": "9812401"
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [85.10, 18.20], [85.25, 18.24], [85.42, 18.26],
                [85.60, 18.23], [85.58, 18.17], [85.39, 18.14],
                [85.20, 18.12], [85.10, 18.20]
            ]]
        },
        "ship_track": {
            "type": "LineString",
            "coordinates": [
                [84.70, 18.35], [85.00, 18.28], [85.35, 18.21], [85.70, 18.10]
            ]
        },
        "ship_position": [85.70, 18.10],
        "center": [85.35, 18.20]
    }
]

db = SessionLocal()
print("Connected to Supabase. Seeding records...")
for s in RAW_SPILLS:
    existing = db.query(SpillIncident).filter(SpillIncident.id == s["id"]).first()
    if existing:
        db.delete(existing)
        db.commit()

    poly_geom = f"SRID=4326;{shape(s['geometry']).wkt}"
    track_geom = f"SRID=4326;{shape(s['ship_track']).wkt}"
    
    incident = SpillIncident(
        id=s["id"], name=s["name"], date=s["date"], date_display=s["date_display"],
        location=s["location"], area_km2=s["area_km2"], length_km=s["length_km"],
        eez=s["eez"], status=s["status"], satellite=s["satellite"],
        orbit_pass=s["orbit_pass"], confidence=s["confidence"],
        vessel_name=s["vessel"]["name"], vessel_mmsi=s["vessel"]["mmsi"],
        vessel_imo=s["vessel"]["imo"], vessel_flag=s["vessel"]["flag"],
        vessel_type=s["vessel"]["type"], vessel_length_m=s["vessel"]["length_m"],
        geometry=poly_geom, ship_track=track_geom,
        center_lon=s["center"][0], center_lat=s["center"][1],
        ship_pos_lon=s["ship_position"][0], ship_pos_lat=s["ship_position"][1]
    )
    db.add(incident)

db.commit()
db.close()
print("Success: Supabase PostGIS table populated.")