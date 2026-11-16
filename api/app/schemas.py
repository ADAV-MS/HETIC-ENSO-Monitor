from pydantic import BaseModel, ConfigDict, Field, model_validator
from datetime import date, datetime

class ObservationFilter(BaseModel):
    start: date = Field(..., description="Date de début (YYYY-MM-DD)")
    end: date = Field(..., description="Date de fin (YYYY-MM-DD)")

    @model_validator(mode='after')
    def check_dates(self):
        if self.start > self.end:
            raise ValueError("La date de début doit être antérieure à la date de fin.")
        return self

class ObservationOut(BaseModel):
    date: date
    value: float
    model_config = ConfigDict(from_attributes=True)

class ObservationsResponse(BaseModel):
    source: str
    indice: str
    unit: str
    version: str
    extracted_at: datetime
    observations: list[ObservationOut]