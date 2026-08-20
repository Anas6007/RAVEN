from sqlalchemy import select

from database.models.linked_chat import LinkedChat
from repositories.base_repository import BaseRepository


class LinkedChatRepository(BaseRepository):

    async def remember(
        self,
        owner_id: int,
        chat_id: int,
        chat_type: str,
        chat_title: str,
        chat_link: str | None = None,
    ):

        existing = await self.get_one(owner_id, chat_id)

        if existing:

            existing.chat_title = chat_title
            existing.chat_type = chat_type
            existing.chat_link = chat_link

            await self.save()
            await self.refresh(existing)

            return existing

        linked = LinkedChat(
            owner_id=owner_id,
            chat_id=chat_id,
            chat_type=chat_type,
            chat_title=chat_title,
            chat_link=chat_link,
        )

        return await self.add(linked)

    async def get_one(self, owner_id: int, chat_id: int):

        result = await self.session.execute(
            select(LinkedChat).where(
                LinkedChat.owner_id == owner_id,
                LinkedChat.chat_id == chat_id,
            )
        )

        return result.scalar_one_or_none()

    async def get_by_owner(self, owner_id: int):

        result = await self.session.execute(
            select(LinkedChat)
            .where(LinkedChat.owner_id == owner_id)
            .order_by(LinkedChat.updated_at.desc())
        )

        return result.scalars().all()
