# ENSO Monitor

Application individuelle HETIC WEB3 d'exploration de l'indice **ONI (Oceanic Niño Index)** de la NOAA CPC : import de mesures authentiques, consultation par période, courbe interactive et comparaison prudente des épisodes **1997–1998** et **2015–2016**.

## Périmètre et limites

- **ETL** Python/Pandas : lecture d'un fichier ONI local, validation des saisons, conversion en dates, contrôle des doublons et mise à jour des valeurs révisées.
- **API** FastAPI `/api/v1` : observations filtrées par `start` et `end` (format `YYYY-MM-DD`), schémas Pydantic, provenance par observation et documentation OpenAPI.
- **Frontend** React/TypeScript/Vite : filtre de période, graphique, états de chargement/erreur/absence de données, comparaison de deux fenêtres fixes.
- **Base** PostgreSQL 16, SQLAlchemy et Alembic. Les tests unitaires Python utilisent SQLite en mémoire ; ils ne remplacent pas un test d'intégration PostgreSQL.

L'ONI représente des anomalies de température de surface de la mer en région Niño 3.4 : il ne mesure pas directement les impacts climatiques et ne constitue **pas une prévision**. La comparaison est descriptive ; elle ne permet pas de conclure à une causalité locale.

## Démarrer depuis un clone vierge (PowerShell + Docker Desktop)

**Prérequis :** Git, Docker Desktop avec Compose v2 et PowerShell. Le téléchargement du fichier NOAA est volontairement manuel ; les données et les secrets ne sont pas versionnés.

```powershell
git clone https://github.com/ADAV-MS/HETIC-ENSO-Monitor.git
cd HETIC-ENSO-Monitor
Copy-Item .env.example .env
# Modifier POSTGRES_PASSWORD dans .env avant le premier démarrage.
New-Item -ItemType Directory -Force .\data | Out-Null
Invoke-WebRequest -Uri "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt" -OutFile ".\data\oni.data"
Get-Content .\data\oni.data -TotalCount 2
```

Le fichier doit commencer par un en-tête contenant `SEAS`, `YR`, `TOTAL`, `ANOM` (et non du HTML). Source : [NOAA CPC — ONI](https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt).

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose build etl
docker compose ps
# L'API applique « alembic upgrade head » avant Uvicorn.
docker compose run --rm api alembic current
docker compose run --rm etl python import_oni.py
```

**Adresses locales :** interface <http://localhost:5173> ; documentation API <http://localhost:8000/docs> ; santé <http://localhost:8000/api/v1/health>. Ouvrir l'interface et vérifier le graphique puis modifier les dates et sélectionner « Actualiser ».

### Développement frontend sans Nginx (optionnel)

Le mode Docker Compose ci-dessus sert le frontend avec **Nginx**. Pour développer avec **Vite** et `npm run dev`, installer **Node.js 24** et npm sur l'hôte (Node.js 25 n'est pas dans la plage de versions déclarée par Vitest 5.1.1). Garder l'API et PostgreSQL démarrés avec Compose ; arrêter le frontend Nginx s'il utilise déjà le port 5173 :

```powershell
docker compose up --build -d db api
docker compose stop frontend
cd frontend
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
npm ci
npm run dev
```

La configuration Vite `frontend/.env` doit définir `VITE_API_URL=http://localhost:8000/api/v1` si l'API est sur le port local 8000. La variable du `.env` **racine** sert à Docker Compose et ne remplace pas automatiquement `frontend/.env` pour Vite. Le serveur de développement s'ouvre sur <http://localhost:5173> ; l'arrêter avec `Ctrl+C` puis revenir à la racine avec `cd ..`. Ne pas lancer simultanément Vite et le frontend Compose sur le même port.

