"""Configuration du chemin du fichier ONI utilisé par l'ETL."""

import os

NOAA_ONI_FILEPATH_ENV = "NOAA_ONI_FILEPATH"
DEFAULT_NOAA_ONI_FILEPATH = "/app/data/oni.data"


def obtenir_chemin_fichier_oni() -> str:
    """Lit le chemin à chaque import, avec une valeur par défaut pour Docker."""
    return os.getenv(NOAA_ONI_FILEPATH_ENV) or DEFAULT_NOAA_ONI_FILEPATH
