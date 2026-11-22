from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.orm import Session, joinedload

from ..db import SessionLocal
from ..models import Import, Observation
from ..schemas import ObservationFilter, ObservationsResponse

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
):
    # Précharge la source de chaque import et l'indice de chaque observation.
    # Sans cela, des requêtes supplémentaires seraient déclenchées pour chaque ligne.
    observations = (
        db.query(Observation)
        .options(
            joinedload(Observation.import_record).joinedload(Import.source),
            joinedload(Observation.indice),
        )
        .filter(
            Observation.date >= filters.start,
            Observation.date <= filters.end,
        )
        .order_by(Observation.date, Observation.id)
        .all()
    )

    resultats = []
    couples_source_indice = set()

    for observation in observations:
        import_record = observation.import_record
        source = import_record.source
        indice = observation.indice
        couples_source_indice.add((source.id, indice.id))

        resultats.append({
            "date": observation.date,
            "value": observation.value,
            "provenance": {
                "source_id": source.id,
                "source": source.name,
                "source_url": source.url,
                "version": source.version,
                "extracted_at": source.extracted_at,
                "import_id": import_record.id,
                "imported_at": import_record.imported_at,
                "indice_code": indice.code,
                "indice": indice.label,
                "unit": indice.unit,
            },
        })

    # Les métadonnées au niveau de la réponse ne sont renseignées que
    # lorsqu'une seule source et un seul indice couvrent toute la période.
    # Pour une période vide ou mixte, elles restent nulles plutôt que fausses.
    metadata = resultats[0]["provenance"] if len(couples_source_indice) == 1 else None

    return {
        "source": metadata["source"] if metadata else None,
        "indice": metadata["indice"] if metadata else None,
        "unit": metadata["unit"] if metadata else None,
        "version": metadata["version"] if metadata else None,
        "extracted_at": metadata["extracted_at"] if metadata else None,
        "observations": resultats,
    }