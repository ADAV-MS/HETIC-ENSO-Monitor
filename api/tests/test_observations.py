import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import date, datetime

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
    
    imp = Import(source_id=source.id, row_count=12, checksum="123")
    db.add(imp)
    db.commit()
    
    # Seed de 12 observations fictives (1 par mois sur 2020)
    for month in range(1, 13):
        db.add(Observation(
            import_id=imp.id,
            index_id=indice.id,
            date=date(2020, month, 1),
            value=float(month) / 10
        ))
    db.commit()
    db.close()
    
    yield
    
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)

# TEST 1 : Période valide → 200
def test_observations_valid_period():
    response = client.get("/api/v1/observations?start=2020-01-01&end=2020-02-28")
    assert response.status_code == 200
    data = response.json()
    assert len(data["observations"]) == 2
    assert data["observations"][0]["value"] == 0.1

# TEST 2 : Date invalide → 422
def test_observations_invalid_dates():
    # Format invalide
    response = client.get("/api/v1/observations?start=abc&end=2020-01-01")
    assert response.status_code == 422

    # Ordre inversé
    response = client.get("/api/v1/observations?start=2021-01-01&end=2020-01-01")
    assert response.status_code == 422

# TEST 3 (bonus) : Période vide → 200 avec liste vide
def test_observations_empty_period():
    response = client.get("/api/v1/observations?start=2030-01-01&end=2030-12-31")
    assert response.status_code == 200
    data = response.json()
    assert len(data["observations"]) == 0

def ajouter_source_secondaire():
    """Ajoute une observation ONI provenant d'un autre import / d'une autre source."""
    with TestingSessionLocal() as db:
        indice = db.query(Indice).filter_by(code="ONI").one()
        source = Source(
            name="NOAA secondaire",
            url="https://example.org/oni.txt",
            version="v2",
            extracted_at=datetime(2026, 2, 1),
        )
        db.add(source)
        db.flush()
        import_record = Import(source_id=source.id, row_count=1, checksum="second")
        db.add(import_record)
        db.flush()
        db.add(Observation(
            import_id=import_record.id,
            index_id=indice.id,
            date=date(2021, 1, 1),
            value=2.1,
        ))
        ids = source.id, import_record.id
        db.commit()
    return ids


def test_provenance_filtree_sur_la_source_reelle():
    """Une autre source en base ne doit pas imposer la première source à l'API."""
    source_id, import_id = ajouter_source_secondaire()
    response = client.get("/api/v1/observations?start=2021-01-01&end=2021-01-01")

    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "NOAA secondaire"
    assert data["version"] == "v2"
    assert len(data["observations"]) == 1
    provenance = data["observations"][0]["provenance"]
    assert provenance["source_id"] == source_id
    assert provenance["source"] == "NOAA secondaire"
    assert provenance["source_url"] == "https://example.org/oni.txt"
    assert provenance["import_id"] == import_id
    assert provenance["indice_code"] == "ONI"


def test_plusieurs_sources_sans_provenance_arbitraire():
    """Si deux sources sont présentes, chacune reste associée à sa ligne."""
    source_id, import_id = ajouter_source_secondaire()
    response = client.get("/api/v1/observations?start=2020-12-01&end=2021-01-01")

    assert response.status_code == 200
    data = response.json()
    assert len(data["observations"]) == 2
    assert data["source"] is None
    assert data["indice"] is None
    assert data["version"] is None
    assert data["extracted_at"] is None
    assert data["observations"][0]["provenance"]["source"] == "NOAA"
    assert data["observations"][1]["provenance"]["source_id"] == source_id
    assert data["observations"][1]["provenance"]["import_id"] == import_id


def test_plusieurs_indices_conservent_leur_identite():
    """Deux indices d'une même source ne sont pas confondus dans les métadonnées."""
    with TestingSessionLocal() as db:
        import_record = db.query(Import).one()
        roni = Indice(code="RONI", label="Relative Oceanic Niño Index", unit="°C anomaly")
        db.add(roni)
        db.flush()
        db.add(Observation(
            import_id=import_record.id,
            index_id=roni.id,
            date=date(2020, 1, 1),
            value=-0.5,
        ))
        db.commit()

    response = client.get("/api/v1/observations?start=2020-01-01&end=2020-01-01")
    assert response.status_code == 200
    data = response.json()
    assert data["indice"] is None
    assert [item["provenance"]["indice_code"] for item in data["observations"]] == [
        "ONI", "RONI"
    ]


def test_plusieurs_imports_meme_source_conservent_metadonnees_communes():
    """Un nouvel import de la même source ne rend pas la période artificiellement mixte."""
    with TestingSessionLocal() as db:
        source = db.query(Source).one()
        indice = db.query(Indice).one()
        second_import = Import(source_id=source.id, row_count=1, checksum="newer")
        db.add(second_import)
        db.flush()
        db.add(Observation(
            import_id=second_import.id,
            index_id=indice.id,
            date=date(2021, 1, 1),
            value=0.3,
        ))
        second_import_id = second_import.id
        db.commit()

    response = client.get("/api/v1/observations?start=2020-12-01&end=2021-01-01")
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "NOAA"
    assert data["indice"] == "ONI"
    assert len(data["observations"]) == 2
    assert data["observations"][1]["provenance"]["import_id"] == second_import_id


