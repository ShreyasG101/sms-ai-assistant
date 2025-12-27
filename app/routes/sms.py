"""SMS endpoints for httpSMS integration."""

import logging

from fastapi import APIRouter, Depends, Header

from app.core.config import Settings, get_settings
from app.dependencies import get_sms_service
from app.models.common import OkResponse
from app.models.sms import (
    AckRequest,
    IncomingSMSRequest,
    OutboxMessageResponse,
    OutgoingMessagesResponse,
)
from app.services.sms import SMSService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sms", tags=["sms"])


@router.post("/incoming", response_model=OkResponse)
async def receive_sms(
    request: IncomingSMSRequest,
    sms_service: SMSService = Depends(get_sms_service),
    x_api_key: str | None = Header(None),
    settings: Settings = Depends(get_settings),
) -> OkResponse:
    """
    Receive incoming SMS from httpSMS.

    - Validates API key if configured
    - Delegates to SMSService.process_incoming()
    - Always returns 200 OK (even for unauthorized - silent ignore)
    """
    # API key check if configured
    if settings.sms_api_key and x_api_key != settings.sms_api_key:
        logger.warning("SMS request with invalid API key")
        return OkResponse(ok=False)

    await sms_service.process_incoming(
        phone_number=request.from_number,
        content=request.content,
        timestamp=request.timestamp,
    )

    return OkResponse(ok=True)


@router.get("/outgoing", response_model=OutgoingMessagesResponse)
async def get_outgoing(
    sms_service: SMSService = Depends(get_sms_service),
) -> OutgoingMessagesResponse:
    """Phone polls for pending messages to send."""
    messages = await sms_service.get_outgoing_messages()

    return OutgoingMessagesResponse(
        messages=[
            OutboxMessageResponse(
                id=msg.id,
                to=msg.phone_number,
                content=msg.content,
                created_at=msg.created_at,
            )
            for msg in messages
        ]
    )


@router.post("/outgoing/{message_id}/ack", response_model=OkResponse)
async def acknowledge_sent(
    message_id: int,
    request: AckRequest,
    sms_service: SMSService = Depends(get_sms_service),
) -> OkResponse:
    """Phone confirms message was sent."""
    await sms_service.acknowledge_sent(message_id, request.status)
    return OkResponse(ok=True)
