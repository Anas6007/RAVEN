from sqlalchemy import select

from database.models.competition_request import CompetitionRequest
from repositories.base_repository import BaseRepository


class CompetitionRequestRepository(BaseRepository):

    async def create(self, **kwargs):
        item = CompetitionRequest(**kwargs)
        return await self.add(item)

    async def get_by_user(self, giveaway_id: int, user_id: int):
        result = await self.session.execute(
            select(CompetitionRequest).where(
                CompetitionRequest.giveaway_id == giveaway_id,
                CompetitionRequest.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get(self, request_id: int):
        result = await self.session.execute(
            select(CompetitionRequest).where(CompetitionRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def set_status(self, request_obj, status: str):
        request_obj.status = status
        await self.save()
        await self.refresh(request_obj)
        return request_obj
