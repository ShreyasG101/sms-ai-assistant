"""Health check endpoint."""

from fastapi import APIRouter, Depends

from app.dependencies import get_outbox_repo
from app.models.common import HealthResponse
from app.repositories.outbox import OutboxRepository

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
async def health_check(
    outbox_repo: OutboxRepository = Depends(get_outbox_repo),
) -> HealthResponse:
    """Health check endpoint."""
    pending = await outbox_repo.get_pending_count()
    return HealthResponse(status="ok", pending_outbox=pending)
