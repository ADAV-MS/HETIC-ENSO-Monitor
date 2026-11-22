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

def test_transformation_ligne_reutilise_conversion():
    """La transformation ONI repose sur la fonction de conversion des saisons."""
    from import_oni import transformer_ligne

    row = pd.Series({"SEAS": "JFM", "YR": 1950, "ANOM": -1.20})
    obs_date, value = transformer_ligne(row)
    assert (obs_date.year, obs_date.month, obs_date.day) == (1950, 2, 1)
    assert value == -1.20
    assert transformer_ligne(pd.Series({"SEAS": "XYZ", "YR": 1950, "ANOM": 0.5})) is None


def test_main_preserve_import_et_anti_doublon(tmp_path, monkeypatch, capsys):
    """Deux exécutions de main conservent la logique actuelle de réimport."""
    from sqlalchemy.orm import sessionmaker
    import import_oni

    filepath = tmp_path / "oni.data"
    filepath.write_text(
        "SEAS YR TOTAL ANOM\n"
        "DJF 1950 25.01 -1.32\n"
        "JFM 1950 25.36 -1.20\n"
        "FMA 1950 25.88 -1.12\n",
        encoding="utf-8",
    )

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr(import_oni, "SessionLocal", Session)

    import_oni.main(str(filepath))
    import_oni.main(str(filepath))

    with Session() as db:
        assert db.query(Source).filter_by(name="NOAA CPC").count() == 1
        assert db.query(Indice).filter_by(code="ONI").count() == 1
        assert db.query(Import).count() == 2
        assert db.query(Observation).count() == 3
        assert {obs.date.month for obs in db.query(Observation).all()} == {1, 2, 3}

    output = capsys.readouterr().out
    assert "Insérées : 3, Ignorées (doublons) : 0" in output
    assert "Insérées : 0, Ignorées (doublons) : 3" in output


@pytest.fixture
def sessions_tracees(monkeypatch):
    """Base isolée et session instrumentée pour vérifier transaction et fermeture."""
    import import_oni
    from sqlalchemy.orm import Session, sessionmaker

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    class SessionTracee(Session):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.nb_commits = 0
            self.nb_rollbacks = 0
            self.est_fermee = False

        def commit(self):
            self.nb_commits += 1
            return super().commit()

        def rollback(self):
            self.nb_rollbacks += 1
            return super().rollback()

        def close(self):
            self.est_fermee = True
            return super().close()

    SessionTest = sessionmaker(bind=engine, class_=SessionTracee, autoflush=False)
    sessions = []

    def creer_session():
        session = SessionTest()
        sessions.append(session)
        return session

    monkeypatch.setattr(import_oni, "SessionLocal", creer_session)
    yield SessionTest, sessions
    engine.dispose()


def test_main_valide_une_seule_transaction(tmp_path, sessions_tracees):
    """Un import réussi valide les quatre tables en un seul commit."""
    import import_oni

    SessionTest, sessions = sessions_tracees
    filepath = tmp_path / "oni.data"
    filepath.write_text(
        "SEAS YR TOTAL ANOM\n"
        "DJF 1950 25.01 -1.32\n"
        "JFM 1950 25.36 -1.20\n",
        encoding="utf-8",
    )

    import_oni.main(str(filepath))

    assert len(sessions) == 1
    assert sessions[0].nb_commits == 1
    assert sessions[0].nb_rollbacks == 0
    assert sessions[0].est_fermee

    with SessionTest() as db:
        assert db.query(Source).count() == 1
        assert db.query(Indice).count() == 1
        assert db.query(Import).count() == 1
        assert db.query(Observation).count() == 2


def test_main_annule_import_apres_echec_et_ferme_session(
    tmp_path, monkeypatch, sessions_tracees
):
    """Même après un flush SQL, une exception annule toutes les écritures."""
    import import_oni

    SessionTest, sessions = sessions_tracees
    filepath = tmp_path / "oni.data"
    filepath.write_text(
        "SEAS YR TOTAL ANOM\n"
        "DJF 1950 25.01 -1.32\n"
        "JFM 1950 25.36 -1.20\n",
        encoding="utf-8",
    )

    enregistrer_original = import_oni.enregistrer_observations

    def planter_apres_insertion(db, df, indice_id, import_id):
        enregistrer_original(db, df, indice_id, import_id)
        db.flush()  # Force l'envoi des INSERT dans la transaction non validée.
        raise RuntimeError("Échec simulé avant le commit")

    monkeypatch.setattr(import_oni, "enregistrer_observations", planter_apres_insertion)

    with pytest.raises(RuntimeError, match="Échec simulé"):
        import_oni.main(str(filepath))

    assert len(sessions) == 1
    assert sessions[0].nb_commits == 0
    assert sessions[0].nb_rollbacks == 1
    assert sessions[0].est_fermee

    with SessionTest() as db:
        assert db.query(Source).count() == 0
        assert db.query(Indice).count() == 0
        assert db.query(Import).count() == 0
        assert db.query(Observation).count() == 0


