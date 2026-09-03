import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping

from database import SessionLocal, Vessel, Incident, SpatialData
from drift_engine import simulate_drift
from pdf_generator import generate_icg_report

app = FastAPI(title="Foldcraft - Marine Protection Gang")

def format_spill(inc: Incident):
    geom = mapping(to_shape(inc.spatial_data.geometry))
    track = mapping(to_shape(inc.spatial_data.ship_track))
    
    return {
        "id": inc.id,
        "name": inc.name,
        "date": inc.date,
        "date_display": inc.date_display,
        "location": inc.location,
        "area_km2": inc.area_km2,
        "length_km": inc.length_km,
        "eez": inc.eez,
        "status": inc.status,
        "satellite": inc.satellite,
        "orbit_pass": inc.orbit_pass,
        "confidence": inc.confidence,
        "vessel": {
            "name": inc.vessel.name,
            "mmsi": inc.vessel.mmsi,
            "imo": inc.vessel.imo,
            "flag": inc.vessel.flag,
            "type": inc.vessel.vessel_type,
            "length_m": inc.vessel.length_m
        },
        "geometry": geom,
        "ship_track": track,
        "ship_position": [inc.spatial_data.ship_pos_lon, inc.spatial_data.ship_pos_lat],
        "center": [inc.spatial_data.center_lon, inc.spatial_data.center_lat]
    }

@app.get("/api/spills")
def get_spills():
    db = SessionLocal()
    incidents = db.query(Incident).all()
    formatted = [format_spill(inc) for inc in incidents]
    db.close()
    
    formatted.sort(key=lambda x: x['date'], reverse=True)
    return {"spills": formatted, "total": len(formatted)}

@app.get("/api/spills/{spill_id}")
def get_spill(spill_id: int):
    db = SessionLocal()
    inc = db.query(Incident).filter(Incident.id == spill_id).first()
    db.close()
    if not inc:
        return JSONResponse(status_code=404, content={"error": "Spill not found"})
    return format_spill(inc)

@app.get("/api/stats")
def get_stats():
    db = SessionLocal()
    incidents = db.query(Incident).all()
    db.close()
    if not incidents:
        return {"total_spills": 0, "total_area_km2": 0, "total_length_km": 0, "avg_confidence": 0}
    
    total_area = sum(i.area_km2 for i in incidents)
    avg_conf = sum(i.confidence for i in incidents) / len(incidents)
    return {
        "total_spills": len(incidents),
        "total_area_km2": round(total_area, 1),
        "total_length_km": round(sum(i.length_km for i in incidents), 1),
        "avg_confidence": round(avg_conf, 1),
        "satellites_used": list(set(i.satellite for i in incidents)),
        "eezs_affected": [i.eez for i in incidents]
    }

@app.get("/api/spills/{spill_id}/trajectory")
def get_trajectory(spill_id: int):
    db = SessionLocal()
    inc = db.query(Incident).filter(Incident.id == spill_id).first()
    if not inc:
        db.close()
        raise HTTPException(status_code=404, detail="Spill incident not found")
    
    geom = mapping(to_shape(inc.spatial_data.geometry))
    db.close()
    
    coords = geom["coordinates"][0]
    forecasts = simulate_drift(coords, hours=[12, 24, 48])
    return {"spill_id": spill_id, "forecasts": forecasts}

@app.get("/api/spills/{spill_id}/report")
def get_report(spill_id: int):
    db = SessionLocal()
    inc = db.query(Incident).filter(Incident.id == spill_id).first()
    db.close()
    if not inc:
        raise HTTPException(status_code=404, detail="Spill incident not found")
    
    pdf_buffer = generate_icg_report(format_spill(inc))
    filename = f"ICG_Dossier_INC_{inc.id:03d}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/")
def get_landing():
    return FileResponse(os.path.join("static", "index.html"))

@app.get("/map")
def get_map():
    return FileResponse(os.path.join("static", "map.html"))

app.mount("/", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)