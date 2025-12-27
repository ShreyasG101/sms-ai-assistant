"""SMS request/response models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class IncomingSMSRequest(BaseModel):
    """Incoming SMS from httpSMS."""

    from_number: str = Field(alias="from")
    to: str | None = None
    content: str
    timestamp: datetime | None = None
    id: str | None = None  # httpSMS message ID

    model_config = {"populate_by_name": True}


class OutboxMessageResponse(BaseModel):
    """Pending outgoing message for phone to send."""

    id: int
    to: str
    content: str
    created_at: datetime


class OutgoingMessagesResponse(BaseModel):
    """Response for GET /api/sms/outgoing."""

    messages: list[OutboxMessageResponse]


class AckRequest(BaseModel):
    """Acknowledge message sent/failed."""

    status: Literal["sent", "failed"]
    sent_at: datetime | None = None