def test_repositories_ne_valident_pas_la_transaction(sessions_tracees):
    """Les accès SQL préparent les écritures, mais seul main() décide du commit."""
    from repositories import (
        ajouter_observation,
        enregistrer_import,
        observation_existe,
        obtenir_ou_creer_indice,
        obtenir_ou_creer_source,
    )

    SessionTest, _ = sessions_tracees
    db = SessionTest()
    try:
        source = obtenir_ou_creer_source(db)
        indice = obtenir_ou_creer_indice(db)
        record = enregistrer_import(db, source.id, 1, "sha256-test")
        obs_date = convertir_saison_en_date("DJF", 1950)
        assert not observation_existe(db, indice.id, obs_date)
        ajouter_observation(
            db, import_id=record.id, indice_id=indice.id, obs_date=obs_date, value=-1.32
        )
        db.flush()
        assert observation_existe(db, indice.id, obs_date)
        assert db.nb_commits == 0
        db.rollback()
    finally:
        db.close()

    with SessionTest() as verification:
        assert verification.query(Source).count() == 0
        assert verification.query(Indice).count() == 0
        assert verification.query(Import).count() == 0
        assert verification.query(Observation).count() == 0


def test_chemin_noaa_par_defaut(monkeypatch):
    """Sans variable d'environnement, le chemin Docker historique est conserve."""
    from config import obtenir_chemin_fichier_oni

    monkeypatch.delenv("NOAA_ONI_FILEPATH", raising=False)
    assert obtenir_chemin_fichier_oni() == "/app/data/oni.data"


def test_chemin_noaa_personnalise_et_env_vide(monkeypatch, tmp_path):
    """La variable est lue a l'execution ; une valeur vide utilise le defaut."""
    from config import obtenir_chemin_fichier_oni

    alternative = tmp_path / "oni-alternative.data"
    monkeypatch.setenv("NOAA_ONI_FILEPATH", str(alternative))
    assert obtenir_chemin_fichier_oni() == str(alternative)

    monkeypatch.setenv("NOAA_ONI_FILEPATH", "")
    assert obtenir_chemin_fichier_oni() == "/app/data/oni.data"


