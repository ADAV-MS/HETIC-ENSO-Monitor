# Tests et preuves de vérification — ENSO Monitor

## Exécuter les tests (#33)

Depuis la racine du dépôt, dans PowerShell :

```powershell
docker compose run --rm etl pytest tests -v
docker compose run --rm api pytest tests -v
cd frontend
npm test
npm run build
cd ..
```

Les suites Python utilisent **SQLite en mémoire** pour isoler les tests ; elles ne
valident pas à elles seules l'exécution réelle de migrations sur PostgreSQL.
Pour la base de développement, Compose applique automatiquement les migrations au démarrage de `api`. Pour les vérifier ou les rejouer :

```powershell
docker compose run --rm api alembic upgrade head
docker compose run --rm api alembic current
```

## Couverture des risques ETL et API (#33)

| Risque | Test(s) existant(s) | Attendu |
|---|---|---|
| Réimport du même fichier | `test_reimport_identique_conserve_identifiants_et_ne_duplique_pas` | Une seule observation par indice/date ; nouveaux imports tracés |
| Révision des valeurs NOAA | `test_reimport_noaa_revision_et_observation_inchangee` | Valeur mise à jour sans doublon |
| Échec en cours d'import | `test_main_annule_import_apres_echec_et_ferme_session` | Rollback, session fermée, aucune écriture partielle |
| Échec après révision | `test_revision_rollback_restitue_ancienne_valeur` | Ancienne valeur et provenance restaurées |
| Absence de source | `test_une_base_sans_source_ne_provoque_pas_de_500` | HTTP 200, observations vides, métadonnées nulles |
| Plusieurs sources | `test_plusieurs_sources_sans_provenance_arbitraire` | Provenance propre à chaque observation |
| Dates invalides/inversées | `test_observations_invalid_dates` | HTTP 422 |
| Borne de début/fin incluse | `test_filtre_temporel_bornes_inclusives` | Une observation exactement sur la borne |
| Dates manquantes | `test_filtre_temporel_parametres_obligatoires` | HTTP 422 |
| Preflight CORS | `test_cors_autorise_origine_configuree` | HTTP 200 et bonne origine autorisée |

## Suites de tests

- **ETL : 17 tests** après l'issue #32, notamment lecture du fichier NOAA,
  checksum, transactions, configuration et révisions.
- **API : 15 tests** après l'issue #35, notamment filtres, provenances,
  métadonnées absentes et séparation service/repository.
- **Frontend : 6 tests** après l'issue #34, dont les états chargement/erreur, filtre de période et provenance mixte.

Ces nombres décrivent les tests présents dans le dépôt ; les commandes ci-dessus
restent la source de vérité pour les exécutions locales.

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

**Résultat historique de l'issue #16 (avant #34) :**
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

En complément de la validation Pydantic côté API (issue #9), le frontend vérifie `start <= end` avant tout appel réseau. Si `start > end`, un message d'erreur s'affiche instantanément sans afficher les anciennes données. Le bouton « Réessayer » n'est pas proposé pour une période invalide. Aucun appel API inutile n'est effectué.