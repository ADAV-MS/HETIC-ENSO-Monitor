from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from ..db import SessionLocal
from ..models import Observation, Indice, Source
from ..schemas import ObservationsResponse

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/observations", response_model=ObservationsResponse)
def get_observations(
    start: date = Query(..., description="Date de début (YYYY-MM-DD)"),
    end: date = Query(..., description="Date de fin (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    # Validation métier
    if start > end:
        raise HTTPException(
            status_code=422, 
            detail="La date de début doit être antérieure à la date de fin."
        )
    
    # Requête paramétrée
    obs = db.query(Observation).filter(
        Observation.date >= start,
        Observation.date <= end
    ).order_by(Observation.date).all()

    # Métadonnées
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