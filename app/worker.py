from __future__ import annotations

import asyncio
import logging

from app.config import get_settings
from app.db import AsyncSessionLocal
from app.services.email_service import get_email_service
from app.services.job_service import JobService
from app.tasks.booking_tasks import send_balance_due_reminder


logger = logging.getLogger(__name__)


async def run_worker() -> None:
    settings = get_settings()
    job_service = JobService()
    email_service = get_email_service()
    while True:
        async with AsyncSessionLocal() as db:
            job = await job_service.claim_next_ready_job(db)
            if job is None:
                await asyncio.sleep(settings.worker_poll_interval_seconds)
                continue
            try:
                if job.queue == "booking.balance_due_reminder":
                    await send_balance_due_reminder(
                        db,
                        email_service,
                        job.payload["booking_id"],
                        job.payload.get("email", "customer@example.com"),
                    )
                await job_service.mark_completed(db, job)
            except Exception as exc:  # pragma: no cover
                logger.exception("worker job failed", exc_info=exc)
                await job_service.mark_failed(db, job, str(exc))
        await asyncio.sleep(0)


def main() -> None:
    asyncio.run(run_worker())