Vérifier également la **vraie pile PostgreSQL** (les tests unitaires utilisent SQLite) :

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/health"
$r = Invoke-RestMethod "http://localhost:8000/api/v1/observations?start=1997-01-01&end=1998-12-31"
$r.observations.Count # Doit être > 0 après l'import.
docker compose run --rm api alembic current
```

La migration attendue à cette version est `d0a9b32c5c91 (head)` ; elle ajoute l'horodatage des imports. Le fonctionnement a été vérifié localement le 22 novembre 2026 avec **24 observations** pour 1997–1998 dans la base de développement ; le nombre dépend du contenu effectivement importé.

## Configuration

Créer `.env` depuis `.env.example` :

| Variable | Rôle | Valeur locale de référence |
|---|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Accès PostgreSQL | `enso`, **à remplacer**, `enso` |
| `POSTGRES_PORT` | Port PostgreSQL publié sur `127.0.0.1` | `5432` |
| `API_PORT` | Port HTTP de l'API sur `127.0.0.1` | `8000` |
| `FRONTEND_PORT` | Port HTTP du frontend sur `127.0.0.1` | `5173` |
| `VITE_API_URL` | Adresse API visible depuis le navigateur, compilée au build | `http://localhost:8000/api/v1` |
| `ALLOWED_ORIGINS` | Origines autorisées par CORS, séparées par des virgules | `http://localhost:5173,http://127.0.0.1:5173` |
| `NOAA_ONI_FILEPATH` | Chemin du fichier **dans le conteneur ETL** | `/app/data/oni.data` si variable vide |

Les conteneurs API et ETL se connectent à `db:5432` sur le réseau Compose. Ne pas utiliser `http://api:8000` dans `VITE_API_URL` : le navigateur ne résout pas ce nom interne Docker. Après modification de `API_PORT` ou `VITE_API_URL`, adapter les deux valeurs et reconstruire le frontend : `docker compose up --build -d frontend`. Après modification de `FRONTEND_PORT`, mettre `ALLOWED_ORIGINS` à jour.

`./data` est monté dans le conteneur ETL sous `/app/data`. Pour charger un autre fichier :

```powershell
docker compose run --rm -e NOAA_ONI_FILEPATH=/app/data/oni-alternative.data etl python import_oni.py
```

Ce fichier doit auparavant exister dans `./data`. Un appel explicite `main(filepath)` est prioritaire sur la variable d'environnement. Sans conteneur ETL, Python ne charge **pas automatiquement** le fichier `.env` de Compose ; il faut définir les variables dans son environnement d'exécution.

Pour consulter les journaux et arrêter les services :

```powershell
docker compose logs --tail 100 db api frontend
docker compose down
```

`docker compose down` conserve le volume PostgreSQL. **Ne pas utiliser `docker compose down -v`** sauf pour effacer volontairement la base locale ; modifier un mot de passe dans `.env` après l'initialisation du volume ne change pas celui qui y est déjà enregistré.

## Architecture et décisions de refactoring (milestone J4.5)

```text
Navigateur → React / Vite (Nginx dans Docker)
                 │ GET /api/v1/observations?start=...&end=...
                 ▼
             FastAPI (route → service → repository)
                 │ SQLAlchemy
                 ▼
             PostgreSQL
                 ▲
      ETL Python (orchestration → fonctions de transformation
                  → repositories SQLAlchemy)
                 ▲
           Fichier NOAA local
```

- **ETL (`etl/import_oni.py`) :** `main()` coordonne lecture, transformation et import. `convertir_saison_en_date()` centralise la conversion ; `etl/repositories.py` contient les accès SQL. Une transaction unique est validée à la fin par `commit()` ; `rollback()` annule les écritures en cas d'échec et la session est toujours fermée. Les repositories n'appellent pas `commit()`.
- **API (`api/app/routes/`, `services/`, `repositories/`) :** les routes valident et délèguent ; le service assemble la réponse et les métadonnées ; le repository filtre les observations par dates et charge les relations. La provenance suit `Observation → Import → Source` et `Observation → Indice` : aucune source arbitraire n'est sélectionnée via `.first()`.
- **Schéma (`api/app/models.py`, `api/alembic/`) :** modèles `Source`, `Indice`, `Import`, `Observation` et migrations reproductibles. L'unicité `(index_id, date)` évite les doublons.
- **Frontend (`frontend/src/App.tsx`) :** périodes saisie et affichée distinctes ; un échec ou un chargement ne présente pas une ancienne courbe comme actuelle. Le composant `Comparison` utilise deux fenêtres historiques fixes.

