# Source NOAA — Indice ONI

## Rôle

Donnée source du projet : valeurs de l'indice ONI (NOAA), importées en base via ETL, exposées par l'API, affichées dans le frontend.

## Source

- **Émetteur** : NOAA Climate Prediction Center (CPC)
- **Indice** : Oceanic Niño Index (ONI) — version 6 (ERSSTv6)
- **Page officielle** : https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/index.php
- **Fichier consommé** : https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt
- **Date d'extraction initiale documentée** : 2026-11-16 (ne concerne pas les futurs réimports)
- **Période couverte** : DJF 1950 → ASO 2026 (921 observations)

## Format

Fichier texte tabulaire, une ligne par saison (3 mois glissants) :

```
SEAS  YR   TOTAL   ANOM
 DJF 1950  25.01  -1.32
```

| Colonne | Signification | Utilisée |
|---|---|---|
| `SEAS` | Saison (DJF, JFM, …, NDJ) | Oui (convertie en date) |
| `YR` | Année | Oui |
| `TOTAL` | SST absolue (°C) | Non |
| `ANOM` | Anomalie ONI (°C) | **Oui** |

Chaque saison est convertie en date via son mois central (DJF → 1er janvier, JFM → 1er février, …, NDJ → 1er décembre).

## Précautions

- L'ONI mesure une anomalie de température dans la région Niño 3.4, pas un impact climatique.
- Aucune prévision n'est faite à partir de cette série.
- Le terme « Super El Niño » n'est pas utilisé.
- Les valeurs récentes sont des estimations, révisables par le NOAA.
## Traçabilité des réimports (#32)

La NOAA CPC met à jour la série ONI ; les valeurs les plus récentes peuvent être révisées. La version de calcul utilisée pour ce projet est **ERSSTv6** et le fichier source est `oni.ascii.txt`.

L'ETL lit un **fichier local** : l'horodatage `Import.extracted_at` est pris à la fin de cette lecture et non lors du téléchargement original depuis NOAA. Son fuseau est UTC. Une source créée par les migrations peut avoir une date ancienne ; elle est actualisée à la prochaine lecture de fichier, et seule la date **par import** sert à la provenance historique.

Chaque exécution crée une ligne `imports` avec la date de lecture (`extracted_at`), la date d'import (`imported_at`), le nombre de lignes (`row_count`) et le SHA-256 du fichier (`checksum`). L'API expose la provenance et ce checksum par observation.

Pour une même clé `(index_id, date)` :

1. **Nouvelle date** : insertion de l'observation avec le nouvel import.
2. **Valeur identique** : aucun doublon ; valeur et `import_id` existants conservés.
3. **Valeur révisée** : mise à jour de `value` et `import_id` vers l'import qui contient la révision.
4. **Date absente de la nouvelle version** : observation antérieure conservée.

La transaction reste atomique : un échec annule les insertions et les révisions. Un fichier avec deux lignes pour une même saison est rejeté.

**Limites** : l'ancienne valeur d'une observation révisée n'est pas conservée dans la table `observations`. Pour garder un historique exhaustif, archiver chaque fichier ONI avec son SHA-256, ou ajouter ultérieurement une table de révisions. Le checksum seul ne permet pas de retrouver un ancien fichier.

Les imports historiques antérieurs à cette migration ont `extracted_at = NULL` : leur horodatage d'extraction exacte n'était pas conservé. Ils restent consultables avec `imported_at`.
