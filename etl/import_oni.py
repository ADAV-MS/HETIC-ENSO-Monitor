import sys
import os
import hashlib
from io import BytesIO
import pandas as pd
from datetime import datetime, date, UTC

# Lien avec l'API pour utiliser les mêmes modèles
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'api')))
from app.db import SessionLocal
from config import obtenir_chemin_fichier_oni
from repositories import (
    ajouter_observation,
    enregistrer_import,
    obtenir_observation,
    mettre_a_jour_observation,
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


def lire_fichier_oni(filepath: str) -> bytes:
    """Capture le contenu exact du fichier local en une seule lecture."""
    with open(filepath, "rb") as fichier:
        return fichier.read()


def calculer_checksum(contenu: bytes) -> str:
    """Calcule le SHA-256 des memes octets que ceux utilises pour l'import."""
    return hashlib.sha256(contenu).hexdigest()


def lire_donnees_oni(contenu: bytes) -> pd.DataFrame:
    """Parse les observations depuis les octets effectivement controles."""
    return pd.read_csv(BytesIO(contenu), sep=r"\s+")


def transformer_ligne(row: pd.Series) -> tuple[date, float] | None:
    """Transforme une ligne NOAA en date et anomalie, ou l'ignore si la saison est inconnue."""
    season = row["SEAS"]
    year = int(row["YR"])
    value = float(row["ANOM"])
    obs_date = convertir_saison_en_date(season, year)
    if obs_date is None:
        return None
    return obs_date, value


def enregistrer_observations(
    db, df: pd.DataFrame, indice_id: int, import_id: int
) -> tuple[int, int, int]:
    """Ajoute, ignore ou revise les valeurs selon (indice, date)."""
    inserted = 0
    skipped = 0
    updated = 0
    dates_du_fichier: set[date] = set()

    for _, row in df.iterrows():
        observation = transformer_ligne(row)
        if observation is None:
            continue

        obs_date, value = observation
        if obs_date in dates_du_fichier:
            raise ValueError(f"Saison en double dans le fichier NOAA : {obs_date}")
        dates_du_fichier.add(obs_date)

        existante = obtenir_observation(db, indice_id, obs_date)
        if existante is None:
            ajouter_observation(
                db, import_id=import_id, indice_id=indice_id, obs_date=obs_date, value=value
            )
            inserted += 1
        elif existante.value != value:
            mettre_a_jour_observation(existante, import_id=import_id, value=value)
            updated += 1
        else:
            # Une valeur identique conserve son Import d'origine.
            skipped += 1

    return inserted, skipped, updated


def main(filepath: str | None = None) -> None:
    """Orchestre l'import ONI, avec un chemin explicite ou configuré."""
    if filepath is None:
        filepath = obtenir_chemin_fichier_oni()

    contenu = lire_fichier_oni(filepath)
    # Horodatage reel de cette extraction LOCALE, en UTC. Il ne date pas
    # le telechargement anterieur depuis le site de la NOAA.
    extracted_at = datetime.now(UTC)
    checksum = calculer_checksum(contenu)
    df = lire_donnees_oni(contenu)
    row_count = len(df)

    db = SessionLocal()
    try:
        source = obtenir_ou_creer_source(db, extracted_at=extracted_at)
        indice = obtenir_ou_creer_indice(db)
        import_record = enregistrer_import(
            db, source.id, row_count, checksum, extracted_at=extracted_at
        )
        inserted, skipped, updated = enregistrer_observations(
            db, df, indice.id, import_record.id
        )
        db.commit()  # Une seule validation pour toutes les écritures.
    except Exception:
        db.rollback()  # Annule aussi les écritures déjà envoyées par flush().
        raise
    finally:
        db.close()

    print(
        f"Import terminé ! Lignes lues : {row_count}, Insérées : {inserted}, "
        f"Ignorées (doublons) : {skipped}, Révisées : {updated}"
    )


if __name__ == "__main__":
    main()
