from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_booking_service_dep, get_db
from app.models import ProcessedWebhookEvent
from app.services.booking_service import BookingService
from app.services.payment_service import PaymentService, get_payment_service


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    booking_service: BookingService = Depends(get_booking_service_dep),
    payment_service: PaymentService = Depends(get_payment_service),
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
):
    payload = await request.body()
    if not payment_service.verify_webhook_signature(payload, stripe_signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")
    event = payment_service.parse_webhook(payload)
    if (
        await db.execute(
            select(ProcessedWebhookEvent).where(
                ProcessedWebhookEvent.provider == "stripe", ProcessedWebhookEvent.event_id == event["id"]
            )
        )
    ).scalar_one_or_none():
        return {"status": "ignored"}

    event_type = event["type"]
    intent_id = event.get("data", {}).get("object", {}).get("id")
    if event_type == "payment_intent.succeeded" and intent_id:
        await booking_service.mark_payment_succeeded(db, intent_id)
    elif event_type == "payment_intent.payment_failed" and intent_id:
        await booking_service.mark_payment_failed(db, intent_id)

    db.add(
        ProcessedWebhookEvent(
            provider="stripe",
            event_id=event["id"],
            event_type=event_type,
            payload=event,
        )
    )
    await db.commit()
    return {"status": "ok"}
