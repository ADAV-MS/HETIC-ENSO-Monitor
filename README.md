# ENSO Monitor

Application d'analyse des épisodes ENSO à partir de l'indice ONI du NOAA CPC.

## Démarrage reproductible - Docker Compose (issue #35)

**Prérequis :** Git, Docker Desktop avec Compose v2 et PowerShell. Le fichier de
mesures NOAA n'est pas versionné dans Git ; il est téléchargé à chaque installation.

Depuis un clone vierge, ouvrir PowerShell :

```powershell
git clone https://github.com/ADAV-MS/HETIC-ENSO-Monitor.git
cd HETIC-ENSO-Monitor
Copy-Item .env.example .env
# Éditer .env : remplacer POSTGRES_PASSWORD=change_me par un mot de passe local.
New-Item -ItemType Directory -Force .\data | Out-Null
Invoke-WebRequest -Uri "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt" -OutFile ".\data\oni.data"
Get-Content .\data\oni.data -TotalCount 2
```

La première ligne doit commencer par `SEAS  YR   TOTAL   ANOM`, et non par du HTML.
La source officielle est [NOAA CPC ONI](https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt).
Le téléchargement est manuel ; la date `extracted_at` en base est la date de **lecture
locale par l'ETL**, pas la date de téléchargement NOAA.

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose build etl  # Le profil tools ne se construit pas avec up.
docker compose ps
# L'API applique alembic upgrade head automatiquement avant son démarrage.
docker compose run --rm etl python import_oni.py
```

Ouvrir :

- **Application :** http://localhost:5173
- **API Swagger :** http://localhost:8000/docs
- **Healthcheck :** http://localhost:8000/api/v1/health

Test d'intégration **avec PostgreSQL réel**, distinct des tests SQLite :

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/health"
$r = Invoke-RestMethod "http://localhost:8000/api/v1/observations?start=1997-01-01&end=1998-12-31"
$r.observations.Count  # Doit être supérieur à zéro après l'import.
docker compose run --rm api alembic current
```

La révision Alembic attendue est `d0a9b32c5c91 (head)`. Pour contrôler CORS :

```powershell
curl.exe -i -X OPTIONS "http://localhost:8000/api/v1/observations" -H "Origin: http://localhost:5173" -H "Access-Control-Request-Method: GET"
```

Le résultat doit contenir un code HTTP `200` et
`access-control-allow-origin: http://localhost:5173`.

### Configuration et commandes utiles

| Variable `.env` | Usage | Défaut local |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Identifiants de la base | `enso` / à changer / `enso` |
| `POSTGRES_PORT` | Port exposé sur l'hôte uniquement | `5432` |
| `API_PORT` | Port API exposé sur l'hôte | `8000` |
| `FRONTEND_PORT` | Port du site web exposé sur l'hôte | `5173` |
| `VITE_API_URL` | URL API **vue du navigateur** ; intégrée au build frontend | `http://localhost:8000/api/v1` |
| `ALLOWED_ORIGINS` | Origines CORS autorisées (liste séparée par des virgules) | `http://localhost:5173,http://127.0.0.1:5173` |
| `NOAA_ONI_FILEPATH` | Chemin du fichier **dans le conteneur ETL** | `/app/data/oni.data` si vide |

Les conteneurs API et ETL utilisent toujours `db:5432` pour PostgreSQL.
Si `API_PORT` change, adapter également `VITE_API_URL` et reconstruire le frontend
(`docker compose up --build -d frontend`). Si `FRONTEND_PORT` change, adapter
`ALLOWED_ORIGINS`. Ne jamais utiliser `http://api:8000` comme URL Vite : cette
adresse Docker n'est pas accessible depuis le navigateur de l'utilisateur.

Pour voir les erreurs ou relancer l'import :

```powershell
docker compose logs --tail 100 db api frontend
docker compose run --rm api alembic upgrade head
docker compose run --rm etl python import_oni.py
docker compose down  # Conserve les données du volume PostgreSQL.
```

`docker compose down -v` **supprime définitivement le volume PostgreSQL** :
ne l'utiliser que pour un reset volontaire de la base locale. Changer le mot
de passe après la première initialisation ne modifie pas le mot de passe déjà
stocké dans ce volume.

Tests automatisés :

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

Les tests Python utilisent SQLite en mémoire. Le smoke test HTTP ci-dessus
vérifie en plus la connexion à PostgreSQL et l'intégration de la pile.

### Alternative frontend hors Docker

Pour le serveur Vite (`localhost:5173`) au lieu du serveur Nginx Docker :

```powershell
cd frontend
Copy-Item .env.example .env.local
npm ci
npm run dev
```

