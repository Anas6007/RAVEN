from pyrogram.enums import ChatMemberStatus

import asyncio

from services.chat_service import ChatService


class SecurityEngine:

    def __init__(self, client):
        self.client = client

    @staticmethod
    def build_full_required_list(giveaway) -> list:
        """
        قائمة القنوات/المجموعات الواجب على المشارك الاشتراك بها فعليًا:
        قناة/مجموعة استضافة السحب نفسها أولًا، ثم قنوات الاشتراك الإجباري
        الإضافية. هذا يضمن أن المشارك عضو فعلي في الدردشة التي يُنشر فيها
        السحب، وليس فقط في القنوات الإضافية.
        """

        host_channel = {
            "id": giveaway.chat_id,
            "title": giveaway.chat_title,
            "link": giveaway.chat_link,
        }

        required = list(giveaway.required_channels or [])

        required = [
            channel for channel in required
            if channel.get("id") != giveaway.chat_id
        ]

        return [host_channel] + required

    async def check_membership(
        self,
        user_id: int,
        chat_id: int,
        chat_link: str | None = None,
    ) -> bool:
        """يتحقق من عضوية مستخدم واحد داخل دردشة واحدة."""

        try:

            try:
                member = await self.client.get_chat_member(chat_id, user_id)

            except Exception:
                await ChatService.ensure_resolved(self.client, chat_id, chat_link)
                member = await self.client.get_chat_member(chat_id, user_id)

            return member.status in (
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.OWNER,
            )

        except Exception:
            return False

    async def check_required_channels(
        self,
        user_id: int,
        channels: list,
    ):

        if not channels:
            return True, None

        # نفحص كل القنوات بالتوازي بدل واحدة تلو الأخرى — كل فحص هو نداء
        # شبكة مستقل لتيليجرام، فتنفيذها بالتوازي يقلّل زمن الانتظار من
        # (عدد القنوات × زمن نداء واحد) إلى زمن أبطأ نداء فقط تقريبًا.
        results = await asyncio.gather(
            *(
                self.check_membership(
                    user_id,
                    channel["id"],
                    channel.get("link"),
                )
                for channel in channels
            )
        )

        missing_channels = [
            channel
            for channel, ok in zip(channels, results)
            if not ok
        ]

        if missing_channels:
            return False, missing_channels

        return True, None
    async def is_authorized_manager(
        self,
        user_id: int,
        giveaway,
    ) -> bool:
        """
        هل يحق لهذا المستخدم إدارة السحب (سحب الفائزين / إيقاف المشاركة)؟
        يُسمح لمنشئ السحب، ولأي مشرف في القناة أو المجموعة التي نُشر فيها السحب.
        """

        if user_id == giveaway.owner_id:
            return True

        try:

            member = await self.client.get_chat_member(
                giveaway.chat_id,
                user_id,
            )

            return member.status in (
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.OWNER,
            )

        except Exception:
            return False
