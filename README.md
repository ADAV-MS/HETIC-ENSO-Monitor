# ENSO Monitor

Application d'analyse des épisodes ENSO à partir de l'indice ONI du NOAA CPC

## Notes techniques

### Tests et base de données
Les tests utilisent une base **SQLite en mémoire** (avec `StaticPool`) pour garantir l'isolation et ne pas polluer la base PostgreSQL de développement. La production utilise PostgreSQL. Les requêtes SQL testées sont compatibles avec les deux moteurs.

## Chemin du fichier NOAA ONI (#31)

Le script `etl/import_oni.py` lit le chemin dans la variable d'environnement
`NOAA_ONI_FILEPATH`. Si elle est absente ou vide, le chemin par défaut est
`/app/data/oni.data`. Un appel explicite `main(filepath)` reste prioritaire.

### Avec Docker Compose (PowerShell)

Le dossier local `./data` est monté dans le conteneur sous `/app/data`.
Placez le fichier NOAA dans `./data/oni.data`, puis lancez :

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
