from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.search import LodgeSearchParams
from app.services.lodge_service import LodgeService


class SearchService:
    def __init__(self, lodge_service: LodgeService | None = None) -> None:
        self.lodge_service = lodge_service or LodgeService()

    async def search_lodges(self, db: AsyncSession, params: LodgeSearchParams):
        return await self.lodge_service.search_lodges(db, params)


def get_search_service() -> SearchService:
    return SearchService()
