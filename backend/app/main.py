from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="QuantForge POC API",
    description="Algorithmic trading research and paper-trading proof of concept.",
    version="0.1.0",
)

class HealthResponse(BaseModel):
    status: str
    app: str
    version: str

@app.get("/", tags=["System"])
def root():
    return {"message": "QuantForge POC API", "version": "0.1.0"}

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health():
    return HealthResponse(status="healthy", app="QuantForge POC", version="0.1.0")
