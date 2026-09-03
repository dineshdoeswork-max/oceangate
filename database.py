

# So, connection stable h schema clear rakh, aur har spill ko ek traceable record banaane ka kaam kara
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from geoalchemy2 import Geometry

# Updated to use the Supabase IPv4 Session Pooler for the ap-southeast-2 region
DATABASE_URL = "postgresql://postgres.zgobwbywkzkjurcywqdu:Abkibaar150par@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class SpillIncident(Base):
    __tablename__ = "spills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    date = Column(String, nullable=False)
    date_display = Column(String, nullable=False)
    location = Column(String, nullable=False)
    area_km2 = Column(Float, nullable=False)
    length_km = Column(Float, nullable=False)
    eez = Column(String, nullable=False)
    status = Column(String, nullable=False)
    satellite = Column(String, nullable=False)
    orbit_pass = Column(String, nullable=False)
    confidence = Column(Integer, nullable=False)
    
    # Vessel Details
    vessel_name = Column(String)
    vessel_mmsi = Column(String)
    vessel_imo = Column(String)
    vessel_flag = Column(String)
    vessel_type = Column(String)
    vessel_length_m = Column(Integer)
    
    # PostGIS Spatial Geometries (WGS84 EPSG:4326)
    geometry = Column(Geometry("POLYGON", srid=4326))
    ship_track = Column(Geometry("LINESTRING", srid=4326))
    
    # Coordinates for mapping
    center_lon = Column(Float)
    center_lat = Column(Float)
    ship_pos_lon = Column(Float)
    ship_pos_lat = Column(Float)

Base.metadata.create_all(bind=engine)