Dans un autre terminal, démarrer la base et l'API via Compose. Ne pas lancer le
service `frontend` de Compose en même temps sur le port 5173.

---

## Notes techniques

### Tests et base de données
Les tests utilisent une base **SQLite en mémoire** (avec `StaticPool`) pour garantir l'isolation et ne pas polluer la base PostgreSQL de développement. La production utilise PostgreSQL. Les requêtes SQL testées sont compatibles avec les deux moteurs.

## Chemin du fichier NOAA ONI (#31)

Le script `etl/import_oni.py` lit le chemin dans la variable d'environnement
`NOAA_ONI_FILEPATH`. Si elle est absente ou vide, le chemin par défaut est
`/app/data/oni.data`. Un appel explicite `main(filepath)` reste prioritaire.

### Avec Docker Compose (PowerShell)

Le dossier local `./data` est monté dans le conteneur sous `/app/data`.
Après avoir démarré la base et appliqué les migrations (démarrage rapide ci-dessus),
placez le fichier NOAA dans `./data/oni.data`, puis lancez :

```powershell
docker compose run --rm etl python import_oni.py
```

Pour utiliser un autre fichier, par exemple `./data/oni-alternative.data`,
indiquez son chemin **dans le conteneur** dans votre `.env` :

```dotenv
NOAA_ONI_FILEPATH=/app/data/oni-alternative.data
```

Ou surchargez la variable pour une seule exécution :

```powershell
docker compose run --rm -e NOAA_ONI_FILEPATH=/app/data/oni-alternative.data etl python import_oni.py
```

### Exécution locale Python (sans conteneur ETL)

Sous PowerShell, choisissez un chemin Windows avant de lancer le script :

```powershell
$env:NOAA_ONI_FILEPATH = (Resolve-Path .\data\oni.data).Path
$env:PYTHONPATH = (Resolve-Path .\api).Path
# Configurer aussi les variables POSTGRES_* pour une base locale accessible.
py -3 .\etl\import_oni.py
```

Un fichier `.env` est interprété par Docker Compose mais n'est pas chargé
automatiquement par Python en execution locale.

### Tests

```powershell
docker compose run --rm etl pytest tests -v
```

## Traçabilité des imports NOAA (#32)

- **Source officielle** : NOAA CPC, [fichier ONI](https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt), indice ONI calculé à partir d'ERSSTv6 (`version = v6`). La version est documentée, et non détectée automatiquement dans le fichier texte.
- **`Source.extracted_at`** : dernière date à laquelle l'ETL a terminé de lire le fichier local, enregistrée en UTC. Cette date est actualisée à chaque import, y compris sans changement de valeurs.
- **`Import.extracted_at`** : date de lecture propre à chaque exécution, conservée avec `row_count`, `checksum` SHA-256 et `imported_at`. Une date inconnue sur un import historique reste `NULL` (pas de date inventée).
- **Important** : l'ETL **ne télécharge pas** le fichier NOAA. Il ne connaît donc pas la date à laquelle tu l'as téléchargé depuis NOAA. `extracted_at` signifie ici « extraction par l'ETL depuis le fichier local », pas date de publication ni de téléchargement NOAA.
- **Réimport** : pour chaque couple `(indice, date)`, une nouvelle observation est insérée ; une valeur identique reste inchangée et conserve son `import_id` ; une valeur différente est **révisée** avec le nouvel `import_id`. Les dates absentes d'un fichier récent ne sont pas supprimées.
- **Limite d'audit** : le nouveau `checksum` permet de vérifier un fichier conservé, mais les anciennes valeurs écrasées ne sont pas historisées. Il faut conserver les fichiers NOAA originaux si une reconstitution exacte est nécessaire.
- **Horodatage API** : `provenance.extracted_at` vient de l'import associé à chaque observation. L'API renvoie aussi `provenance.checksum`. Si plusieurs dates d'extraction coexistent dans une période, `extracted_at` au niveau global est `null`.

### Migration PostgreSQL dans Docker Compose (#32)

Le service `api` lance automatiquement `alembic upgrade head` avant Uvicorn.
Pour rejouer cette commande manuellement depuis la racine du projet :

```powershell
docker compose run --rm api alembic upgrade head
```

Cette migration **ajoute** `imports.extracted_at` sans supprimer les observations existantes. Les anciens imports auront `extracted_at = NULL` car leur date de lecture exacte est inconnue.

### Vérifier la stratégie

```powershell
docker compose run --rm etl pytest tests -v
docker compose run --rm api pytest tests -v
```

Après avoir récupéré une nouvelle version officielle du fichier, remplacez le fichier local configuré (voir #31) et relancez :

```powershell
docker compose run --rm etl python import_oni.py
```
