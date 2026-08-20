from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, instance):
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance):
        await self.session.delete(instance)
        await self.session.commit()

    async def save(self):
        await self.session.commit()

    async def refresh(self, instance):
        await self.session.refresh(instance)

    async def get_by_id(self, model, object_id):
        result = await self.session.execute(
            select(model).where(model.id == object_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, model):
        result = await self.session.execute(
            select(model)
        )
        return result.scalars().all()