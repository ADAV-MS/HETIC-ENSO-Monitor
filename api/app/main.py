from fastapi import FastAPI
from .routes import observations

app = FastAPI(
    title="ENSO Monitor API",
    version="0.1.0",
    description="API de consultation des observations ONI du NOAA CPC."
)

@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

# On branche la route
app.include_router(observations.router, prefix="/api/v1", tags=["Observations"])