"""
Health Check Endpoints
"""
from fastapi import APIRouter
from schema import HealthCheckResponse
from utils import get_timestamp

router = APIRouter(prefix="", tags=["health"])

@router.get("/", response_model=HealthCheckResponse)
async def root():
    """Root health check endpoint"""
    return HealthCheckResponse(
        status="healthy",
        version="0.1.0",
        timestamp=get_timestamp()
    )

@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Detailed health check endpoint"""
    return HealthCheckResponse(
        status="healthy",
        version="0.1.0",
        timestamp=get_timestamp()
    )