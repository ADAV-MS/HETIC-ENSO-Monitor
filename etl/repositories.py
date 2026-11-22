"""Accès aux données de l'ETL ONI.

Ces fonctions utilisent la session fournie par le service ETL : elles ne
valident jamais la transaction et ne ferment jamais la session.
"""

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.models import Import, Indice, Observation, Source


def obtenir_ou_creer_source(db: Session) -> Source:
    """Récupère la source NOAA CPC ou la crée si elle est absente."""
    source = db.query(Source).filter_by(name="NOAA CPC").first()
    if source is None:
        source = Source(
            name="NOAA CPC",
            url="https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt",
            version="v6",
            extracted_at=datetime.now(UTC),
        )
        db.add(source)
        db.flush()  # Génère l'ID sans valider la transaction.
    return source


def obtenir_ou_creer_indice(db: Session) -> Indice:
    """Récupère la définition ONI ou la crée si elle est absente."""
    indice = db.query(Indice).filter_by(code="ONI").first()
    if indice is None:
        indice = Indice(code="ONI", label="Oceanic Niño Index", unit="°C anomaly")
        db.add(indice)
        db.flush()
    return indice


def enregistrer_import(db: Session, source_id: int, row_count: int, checksum: str) -> Import:
    """Crée une trace d'import liée à la source."""
    import_record = Import(source_id=source_id, row_count=row_count, checksum=checksum)
    db.add(import_record)
    db.flush()  # L'ID est nécessaire pour lier les observations.
    return import_record


def observation_existe(db: Session, indice_id: int, obs_date: date) -> bool:
    """Détecte une observation déjà présente pour l'indice et la date."""
    return db.query(Observation).filter_by(index_id=indice_id, date=obs_date).first() is not None


def ajouter_observation(
    db: Session, *, import_id: int, indice_id: int, obs_date: date, value: float
) -> None:
    """Prépare une observation pour la transaction en cours."""
    db.add(
        Observation(import_id=import_id, index_id=indice_id, date=obs_date, value=value)
    )
