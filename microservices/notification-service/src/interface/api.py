"""FastAPI interface layer following CLAUDE.md 12-factor principles"""
import os
from fastapi import FastAPI, Depends
from pydantic import BaseModel

# 12-Factor: Config from environment
DATABASE_URL = os.getenv("DATABASE_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "")

app = FastAPI(
    title="notification-service",
    description="CLAUDE.md-compliant microservice with Onion Architecture",
    version="0.1.0"
)

class HealthResponse(BaseModel):
    status: str
    service: str

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for Kubernetes probes"""
    return HealthResponse(status="healthy", service="notification-service")

@app.get("/ready", response_model=HealthResponse)
async def readiness_check():
    """Readiness check endpoint for Kubernetes probes"""
    return HealthResponse(status="ready", service="notification-service")

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Hello from notification-service", "architecture": "onion"}
