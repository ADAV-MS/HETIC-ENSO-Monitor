from pydantic import BaseModel, ConfigDict
from datetime import date, datetime

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