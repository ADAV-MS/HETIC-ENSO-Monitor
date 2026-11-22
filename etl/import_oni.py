import sys
import os
import hashlib
import pandas as pd
from datetime import datetime, UTC, date

# Lien avec l'API pour utiliser les mêmes modèles
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'api')))
from app.db import SessionLocal
from app.models import Source, Indice, Import, Observation

SEASON_TO_MONTH = {
    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12
}


def convertir_saison_en_date(season: str, year: int):
    """Transforme une saison (ex: DJF) et une année en date (ex: 1950-01-01)."""
    month = SEASON_TO_MONTH.get(season)
    if not month:
        return None
    return datetime(year, month, 1).date()


def calculer_checksum(filepath: str) -> str:
    """Calcule l'empreinte SHA-256 du fichier source NOAA."""
    with open(filepath, "rb") as fichier:
        return hashlib.sha256(fichier.read()).hexdigest()


def lire_donnees_oni(filepath: str) -> pd.DataFrame:
    """Lit les observations NOAA séparées par des espaces."""
    return pd.read_csv(filepath, sep=r"\s+")


def obtenir_ou_creer_source(db) -> Source:
    """Récupère la source NOAA CPC ou l'enregistre si elle est absente."""
    source = db.query(Source).filter_by(name="NOAA CPC").first()
    if not source:
        source = Source(
            name="NOAA CPC",
            url="https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt",
            version="v6",
            extracted_at=datetime.now(UTC),
        )
        db.add(source)
        db.flush()  # Attribue l'ID sans valider la transaction.
    return source


def obtenir_ou_creer_indice(db) -> Indice:
    """Récupère la définition de l'indice ONI ou la crée."""
    indice = db.query(Indice).filter_by(code="ONI").first()
    if not indice:
        indice = Indice(code="ONI", label="Oceanic Niño Index", unit="°C anomaly")
        db.add(indice)
        db.flush()  # Attribue l'ID sans valider la transaction.
    return indice


def enregistrer_import(db, source_id: int, row_count: int, checksum: str) -> Import:
    """Enregistre la traçabilité de l'import, avant les observations."""
    import_record = Import(source_id=source_id, row_count=row_count, checksum=checksum)
    db.add(import_record)
    db.flush()  # L'ID est nécessaire pour associer les observations.
    return import_record


def transformer_ligne(row: pd.Series) -> tuple[date, float] | None:
    """Transforme une ligne NOAA en date et anomalie, ou l'ignore si la saison est inconnue."""
    season = row["SEAS"]
    year = int(row["YR"])
    value = float(row["ANOM"])
    obs_date = convertir_saison_en_date(season, year)
    if obs_date is None:
        return None
    return obs_date, value


def enregistrer_observations(db, df: pd.DataFrame, indice_id: int, import_id: int) -> tuple[int, int]:
    """Insère les observations inédites et compte les doublons ignorés."""
    inserted = 0
    skipped = 0

    for _, row in df.iterrows():
        observation = transformer_ligne(row)
        if observation is None:
            continue

        obs_date, value = observation
        exists = db.query(Observation).filter_by(index_id=indice_id, date=obs_date).first()
        if exists:
            skipped += 1
            continue

        db.add(Observation(import_id=import_id, index_id=indice_id, date=obs_date, value=value))
        inserted += 1

    return inserted, skipped


def main(filepath: str = "/app/data/oni.data") -> None:
    """Orchestre la lecture, la transformation et la persistance de l'import ONI."""
    checksum = calculer_checksum(filepath)
    df = lire_donnees_oni(filepath)
    row_count = len(df)

    db = SessionLocal()
    try:
        source = obtenir_ou_creer_source(db)
        indice = obtenir_ou_creer_indice(db)
        import_record = enregistrer_import(db, source.id, row_count, checksum)
        inserted, skipped = enregistrer_observations(db, df, indice.id, import_record.id)
        db.commit()  # Une seule validation pour toutes les écritures.
    except Exception:
        db.rollback()  # Annule aussi les écritures déjà envoyées par flush().
        raise
    finally:
        db.close()

    print(f"Import terminé ! Lignes lues : {row_count}, Insérées : {inserted}, Ignorées (doublons) : {skipped}")


if __name__ == "__main__":
    main()
