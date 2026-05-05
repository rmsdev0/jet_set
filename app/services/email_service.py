from __future__ import annotations

import logging
from typing import Any

from app.config import Settings, get_settings


logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send_email(self, to_email: str, subject: str, html: str, metadata: dict[str, Any] | None = None) -> None:
        logger.info("email.send to=%s subject=%s metadata=%s", to_email, subject, metadata or {})


def get_email_service() -> EmailService:
    return EmailService(get_settings())
