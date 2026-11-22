from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..schemas import ObservationFilter, ObservationsResponse
from ..services.observations import construire_reponse_observations

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
    db: Session = Depends(get_db),
) -> ObservationsResponse:
    return construire_reponse_observations(db, filters)
