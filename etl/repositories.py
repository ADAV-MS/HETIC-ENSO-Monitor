"""Accès aux données de l'ETL ONI.

Ces fonctions utilisent la session fournie par le service ETL : elles ne
valident jamais la transaction et ne ferment jamais la session.
"""

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.models import Import, Indice, Observation, Source


def obtenir_ou_creer_source(db: Session, extracted_at: datetime | None = None) -> Source:
    """Retourne la source NOAA et actualise sa derniere extraction ETL connue."""
    if extracted_at is None:
        extracted_at = datetime.now(UTC)
    source = db.query(Source).filter_by(name="NOAA CPC").first()
    if source is None:
        source = Source(
            name="NOAA CPC",
            url="https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt",
            version="v6",
            extracted_at=extracted_at,
        )
        db.add(source)
        db.flush()  # Genere l'ID sans valider la transaction.
    else:
        # Cette date correspond a la DERNIERE lecture du fichier. Les snapshots
        # historiques sont conserves sur Import.extracted_at.
        source.extracted_at = extracted_at
    return source


def obtenir_ou_creer_indice(db: Session) -> Indice:
    """Récupère la définition ONI ou la crée si elle est absente."""
    indice = db.query(Indice).filter_by(code="ONI").first()
    if indice is None:
        indice = Indice(code="ONI", label="Oceanic Niño Index", unit="°C anomaly")
        db.add(indice)
        db.flush()
    return indice


def enregistrer_import(
    db: Session,
    source_id: int,
    row_count: int,
    checksum: str,
    extracted_at: datetime | None = None,
) -> Import:
    """Enregistre une execution avec son checksum et sa date d'extraction ETL."""
    import_record = Import(
        source_id=source_id,
        row_count=row_count,
        checksum=checksum,
        extracted_at=extracted_at,
    )
    db.add(import_record)
    db.flush()  # L'ID est necessaire pour lier les observations.
    return import_record


def obtenir_observation(db: Session, indice_id: int, obs_date: date) -> Observation | None:
    """Trouve l'observation courante par sa cle naturelle (indice, date)."""
    return db.query(Observation).filter_by(index_id=indice_id, date=obs_date).first()


def observation_existe(db: Session, indice_id: int, obs_date: date) -> bool:
    """Compatibilite avec les tests des issues precedentes."""
    return obtenir_observation(db, indice_id, obs_date) is not None


def mettre_a_jour_observation(
    observation: Observation, *, import_id: int, value: float
) -> None:
    """Applique une revision NOAA sans creer un doublon (indice, date)."""
    observation.value = value
    observation.import_id = import_id


def ajouter_observation(
    db: Session, *, import_id: int, indice_id: int, obs_date: date, value: float
) -> None:
    """Prépare une observation pour la transaction en cours."""
    db.add(
        Observation(import_id=import_id, index_id=indice_id, date=obs_date, value=value)
    )