def test_une_base_sans_source_ne_provoque_pas_de_500():
    """En l'absence d'observations, aucune provenance n'est inventée."""
    with TestingSessionLocal() as db:
        db.query(Observation).delete()
        db.query(Import).delete()
        db.query(Indice).delete()
        db.query(Source).delete()
        db.commit()

    response = client.get("/api/v1/observations?start=2020-01-01&end=2020-12-31")
    assert response.status_code == 200
    data = response.json()
    assert data["observations"] == []
    assert data["source"] is None
    assert data["extracted_at"] is None

def test_service_delegue_la_recherche_au_repository(monkeypatch):
    """Business logic must call the repository rather than query SQL itself."""
    from app.schemas import ObservationFilter
    from app.services import observations as service

    appels = []
    session_factice = object()
    periode = ObservationFilter(start=date(2020, 1, 1), end=date(2020, 3, 31))

    def faux_lister_observations(db, debut, fin):
        appels.append((db, debut, fin))
        return []

    monkeypatch.setattr(service, "lister_observations", faux_lister_observations)
    resultat = service.construire_reponse_observations(session_factice, periode)

    assert appels == [(session_factice, periode.start, periode.end)]
    assert resultat.observations == []
    assert resultat.source is None
    assert resultat.extracted_at is None


# #32 — Une provenance doit etre liee a l'import de l'observation.

def test_provenance_utilise_date_de_lecture_et_checksum_de_l_import():
    with TestingSessionLocal() as db:
        trace = db.query(Import).one()
        trace.extracted_at = datetime(2026, 11, 21, 10, 12)
        trace.checksum = "sha256-documente"
        db.query(Source).one().extracted_at = datetime(2025, 1, 1)
        db.commit()

    response = client.get("/api/v1/observations?start=2020-01-01&end=2020-01-01")
    assert response.status_code == 200
    data = response.json()
    p = data["observations"][0]["provenance"]
    assert p["extracted_at"].startswith("2026-11-21T10:12:00")
    assert p["checksum"] == "sha256-documente"
    assert p["source"] == "NOAA"
    assert data["extracted_at"] == p["extracted_at"]


def test_melange_imports_meme_source_ne_propose_pas_date_globale_arbitraire():
    with TestingSessionLocal() as db:
        premier = db.query(Import).one()
        premier.extracted_at = datetime(2026, 11, 1, 12)
        source = db.query(Source).one()
        indice = db.query(Indice).one()
        nouveau = Import(
            source_id=source.id,
            row_count=1,
            checksum="sha256-revision",
            extracted_at=datetime(2026, 11, 22, 9),
        )
        db.add(nouveau)
        db.flush()
        db.add(Observation(
            import_id=nouveau.id,
            index_id=indice.id,
            date=date(2021, 1, 1),
            value=1.0,
        ))
        db.commit()

    response = client.get("/api/v1/observations?start=2020-12-01&end=2021-01-01")
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "NOAA"
    assert data["indice"] == "ONI"
    assert data["extracted_at"] is None
    assert len(data["observations"]) == 2
    assert data["observations"][0]["provenance"]["extracted_at"].startswith("2026-11-01")
    assert data["observations"][1]["provenance"]["extracted_at"].startswith("2026-11-22")
    assert data["observations"][1]["provenance"]["checksum"] == "sha256-revision"


def test_import_historique_sans_date_ne_recoit_pas_date_source_inventee():
    with TestingSessionLocal() as db:
        assert db.query(Import).one().extracted_at is None
    response = client.get("/api/v1/observations?start=2020-01-01&end=2020-01-01")
    assert response.status_code == 200
    assert response.json()["observations"][0]["provenance"]["extracted_at"] is None


# #33 — Bornes temporelles et paramètres obligatoires.
def test_filtre_temporel_bornes_inclusives():
    """start et end sont inclus : une seule journée ne renvoie qu'une observation."""
    response = client.get("/api/v1/observations?start=2020-03-01&end=2020-03-01")
    assert response.status_code == 200
    rows = response.json()["observations"]
    assert len(rows) == 1
    assert rows[0]["date"] == "2020-03-01"
    assert rows[0]["value"] == 0.3


def test_filtre_temporel_parametres_obligatoires():
    """L'API rejette proprement les paramètres manquants, sans requête non filtrée."""
    for url in (
        "/api/v1/observations",
        "/api/v1/observations?start=2020-01-01",
        "/api/v1/observations?end=2020-12-01",
    ):
        response = client.get(url)
        assert response.status_code == 422


def test_cors_autorise_origine_configuree():
    """Preflight requests must work from the configured frontend origin."""
    origins = [
        origin.strip()
        for origin in os.getenv(
            "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ]
    assert origins
    response = client.options(
        "/api/v1/observations",
        headers={
            "Origin": origins[0],
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origins[0]
