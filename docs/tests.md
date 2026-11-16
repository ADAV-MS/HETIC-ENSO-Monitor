# Preuves d'exécution des tests

## 1. Test ETL (Issue #6)

**Commande :** `docker compose run --rm etl pytest tests -v`

**Résultat :**
```text
platform linux -- Python 3.12.16, pytest-8.3.3, pluggy-1.7.0
rootdir: /app
collected 2 items

tests/test_import.py::test_saison_invalide PASSED
tests/test_import.py::test_doublon_non_reinsere PASSED

============================== 2 passed in 1.07s ==============================
```

**Ce qui est testé :**
- Le rejet d'une saison invalide (qui ne correspond à aucun mois).
- La détection d'un doublon via une requête SQL (simulée sur une base SQLite en mémoire).

## 2. Test API (Issue #10)

**Commande :** `docker compose run --rm api pytest tests -v`

**Résultat :**
```text
platform linux -- Python 3.12.16, pytest-8.3.3, pluggy-1.7.0
rootdir: /app
configfile: pytest.ini
collected 3 items

tests/test_observations.py::test_observations_valid_period PASSED
tests/test_observations.py::test_observations_invalid_dates PASSED
tests/test_observations.py::test_observations_empty_period PASSED

============================== 3 passed in 0.91s ==============================
```

**Ce qui est testé :**
- Période valide → 200 avec les bonnes observations.
- Format invalide ou ordre inversé → 422.
- Période sans données → 200 avec liste vide.
*(Note : les tests utilisent SQLite en mémoire avec `StaticPool`. La limite SQLite/PostgreSQL est documentée dans le README).*