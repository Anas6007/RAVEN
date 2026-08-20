from sqlalchemy import case, func, select

from database.models.giveaway import Giveaway
from repositories.base_repository import BaseRepository


class GiveawayRepository(BaseRepository):

    # ---------------------------------
    # إنشاء سحب
    # ---------------------------------

    async def create(self, **kwargs):

        giveaway = Giveaway(**kwargs)

        return await self.add(giveaway)

    # ---------------------------------
    # الحصول على سحب
    # ---------------------------------

    async def get(self, giveaway_id: int):

        result = await self.session.execute(
            select(Giveaway).where(
                Giveaway.id == giveaway_id
            )
        )

        return result.scalar_one_or_none()

    # ---------------------------------
    # جميع السحوبات
    # ---------------------------------

    async def get_all(self):

        result = await self.session.execute(
            select(Giveaway).order_by(
                Giveaway.id.desc()
            )
        )

        return result.scalars().all()

    # ---------------------------------
    # إحصائيات مجمّعة (بدون تحميل كل السحوبات للذاكرة)
    # ---------------------------------

    async def get_stats(self):

        result = await self.session.execute(
            select(
                func.count(Giveaway.id),
                func.coalesce(
                    func.sum(case((Giveaway.is_active.is_(True), 1), else_=0)),
                    0,
                ),
                func.coalesce(func.sum(Giveaway.participants_count), 0),
            )
        )

        total, active, participants = result.one()

        return {
            "total": total,
            "active": active,
            "participants": participants,
        }

    # ---------------------------------
    # السحوبات النشطة
    # ---------------------------------

    async def get_active(self):

        result = await self.session.execute(
            select(Giveaway).where(
                Giveaway.is_active.is_(True)
            )
        )

        return result.scalars().all()

    # ---------------------------------
    # حسب المالك
    # ---------------------------------

    async def get_by_owner(self, owner_id: int, flow_kind: str | None = None):

        stmt = select(Giveaway).where(Giveaway.owner_id == owner_id)

        if flow_kind is not None:
            stmt = stmt.where(Giveaway.flow_kind == flow_kind)

        result = await self.session.execute(stmt)

        return result.scalars().all()

    # ---------------------------------
    # حسب الدردشة
    # ---------------------------------

    async def get_by_chat(self, chat_id: int, flow_kind: str | None = None):

        stmt = select(Giveaway).where(Giveaway.chat_id == chat_id)

        if flow_kind is not None:
            stmt = stmt.where(Giveaway.flow_kind == flow_kind)

        result = await self.session.execute(stmt)

        return result.scalars().all()

    # ---------------------------------
    # تحديث
    # ---------------------------------

    async def update(self, giveaway, **kwargs):

        for key, value in kwargs.items():

            if hasattr(giveaway, key):
                setattr(giveaway, key, value)

        await self.save()
        await self.refresh(giveaway)

        return giveaway

    # ---------------------------------
    # تحديث message_id
    # ---------------------------------

    async def update_message_id(
        self,
        giveaway,
        message_id: int,
    ):

        giveaway.message_id = message_id

        await self.save()
        await self.refresh(giveaway)

        return giveaway

    # ---------------------------------
    # إيقاف السحب
    # ---------------------------------

    async def finish(self, giveaway):

        giveaway.is_active = False

        await self.save()
        await self.refresh(giveaway)

        return giveaway

    # ---------------------------------
    # إعادة فتح السحب
    # ---------------------------------

    async def reopen(self, giveaway):

        giveaway.is_active = True

        await self.save()
        await self.refresh(giveaway)

        return giveaway

    # ---------------------------------
    # تحديث عدد المشاركين
    # ---------------------------------

    async def update_participants_count(
        self,
        giveaway,
        count: int,
    ):

        giveaway.participants_count = count

        await self.save()
        await self.refresh(giveaway)

        return giveaway

    # ---------------------------------
    # حذف
    # ---------------------------------

    async def delete_by_id(self, giveaway_id: int):

        giveaway = await self.get(giveaway_id)

        if giveaway:
            await self.delete(giveaway)