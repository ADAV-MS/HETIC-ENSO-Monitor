import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import observations

app = FastAPI(
    title="ENSO Monitor API",
    version="0.1.0",
    description="API de consultation des observations ONI du NOAA CPC."
)

# Récupère les origines depuis .env (séparées par virgule si multiple)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

app.include_router(observations.router, prefix="/api/v1", tags=["Observations"])