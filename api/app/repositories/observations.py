"""SQLAlchemy reads for observations and their provenance."""

from datetime import date

from sqlalchemy.orm import Session, joinedload

from ..models import Import, Observation


def lister_observations(db: Session, debut: date, fin: date) -> list[Observation]:
    """List chronological observations with their provenance preloaded."""
    return (
        db.query(Observation)
        .options(
            joinedload(Observation.import_record).joinedload(Import.source),
            joinedload(Observation.indice),
        )
        .filter(
            Observation.date >= debut,
            Observation.date <= fin,
        )
        .order_by(Observation.date, Observation.id)
        .all()
    )
