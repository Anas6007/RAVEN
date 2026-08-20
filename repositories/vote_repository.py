from sqlalchemy import func, select

from database.models.vote import Vote
from repositories.base_repository import BaseRepository


class VoteRepository(BaseRepository):

    async def create(self, **kwargs):
        vote = Vote(**kwargs)
        return await self.add(vote)

    async def get_by_voter(self, giveaway_id: int, voter_user_id: int):
        result = await self.session.execute(
            select(Vote).where(
                Vote.giveaway_id == giveaway_id,
                Vote.voter_user_id == voter_user_id,
            )
        )
        return result.scalar_one_or_none()


    async def count_for_giveaway(self, giveaway_id: int):
        result = await self.session.execute(
            select(func.count()).select_from(Vote).where(Vote.giveaway_id == giveaway_id)
        )
        return result.scalar_one()
