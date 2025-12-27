"""Common response models."""

from pydantic import BaseModel


class OkResponse(BaseModel):
    """Generic success response."""

    ok: bool = True


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    pending_outbox: int