def test_main_charge_le_chemin_noaa_depuis_env(tmp_path, monkeypatch, sessions_tracees):
    """main() sans argument charge le fichier defini par la configuration."""
    import import_oni

    SessionTest, sessions = sessions_tracees
    alternative = tmp_path / "oni-alternative.data"
    alternative.write_text(
        "SEAS YR TOTAL ANOM\n"
        "DJF 1998 25.01 1.40\n"
        "JFM 1998 25.36 1.20\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("NOAA_ONI_FILEPATH", str(alternative))

    import_oni.main()

    assert len(sessions) == 1
    assert sessions[0].nb_commits == 1
    assert sessions[0].est_fermee
    with SessionTest() as db:
        observations = db.query(Observation).order_by(Observation.date).all()
        assert [(obs.date.year, obs.date.month, obs.value) for obs in observations] == [
            (1998, 1, 1.40), (1998, 2, 1.20)
        ]


def test_main_argument_explicite_prioritaire_sur_env(tmp_path, monkeypatch, sessions_tracees):
    """L'argument filepath historique reste prioritaire pour les appels existants."""
    import import_oni

    SessionTest, _ = sessions_tracees
    fichier = tmp_path / "oni-explicite.data"
    fichier.write_text("SEAS YR TOTAL ANOM\nDJF 2001 25.01 -0.42\n", encoding="utf-8")
    monkeypatch.setenv("NOAA_ONI_FILEPATH", str(tmp_path / "inexistant.data"))

    import_oni.main(str(fichier))

    with SessionTest() as db:
        observations = db.query(Observation).all()
        assert len(observations) == 1
        assert (observations[0].date.year, observations[0].value) == (2001, -0.42)


# #32 — Traçabilité scientifique et valeurs révisées NOAA.

def _horodatage_utc(value):
    """SQLite perd le fuseau sur les DateTime ; normalise pour les assertions."""
    from datetime import UTC

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def test_import_trace_la_vraie_lecture_locale_et_checksum(tmp_path, sessions_tracees):
    from datetime import UTC
    from hashlib import sha256
    import import_oni

    SessionTest, sessions = sessions_tracees
    fichier = tmp_path / "oni.data"
    fichier.write_text("SEAS YR TOTAL ANOM\nDJF 2001 25.01 -0.42\n", encoding="utf-8")

    avant = datetime.now(UTC)
    import_oni.main(str(fichier))
    apres = datetime.now(UTC)

    assert sessions[0].nb_commits == 1
    assert sessions[0].est_fermee
    with SessionTest() as db:
        source = db.query(Source).filter_by(name="NOAA CPC").one()
        trace = db.query(Import).one()
        obs = db.query(Observation).one()
        assert source.version == "v6"
        assert source.url == "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
        assert trace.row_count == 1
        assert trace.checksum == sha256(fichier.read_bytes()).hexdigest()
        assert avant <= _horodatage_utc(trace.extracted_at) <= apres
        assert avant <= _horodatage_utc(source.extracted_at) <= apres
        assert obs.import_id == trace.id


def test_reimport_noaa_revision_et_observation_inchangee(tmp_path, sessions_tracees, capsys):
    """Une valeur modifiee est actualisee ; une valeur identique reste liee a son import."""
    import import_oni

    SessionTest, sessions = sessions_tracees
    fichier = tmp_path / "oni.data"
    fichier.write_text(
        "SEAS YR TOTAL ANOM\nDJF 2001 25.01 -0.42\nJFM 2001 26.22 -0.21\n",
        encoding="utf-8",
    )
    import_oni.main(str(fichier))
    with SessionTest() as db:
        premier = db.query(Import).one()
        premier_id = premier.id
        ancien_checksum = premier.checksum

    fichier.write_text(
        "SEAS YR TOTAL ANOM\nDJF 2001 25.01 -0.38\nJFM 2001 26.22 -0.21\n",
        encoding="utf-8",
    )
    import_oni.main(str(fichier))

    assert len(sessions) == 2
    assert all(s.nb_commits == 1 and s.est_fermee for s in sessions)
    with SessionTest() as db:
        assert db.query(Source).filter_by(name="NOAA CPC").count() == 1
        assert db.query(Indice).filter_by(code="ONI").count() == 1
        assert db.query(Import).count() == 2
        assert db.query(Observation).count() == 2
        imports = db.query(Import).order_by(Import.id).all()
        assert imports[0].checksum == ancien_checksum
        assert imports[1].checksum != ancien_checksum
        assert imports[0].extracted_at is not None
        assert imports[1].extracted_at is not None
        obs = {o.date.month: o for o in db.query(Observation).all()}
        assert obs[1].value == -0.38
        assert obs[1].import_id == imports[1].id
        assert obs[2].value == -0.21
        assert obs[2].import_id == premier_id
        assert _horodatage_utc(db.query(Source).one().extracted_at) == _horodatage_utc(imports[1].extracted_at)
    assert "Insérées : 0, Ignorées (doublons) : 1, Révisées : 1" in capsys.readouterr().out


def test_reimport_identique_conserve_identifiants_et_ne_duplique_pas(tmp_path, sessions_tracees):
    import import_oni

    SessionTest, _ = sessions_tracees
    fichier = tmp_path / "oni.data"
    fichier.write_text("SEAS YR TOTAL ANOM\nDJF 2001 25.01 -0.42\n", encoding="utf-8")
    import_oni.main(str(fichier))
    with SessionTest() as db:
        original_id = db.query(Observation).one().import_id
    import_oni.main(str(fichier))
    with SessionTest() as db:
        assert db.query(Import).count() == 2  # Une trace par tentative d'import.
        assert db.query(Observation).count() == 1
        assert db.query(Observation).one().import_id == original_id
        assert db.query(Import).all()[0].checksum == db.query(Import).all()[1].checksum


def test_revision_rollback_restitue_ancienne_valeur(tmp_path, monkeypatch, sessions_tracees):
    """Si une revision plante apres flush, l'ancien contenu reste intact."""
    import import_oni

    SessionTest, sessions = sessions_tracees
    fichier = tmp_path / "oni.data"
    fichier.write_text("SEAS YR TOTAL ANOM\nDJF 2001 25.01 -0.42\n", encoding="utf-8")
    import_oni.main(str(fichier))

    with SessionTest() as db:
        before = db.query(Observation).one()
        old_id = before.import_id
        old_value = before.value
        old_date = _horodatage_utc(db.query(Source).one().extracted_at)

    fichier.write_text("SEAS YR TOTAL ANOM\nDJF 2001 25.01 -0.31\n", encoding="utf-8")
    original = import_oni.enregistrer_observations

    def echouer_apres_revision(db, df, indice_id, import_id):
        original(db, df, indice_id, import_id)
        db.flush()
        raise RuntimeError("revision echouee")

    monkeypatch.setattr(import_oni, "enregistrer_observations", echouer_apres_revision)
    with pytest.raises(RuntimeError, match="revision echouee"):
        import_oni.main(str(fichier))

    assert sessions[-1].nb_commits == 0
    assert sessions[-1].nb_rollbacks == 1
    assert sessions[-1].est_fermee
    with SessionTest() as db:
        obs = db.query(Observation).one()
        assert obs.value == old_value
        assert obs.import_id == old_id
        assert db.query(Import).count() == 1
        assert _horodatage_utc(db.query(Source).one().extracted_at) == old_date


def test_rejet_saisons_en_double_et_rollback(tmp_path, sessions_tracees):
    import import_oni

    SessionTest, sessions = sessions_tracees
    fichier = tmp_path / "oni.data"
    fichier.write_text(
        "SEAS YR TOTAL ANOM\nDJF 2001 25.01 -0.42\nDJF 2001 25.01 -0.31\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Saison en double"):
        import_oni.main(str(fichier))

    assert sessions[0].nb_rollbacks == 1
    assert sessions[0].est_fermee
    with SessionTest() as db:
        assert db.query(Import).count() == 0
        assert db.query(Observation).count() == 0
