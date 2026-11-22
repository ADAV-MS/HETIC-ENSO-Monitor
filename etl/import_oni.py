import sys
import os
import hashlib
import pandas as pd
from datetime import datetime, date

# Lien avec l'API pour utiliser les mêmes modèles
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'api')))
from app.db import SessionLocal
from repositories import (
    ajouter_observation,
    enregistrer_import,
    observation_existe,
    obtenir_ou_creer_indice,
    obtenir_ou_creer_source,
)

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
        if observation_existe(db, indice_id, obs_date):
            skipped += 1
            continue

        ajouter_observation(
            db, import_id=import_id, indice_id=indice_id, obs_date=obs_date, value=value
        )
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
