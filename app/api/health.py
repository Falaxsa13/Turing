from fastapi import APIRouter
from app.core.responses import HealthCheckResponse
from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    return HealthCheckResponse(
        status="healthy",
        environment=settings.app_env,
        version="1.0.0",
        services={"api": "healthy", "database": "healthy"},
    )
