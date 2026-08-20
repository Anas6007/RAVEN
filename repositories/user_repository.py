from sqlalchemy import select, func

from database.models.bot_user import BotUser
from repositories.base_repository import BaseRepository


class UserRepository(BaseRepository):

    async def remember(
        self,
        telegram_id: int,
        first_name: str | None = None,
        username: str | None = None,
    ):
        """يسجل مستخدمًا جديدًا أو يحدّث بياناته إن كان موجودًا بالفعل."""

        existing = await self.get_by_telegram_id(telegram_id)

        if existing:

            existing.first_name = first_name
            existing.username = username

            await self.save()
            await self.refresh(existing)

            return existing

        user = BotUser(
            telegram_id=telegram_id,
            first_name=first_name,
            username=username,
        )

        return await self.add(user)

    async def get_by_telegram_id(self, telegram_id: int):

        result = await self.session.execute(
            select(BotUser).where(
                BotUser.telegram_id == telegram_id,
            )
        )

        return result.scalar_one_or_none()

    async def get_all(self):

        result = await self.session.execute(
            select(BotUser).where(
                BotUser.is_banned.is_(False),
            )
        )

        return result.scalars().all()

    async def count(self) -> int:

        result = await self.session.execute(
            select(func.count()).select_from(BotUser)
        )

        return result.scalar_one()

    async def set_banned(self, telegram_id: int, banned: bool = True):

        user = await self.get_by_telegram_id(telegram_id)

        if user is None:
            return None

        user.is_banned = banned

        await self.save()
        await self.refresh(user)

        return user
