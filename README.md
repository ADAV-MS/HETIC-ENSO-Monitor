# ENSO Monitor

Application d'analyse des épisodes ENSO à partir de l'indice ONI du NOAA CPC

## Notes techniques

### Tests et base de données
Les tests utilisent une base **SQLite en mémoire** (avec `StaticPool`) pour garantir l'isolation et ne pas polluer la base PostgreSQL de développement. La production utilise PostgreSQL. Les requêtes SQL testées sont compatibles avec les deux moteurs.