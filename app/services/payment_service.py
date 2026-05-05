from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass

from app.config import Settings, get_settings


@dataclass
class PaymentIntentResult:
    id: str
    client_secret: str


@dataclass
class RefundResult:
    id: str
    amount: int


@dataclass
class AccountResult:
    id: str
    onboarding_url: str


class PaymentService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def create_lodge_account(self, lodge_name: str, owner_email: str, slug: str) -> AccountResult:
        account_id = f"acct_{uuid.uuid4().hex[:18]}"
        onboarding_url = (
            f"{self.settings.app_url}/lodge-admin/stripe/onboarding?account_id={account_id}&slug={slug}&email={owner_email}"
        )
        return AccountResult(id=account_id, onboarding_url=onboarding_url)

    async def create_booking_payment(
        self, booking_id: str, amount: int, platform_fee: int, payment_type: str
    ) -> PaymentIntentResult:
        suffix = uuid.uuid4().hex[:18]
        return PaymentIntentResult(
            id=f"pi_{suffix}",
            client_secret=f"pi_{suffix}_secret_{booking_id}_{payment_type}_{amount}_{platform_fee}",
        )

    async def process_refund(self, payment_intent_id: str, amount: int) -> RefundResult:
        return RefundResult(id=f"re_{uuid.uuid4().hex[:18]}", amount=amount)

    def verify_webhook_signature(self, payload: bytes, signature: str | None) -> bool:
        if not self.settings.stripe_webhook_secret:
            return True
        if not signature:
            return False
        expected = hmac.new(
            self.settings.stripe_webhook_secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected)

    def parse_webhook(self, payload: bytes) -> dict:
        return json.loads(payload.decode("utf-8"))


def get_payment_service() -> PaymentService:
    return PaymentService(get_settings())
