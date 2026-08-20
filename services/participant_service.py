from sqlalchemy.exc import IntegrityError

from repositories.participant_repository import ParticipantRepository


class ParticipantService:

    def __init__(
        self,
        repository: ParticipantRepository,
    ):
        self.repository = repository

    async def join(
        self,
        giveaway_id: int,
        user,
    ):

        exists = await self.repository.get_by_user(
            giveaway_id,
            user.id,
        )

        if exists:
            return exists

        try:

            return await self.repository.create(

                giveaway_id=giveaway_id,

                user_id=user.id,

                first_name=user.first_name,

                username=user.username,

                passed_captcha=False,

            )

        except IntegrityError:
            # سباق نادر: ضغطتان متزامنتان سجّلتا المستخدم في نفس اللحظة.
            # القيد الفريد بقاعدة البيانات منع التكرار، فقط نُعيد السجل
            # الموجود فعليًا بدل رفع الخطأ للمستخدم.

            await self.repository.session.rollback()

            return await self.repository.get_by_user(
                giveaway_id,
                user.id,
            )

    async def count(
        self,
        giveaway_id: int,
    ):

        return await self.repository.count(
            giveaway_id
        )