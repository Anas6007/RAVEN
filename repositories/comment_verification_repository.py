from sqlalchemy import delete, select

from database.models.comment_verification import CommentVerification
from repositories.base_repository import BaseRepository


class CommentVerificationRepository(BaseRepository):

    async def remember(self, giveaway_id: int, user_id: int):
        existing = await self.get_one(giveaway_id, user_id)
        if existing:
            return existing

        item = CommentVerification(
            giveaway_id=giveaway_id,
            user_id=user_id,
        )
        return await self.add(item)

    async def get_one(self, giveaway_id: int, user_id: int):
        result = await self.session.execute(
            select(CommentVerification).where(
                CommentVerification.giveaway_id == giveaway_id,
                CommentVerification.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def exists(self, giveaway_id: int, user_id: int) -> bool:
        return await self.get_one(giveaway_id, user_id) is not None

    async def clear_giveaway(self, giveaway_id: int):
        await self.session.execute(
            delete(CommentVerification).where(
                CommentVerification.giveaway_id == giveaway_id
            )
        )
        await self.save()
