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
