import asyncio
from random import SystemRandom

from repositories.giveaway_repository import GiveawayRepository
from repositories.participant_repository import ParticipantRepository
from services.engines.security_engine import SecurityEngine


class DrawEngine:
    """محرك اختيار الفائزين أو أفضل متسابقين حسب نوع التدفق."""

    # مولّد عشوائي آمن تشفيريًا (يعتمد على os.urandom) بدل مولّد
    # random العادي (Mersenne Twister)، لأن اختيار فائزي السحب يجب أن
    # يكون غير قابل للتنبؤ به حتى لو تسرّبت حالة المولّد الداخلية.
    _rng = SystemRandom()

    def __init__(self, session, client=None):
        self.session = session
        self.client = client
        self.giveaways = GiveawayRepository(session)
        self.participants = ParticipantRepository(session)

    async def _eligible_participant(self, giveaway, participant) -> bool:
        if self.client is None:
            return True

        security = SecurityEngine(self.client)
        required = SecurityEngine.build_full_required_list(giveaway)

        ok, _missing = await security.check_required_channels(
            participant.user_id,
            required
        )

        return ok

    async def draw(self, giveaway_id: int):
        giveaway = await self.giveaways.get(giveaway_id)

        if giveaway is None:
            return False, 'السحب غير موجود.'

        available = await self.participants.get_available(giveaway_id)

        if self.client is not None:
            results = await asyncio.gather(
                *(self._eligible_participant(giveaway, p) for p in available)
            )

            available = [
                p for p, ok in zip(available, results)
                if ok
            ]

        if not available:
            if giveaway.drawn_once:
                return False, 'تم سحب جميع المشاركين بالفعل، لا يوجد المزيد.'

            return False, 'لا يوجد مشاركون بعد.'

        if getattr(giveaway, 'flow_kind', 'giveaway') == 'competition':

            winners_count = min(
                giveaway.winners_count or 1,
                len(available)
            )

            winners = await self.participants.get_top_by_votes(
                giveaway_id,
                winners_count
            )

            if not winners:
                winners = available[:winners_count]

        else:

            winners_count = min(
                giveaway.winners_count,
                len(available)
            )

            winners = self._rng.sample(
                available,
                winners_count
            )

        for participant in winners:
            await self.participants.mark_winner(participant)

        remaining = await self.participants.get_available(giveaway_id)

        await self.giveaways.update(
            giveaway,
            drawn_once=True
        )

        if getattr(giveaway, 'flow_kind', 'giveaway') == 'competition':
            await self.giveaways.finish(giveaway)

        elif not remaining:
            await self.giveaways.finish(giveaway)


        # حل الاستيراد الدائري
        if (
            getattr(giveaway, 'flow_kind', 'giveaway') == 'competition'
            and self.client is not None
        ):
            try:
                from services.competition_flow import close_competition_participant_buttons

                await close_competition_participant_buttons(
                    self.client,
                    giveaway,
                    await self.participants.get_all(giveaway_id)
                )

            except Exception:
                pass


        return True, (
            giveaway,
            winners,
            len(remaining) > 0
        )
