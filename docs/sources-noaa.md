# Source NOAA — Indice ONI

## Rôle

Donnée source du projet : valeurs de l'indice ONI (NOAA), importées en base via ETL, exposées par l'API, affichées dans le frontend.

## Source

- **Émetteur** : NOAA Climate Prediction Center (CPC)
- **Indice** : Oceanic Niño Index (ONI) — version 6 (ERSSTv6)
- **Page officielle** : https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/index.php
- **Fichier consommé** : https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt
- **Date d'extraction** : 2026-11-16
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