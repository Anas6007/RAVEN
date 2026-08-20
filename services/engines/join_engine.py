from repositories.giveaway_repository import GiveawayRepository
from repositories.participant_repository import ParticipantRepository

from services.engines.security_engine import SecurityEngine
from services.participant_service import ParticipantService
from config import logger


class JoinEngine:

    def __init__(self, client, session):

        self.client = client
        self.session = session

        self.giveaways = GiveawayRepository(session)
        self.participants = ParticipantRepository(session)

        self.security = SecurityEngine(client)

    async def complete_join(
        self,
        giveaway_id: int,
        user,
    ):

        participant_service = ParticipantService(self.participants)

        await participant_service.join(
            giveaway_id,
            user,
        )

        giveaway = await self.giveaways.get(giveaway_id)

        count = await participant_service.count(giveaway_id)

        giveaway = await self.giveaways.update(
            giveaway,
            participants_count=count,
        )

        return giveaway, count

    async def maybe_auto_draw_by_count(self, giveaway):
        """
        إن كان السحب من نوع "تلقائي عند وصول عدد معين" ووصل عدد
        المشاركين للحد المطلوب، يقوم تلقائيًا بسحب الفائزين وإعلانهم.
        """

        if not giveaway.is_active:
            return None

        if giveaway.mode != "auto" or giveaway.auto_trigger != "count":
            return None

        if not giveaway.auto_threshold:
            return None

        if giveaway.participants_count < giveaway.auto_threshold:
            return None

        from services.engines.draw_engine import DrawEngine
        from bot.keyboards.giveaway import giveaway_keyboard

        engine = DrawEngine(self.session, self.client)

        success, result = await engine.draw(giveaway.id)

        if not success:
            return None

        giveaway_obj, winners, has_more = result

        lines = ["🏆 **تم الوصول للعدد المطلوب من المشاركين — نتائج السحب**\n"]

        for i, winner in enumerate(winners, 1):
            name = f"@{winner.username}" if winner.username else winner.first_name
            lines.append(f"{i}. {name}")

        text = "\n".join(lines)

        from utils.safe_edit import safe_client_edit_reply_markup
        from utils.broadcast import notify_users

        try:

            await self.client.send_message(
                chat_id=giveaway_obj.chat_id,
                text=text,
            )

            await safe_client_edit_reply_markup(
                self.client,
                giveaway_obj.chat_id,
                giveaway_obj.message_id,
                giveaway_keyboard(
                    giveaway_obj.id,
                    giveaway_obj.participants_count,
                    giveaway_obj.is_active,
                    giveaway_obj.drawn_once,
                    management=getattr(giveaway_obj, 'flow_kind', 'giveaway') != 'competition',
                    flow_kind=getattr(giveaway_obj, 'flow_kind', 'giveaway'),
                    contestant_slots=getattr(giveaway_obj, 'contestant_slots', None),
                ),
            )

        except Exception as e:
            logger.warning("AUTO DRAW NOTIFY ERROR: {}", repr(e))

        await notify_users(
            self.client,
            [winner.user_id for winner in winners],
            lambda _uid: {
                "text": (
                    "🎉 مبروك! لقد فزت في السحب.\n\n"
                    f"📢 القناة/المجموعة: {giveaway_obj.chat_title}\n\n"
                    "سيتواصل معك منظّم السحب قريبًا بخصوص جائزتك."
                )
            },
            context=f"auto-draw-count giveaway#{giveaway_obj.id}",
        )

        return giveaway_obj
