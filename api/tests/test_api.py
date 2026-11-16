import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import date

from app.main import app
from app.routes.observations import get_db
from app.db import Base
from app.models import Source, Indice, Observation, Import

SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    source = Source(name="NOAA", url="test", version="v1", extracted_at=date(2026,1,1))
    indice = Indice(code="ONI", label="ONI", unit="°C")
    db.add(source)
    db.add(indice)
    db.commit()
    
    imp = Import(source_id=source.id, row_count=2, checksum="123")
    db.add(imp)
    db.commit()
    
    db.add(Observation(import_id=imp.id, index_id=indice.id, date=date(2020,1,1), value=1.5))
    db.add(Observation(import_id=imp.id, index_id=indice.id, date=date(2020,2,1), value=1.8))
    db.commit()
    db.close()
    
    yield
    
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)

def test_observations_valid_period():
    response = client.get("/api/v1/observations?start=2020-01-01&end=2020-02-28")
    assert response.status_code == 200
    data = response.json()
    assert len(data["observations"]) == 2
    assert data["observations"][0]["value"] == 1.5

def test_observations_invalid_dates():
    # Format invalide
    response = client.get("/api/v1/observations?start=abc&end=2020-01-01")
    assert response.status_code == 422

    # Ordre inversé
    response = client.get("/api/v1/observations?start=2021-01-01&end=2020-01-01")
    assert response.status_code == 422