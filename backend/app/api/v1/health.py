"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Application health check — returns service status."""
    return {
        "status": "healthy",
        "service": "quantedge-api",
        "version": "0.1.0",
    }
