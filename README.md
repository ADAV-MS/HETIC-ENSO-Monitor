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

## Traçabilité des imports NOAA (#32)

- **Source officielle** : NOAA CPC, [fichier ONI](https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt), indice ONI calculé à partir d'ERSSTv6 (`version = v6`). La version est documentée, et non détectée automatiquement dans le fichier texte.
- **`Source.extracted_at`** : dernière date à laquelle l'ETL a terminé de lire le fichier local, enregistrée en UTC. Cette date est actualisée à chaque import, y compris sans changement de valeurs.
- **`Import.extracted_at`** : date de lecture propre à chaque exécution, conservée avec `row_count`, `checksum` SHA-256 et `imported_at`. Une date inconnue sur un import historique reste `NULL` (pas de date inventée).
- **Important** : l'ETL **ne télécharge pas** le fichier NOAA. Il ne connaît donc pas la date à laquelle tu l'as téléchargé depuis NOAA. `extracted_at` signifie ici « extraction par l'ETL depuis le fichier local », pas date de publication ni de téléchargement NOAA.
- **Réimport** : pour chaque couple `(indice, date)`, une nouvelle observation est insérée ; une valeur identique reste inchangée et conserve son `import_id` ; une valeur différente est **révisée** avec le nouvel `import_id`. Les dates absentes d'un fichier récent ne sont pas supprimées.
- **Limite d'audit** : le nouveau `checksum` permet de vérifier un fichier conservé, mais les anciennes valeurs écrasées ne sont pas historisées. Il faut conserver les fichiers NOAA originaux si une reconstitution exacte est nécessaire.
- **Horodatage API** : `provenance.extracted_at` vient de l'import associé à chaque observation. L'API renvoie aussi `provenance.checksum`. Si plusieurs dates d'extraction coexistent dans une période, `extracted_at` au niveau global est `null`.

### Migration PostgreSQL nécessaire avant de lancer #32

Depuis la racine du projet :

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
