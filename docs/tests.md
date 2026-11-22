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

## 3. Accessibilité (Issue #14)

**Tests manuels effectués :**

- **Navigation clavier** : Tab depuis la barre d'adresse → "Date de début" → "Date de fin" → "Actualiser". Le focus est toujours visible (outline bleu) et l'ordre est logique. Aucun piège au clavier.
- **Lecteur d'écran** : Le conteneur du graphique a `role="img"` et `aria-label="Graphique de l'indice ONI de 1997-01-01 à 1998-12-31"`. Le tableau récapitulatif est lu avec son caption et ses en-têtes.
- **Contraste** (vérifié avec WebAIM Contrast Checker) :
  - `#000000` sur `#ffffff` : **21:1** (WCAG AAA)
  - `#ffffff` sur `#004080` : **9:1** (WCAG AAA)
  - `#333333` sur `#ffffff` : **12.6:1** (WCAG AAA)
- **Skip link** : Au premier Tab, un lien « Aller au contenu » devient visible et permet de sauter directement au contenu principal.

**Audit automatisé :**

- **Outil** : axe DevTools (extension navigateur)
- **Résultat** : **0 problème automatique détecté** sur la page.

## 4. Test Frontend (Issue #16)

**Commande :** `cd frontend && npm test`

**Résultat :**
```text
 ✓ src/App.test.tsx (2 tests) 388ms
   ✓ App (2)
     ✓ appelle fetch avec les nouvelles dates après changement de période 306ms
     ✓ met à jour les valeurs affichées après changement de période 79ms

 Test Files  1 passed (1)
      Tests  2 passed (2)
```

**Ce qui est testé :**
- Après changement des champs `start` / `end` et clic sur « Actualiser », `fetch` est rappelé avec les nouvelles dates dans l'URL.
- La table principale « Statistiques sur la période » affiche les nouvelles valeurs (max passe de 2.00 °C à 2.60 °C).
*(Note : `fetch` est mocké via `vi.stubGlobal`, aucun appel réseau réel. `ResizeObserver` est polyfillé pour Recharts, `cleanup()` est appelé entre chaque test, et `within(mainTable)` isole la table principale des tables de comparaison).*

## 5. Validation croisée (Frontend + API)

En complément de la validation Pydantic côté API (issue #9), le frontend vérifie `start <= end` avant tout appel réseau. Si `start > end`, un message d'erreur s'affiche instantanément et le bouton « Réessayer » est proposé. Aucun appel API inutile n'est effectué.