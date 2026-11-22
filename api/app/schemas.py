from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator


class ObservationFilter(BaseModel):
    start: date = Field(..., description="Date de début (YYYY-MM-DD)")
    end: date = Field(..., description="Date de fin (YYYY-MM-DD)")

    @model_validator(mode="after")
    def check_dates(self):
        if self.start > self.end:
            raise ValueError("La date de début doit être antérieure à la date de fin.")
        return self


class ProvenanceOut(BaseModel):
    source_id: int
    source: str
    source_url: str
    version: str
    extracted_at: datetime | None
    import_id: int
    imported_at: datetime | None
    checksum: str | None = None
    indice_code: str
    indice: str
    unit: str


class ObservationOut(BaseModel):
    date: date
    value: float
    provenance: ProvenanceOut


class ObservationsResponse(BaseModel):
    # null si la période est vide ou si plusieurs provenances sont présentes.
    source: str | None
    indice: str | None
    unit: str | None
    version: str | None
    extracted_at: datetime | None
    observations: list[ObservationOut]
