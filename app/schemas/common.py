from __future__ import annotations

from datetime import datetime
from typing import Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    detail: str


class CursorPageMeta(BaseModel):
    next_cursor: Optional[str] = None


T = TypeVar("T")


class CursorPage(BaseModel, Generic[T]):
    items: List[T]
    meta: CursorPageMeta


class TimestampedModel(ORMModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
