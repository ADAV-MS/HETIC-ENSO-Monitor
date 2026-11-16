from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.orm import Session
from datetime import date
from ..db import SessionLocal
from ..models import Observation, Indice, Source
from ..schemas import ObservationsResponse, ObservationFilter

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_filters(
    start: date = Query(..., description="Date de début (YYYY-MM-DD)"),
    end: date = Query(..., description="Date de fin (YYYY-MM-DD)"),
) -> ObservationFilter:
    try:
        return ObservationFilter(start=start, end=end)
    except ValidationError as e:
        error_msg = e.errors()[0]["msg"]
        raise HTTPException(status_code=422, detail=error_msg)

@router.get("/observations", response_model=ObservationsResponse)
def get_observations(
    filters: ObservationFilter = Depends(get_filters),
    db: Session = Depends(get_db)
):
    obs = db.query(Observation).filter(
        Observation.date >= filters.start,
        Observation.date <= filters.end
    ).order_by(Observation.date).all()

    indice = db.query(Indice).first()
    source = db.query(Source).first()

    return {
        "source": source.name if source else "Inconnue",
        "indice": indice.label if indice else "ONI",
        "unit": indice.unit if indice else "°C",
        "version": source.version if source else "N/A",
        "extracted_at": source.extracted_at if source else None,
        "observations": obs
    }