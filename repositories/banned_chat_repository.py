from sqlalchemy import select, func

from database.models.banned_chat import BannedChat
from repositories.base_repository import BaseRepository


class BannedChatRepository(BaseRepository):

    async def ban(
        self,
        chat_id: int,
        chat_title: str | None = None,
        reason: str | None = None,
        banned_by: int | None = None,
    ):

        existing = await self.get_one(chat_id)

        if existing:
            return existing

        banned = BannedChat(
            chat_id=chat_id,
            chat_title=chat_title,
            reason=reason,
            banned_by=banned_by,
        )

        return await self.add(banned)

    async def unban(self, chat_id: int) -> bool:

        existing = await self.get_one(chat_id)

        if existing is None:
            return False

        await self.delete(existing)

        return True

    async def get_one(self, chat_id: int):

        result = await self.session.execute(
            select(BannedChat).where(
                BannedChat.chat_id == chat_id,
            )
        )

        return result.scalar_one_or_none()

    async def is_banned(self, chat_id: int) -> bool:

        return await self.get_one(chat_id) is not None

    async def get_all(self):

        result = await self.session.execute(
            select(BannedChat).order_by(BannedChat.banned_at.desc())
        )

        return result.scalars().all()

    async def count(self) -> int:

        result = await self.session.execute(
            select(func.count()).select_from(BannedChat)
        )

        return result.scalar_one()
