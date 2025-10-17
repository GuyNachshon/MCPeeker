"""
Health check API endpoints

Reference: Phase 8 (Production readiness), T126
"""

from fastapi import APIRouter

from ..health import health_checker

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint.

    Returns service health status including:
    - PostgreSQL connectivity
    - ClickHouse connectivity
    - NATS connectivity

    Used by Kubernetes liveness/readiness probes.
    """
    return await health_checker.check_all()


@router.get("/health/live")
async def liveness_check():
    """
    Liveness probe - is the service running?

    This is a minimal check that the service is alive.
    Does not check dependencies.
    """
    return {
        "status": "alive",
        "service": "registry-api",
    }


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness probe - is the service ready to serve traffic?

    Checks that all dependencies are available.
    """
    health_status = await health_checker.check_all()

    # Return 503 if not healthy
    if health_status["status"] != "healthy":
        from fastapi import Response
        return Response(
            content=str(health_status),
            status_code=503,
            media_type="application/json",
        )

    return {
        "status": "ready",
        "service": "registry-api",
        "checks": health_status["checks"],
    }
