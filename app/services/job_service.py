from __future__ import annotations

import socket
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import JobQueue, JobStatus


class JobService:
    async def enqueue(
        self,
        db: AsyncSession,
        queue: str,
        payload: dict,
        delay_seconds: int = 0,
        max_attempts: int = 5,
    ) -> JobQueue:
        job = JobQueue(
            queue=queue,
            payload=payload,
            run_at=datetime.now(timezone.utc) + timedelta(seconds=delay_seconds),
            max_attempts=max_attempts,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    async def claim_next_ready_job(self, db: AsyncSession) -> Optional[JobQueue]:
        statement = (
            select(JobQueue)
            .where(
                and_(
                    JobQueue.status == JobStatus.queued,
                    JobQueue.run_at <= datetime.now(timezone.utc),
                )
            )
            .order_by(JobQueue.run_at.asc())
            .limit(1)
        )
        result = await db.execute(statement)
        job = result.scalar_one_or_none()
        if job is None:
            return None
        job.status = JobStatus.processing
        job.locked_at = datetime.now(timezone.utc)
        job.locked_by = socket.gethostname()
        job.attempts += 1
        await db.commit()
        await db.refresh(job)
        return job

    async def mark_completed(self, db: AsyncSession, job: JobQueue) -> None:
        job.status = JobStatus.completed
        await db.commit()

    async def mark_failed(self, db: AsyncSession, job: JobQueue, error: str) -> None:
        job.last_error = error
        if job.attempts >= job.max_attempts:
            job.status = JobStatus.failed
        else:
            job.status = JobStatus.queued
            job.run_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        await db.commit()
