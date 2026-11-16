import sys
import os
import hashlib
import pandas as pd
from datetime import datetime

# Lien avec l'API pour utiliser les mêmes modèles
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'api')))
from app.db import SessionLocal
from app.models import Source, Indice, Import, Observation

SEASON_TO_MONTH = {
    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12
}

def main():
    filepath = "/app/data/oni.data"
    
    with open(filepath, "rb") as f:
        checksum = hashlib.sha256(f.read()).hexdigest()

    # Lecture du fichier avec séparation sur les espaces
    df = pd.read_csv(filepath, sep=r'\s+')
    row_count = len(df)

    db = SessionLocal()

    # 1. Source
    source = db.query(Source).filter_by(name="NOAA CPC").first()
    if not source:
        source = Source(name="NOAA CPC", url="https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt", version="v6", extracted_at=datetime.utcnow())
        db.add(source)
        db.commit()
        db.refresh(source)

    # 2. Indice
    indice = db.query(Indice).filter_by(code="ONI").first()
    if not indice:
        indice = Indice(code="ONI", label="Oceanic Niño Index", unit="°C anomaly")
        db.add(indice)
        db.commit()
        db.refresh(indice)

    # 3. Traçabilité de l'import
    import_record = Import(source_id=source.id, row_count=row_count, checksum=checksum)
    db.add(import_record)
    db.commit()
    db.refresh(import_record)

    # 4. Observations
    inserted = 0
    skipped = 0

    for _, row in df.iterrows():
        season = row['SEAS']
        year = int(row['YR'])
        value = float(row['ANOM'])
        month = SEASON_TO_MONTH.get(season)
        if not month:
            continue
            
        obs_date = datetime(year, month, 1).date()

        # Anti-doublon
        exists = db.query(Observation).filter_by(index_id=indice.id, date=obs_date).first()
        if exists:
            skipped += 1
            continue

        obs = Observation(import_id=import_record.id, index_id=indice.id, date=obs_date, value=value)
        db.add(obs)
        inserted += 1

    db.commit()
    db.close()

    print(f"Import terminé ! Lignes lues : {row_count}, Insérées : {inserted}, Ignorées (doublons) : {skipped}")

if __name__ == "__main__":
    main()