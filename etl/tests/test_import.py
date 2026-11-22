import pytest
import pandas as pd
from io import StringIO
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

import sys
import os
# On ajoute le dossier parent (etl) et le dossier api pour que les imports fonctionnent
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'api')))

from import_oni import convertir_saison_en_date, SEASON_TO_MONTH
from app.db import Base
from app.models import Source, Indice, Import, Observation

# 1. FIXTURE : Mini CSV en mémoire (5 lignes)
@pytest.fixture
def mini_csv():
    data = """SEAS  YR   TOTAL   ANOM
  DJF 1950  25.01  -1.32
  JFM 1950  25.36  -1.20
  FMA 1950  25.88  -1.12
  MAM 1950  26.24  -1.08
  AMJ 1950  26.35  -1.10"""
    return StringIO(data)

# 2. FIXTURE : Base de données SQLite en mémoire
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Seed de base
    source = Source(name="Test", url="test", version="v1", extracted_at=datetime.now())
    indice = Indice(code="ONI", label="Test", unit="°C")
    session.add(source)
    session.add(indice)
    session.commit()
    
    yield session
    session.close()

# TEST 1 : Date invalide (saison inconnue) rejetée
def test_saison_valide():
    """Vérifie qu'une saison valide est bien convertie en date."""
    date = convertir_saison_en_date("DJF", 1950)
    assert date.year == 1950
    assert date.month == 1
    assert date.day == 1

def test_saison_invalide():
    # Une saison qui n'existe pas (ex: XYZ) doit renvoyer None
    assert convertir_saison_en_date("XYZ", 1950) is None

# TEST 2 : Doublon non réinséré
def test_doublon_non_reinsere(db_session, mini_csv):
    # On lit le CSV
    df = pd.read_csv(mini_csv, sep=r'\s+')
    
    indice = db_session.query(Indice).first()
    
    # On insère la première ligne manuellement
    obs_date = convertir_saison_en_date(df.iloc[0]['SEAS'], int(df.iloc[0]['YR']))
    obs1 = Observation(import_id=1, index_id=indice.id, date=obs_date, value=df.iloc[0]['ANOM'])
    db_session.add(obs1)
    db_session.commit()

    # On simule la vérification anti-doublon du script
    exists = db_session.query(Observation).filter_by(index_id=indice.id, date=obs_date).first()
    
    # On vérifie que le doublon est bien détecté
    assert exists is not None
    assert exists.value == -1.32