Ces choix privilégient une architecture explicable, testable et adaptée au MVP, sans multiplier les couches ou fonctionnalités facultatives. Les repositories isolent les requêtes ; ils ne prétendent pas constituer une abstraction générique de stockage.

## Source NOAA, horodatage et révisions

La série utilisée est l'ONI NOAA CPC : [description et limites scientifiques](docs/sources-noaa.md). L'ETL lit un **fichier local**, pas une ressource téléchargée automatiquement. `Import.extracted_at` correspond à la **lecture du fichier par l'ETL en UTC** ; ce n'est ni la date de publication NOAA ni la date du téléchargement manuel.

Chaque exécution produit un enregistrement d'import avec `row_count`, `checksum` SHA-256, `imported_at` et `extracted_at` (l'horodatage est `NULL` pour les imports historiques dont la date exacte est inconnue). Un réimport identique n'insère pas de doublon et conserve les liens d'origine ; une valeur corrigée est mise à jour et associée au nouvel import. Les anciennes valeurs écrasées ne sont **pas historisées** : conserver les fichiers originaux est nécessaire pour une reconstitution complète.

## Tests et qualité

Depuis la racine, exécuter :

```powershell
docker compose run --rm etl pytest tests -v
docker compose run --rm api pytest tests -v
cd frontend
npm ci
npm test
npm run lint
npm run build
cd ..
```

Au 22 novembre 2026, les validations locales rapportées pour l'issue #35 sont **17 tests ETL, 15 tests API et 6 tests frontend réussis**, avec lint et build frontend réussis. Les suites Python utilisent SQLite en mémoire ; compléter par le test HTTP de la pile PostgreSQL indiqué ci-dessus. Détails et scénarios : [docs/tests.md](docs/tests.md).

Le build Vite peut avertir que le bundle JavaScript dépasse 500 Ko ; ce warning de taille n'empêche pas le build et reste une piste d'optimisation.

## Usage de l'IA

**Outil déclaré :** ChatGPT (OpenAI), utilisé comme assistant pour formuler et réviser des propositions d'architecture, de refactoring du code ETL/API/frontend, de tests de non-régression, de diagrammes Mermaid et de documentation technique. L'auteur a intégré les modifications dans le dépôt Git, exécuté les commandes de vérification et contrôlé les résultats avant les Pull Requests. L'assistance IA ne remplace ni les tests d'exécution ni la revue des limites scientifiques.

Les observations ONI sont issues du fichier **NOAA CPC** téléchargé séparément : les mesures ne sont pas générées par l'IA. Cette déclaration décrit l'assistance documentée dans ce projet ; elle doit être complétée si d'autres outils d'IA ont été utilisés.

## Livrables HETIC et périmètre de déploiement

Le dépôt contient **le code applicatif et sa documentation d'exécution**. Le sujet HETIC demande **séparément** un dossier de conception PDF (15 pages maximum, couverture comprise), avec parcours UX, diagrammes UML (cas d'utilisation, domaine/classes, séquence), architecture et schéma SQL, organisation, tests, sécurité, déploiement cible et bilan avec usage de l'IA. Le README ne se substitue pas à ce livrable.

Les trois diagrammes sont versionnés dans [docs/uml](docs/uml/README.md), avec les sources Mermaid et les exports SVG/PNG utilisables dans le dossier de conception.

**Docker Compose ci-dessus est destiné au développement local.** Le déploiement sur VPS avec HTTPS/Caddy, sauvegardes et gestion des secrets relève de l'architecture cible à justifier dans le dossier ; il n'est pas fourni ici comme un déploiement public opérationnel.
