"""Build the public observations response from repository results."""

from sqlalchemy.orm import Session

from ..repositories.observations import lister_observations
from ..schemas import ObservationFilter, ObservationOut, ObservationsResponse, ProvenanceOut


def construire_reponse_observations(
    db: Session, filtres: ObservationFilter
) -> ObservationsResponse:
    """Preserve per-observation provenance and avoid arbitrary global metadata."""
    observations = lister_observations(db, filtres.start, filtres.end)
    resultats: list[ObservationOut] = []
    couples_source_indice: set[tuple[int, int]] = set()

    for observation in observations:
        import_record = observation.import_record
        source = import_record.source
        indice = observation.indice
        couples_source_indice.add((source.id, indice.id))

        resultats.append(
            ObservationOut(
                date=observation.date,
                value=observation.value,
                provenance=ProvenanceOut(
                    source_id=source.id,
                    source=source.name,
                    source_url=source.url,
                    version=source.version,
                    extracted_at=source.extracted_at,
                    import_id=import_record.id,
                    imported_at=import_record.imported_at,
                    indice_code=indice.code,
                    indice=indice.label,
                    unit=indice.unit,
                ),
            )
        )

    # Global metadata only describes a period covered by one source/index pair.
    metadata = resultats[0].provenance if len(couples_source_indice) == 1 else None

    return ObservationsResponse(
        source=metadata.source if metadata else None,
        indice=metadata.indice if metadata else None,
        unit=metadata.unit if metadata else None,
        version=metadata.version if metadata else None,
        extracted_at=metadata.extracted_at if metadata else None,
        observations=resultats,
    )
