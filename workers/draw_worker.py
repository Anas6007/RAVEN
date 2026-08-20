"""
worker للسحب التلقائي عند انتهاء وقت السحب.
يُشغَّل بشكل دوري عبر APScheduler ويتحقق من السحوبات المنتهية بالوقت.
"""

import asyncio
from datetime import datetime

from sqlalchemy import select

from database.session import SessionLocal
from config import logger
from database.models.giveaway import Giveaway

from repositories.giveaway_repository import GiveawayRepository
from repositories.participant_repository import ParticipantRepository

from services.engines.draw_engine import DrawEngine

from bot.keyboards.giveaway import giveaway_keyboard
from services.chat_service import ChatService
from utils.safe_edit import safe_client_edit_reply_markup
from utils.text import safe_excerpt
from utils.broadcast import notify_users
from services.competition_flow import announce_competition_result


# أقصى عدد سحوبات تُعالَج بالتوازي في نفس اللحظة. عند دفعات كبيرة (مئات/
# آلاف السحوبات تنتهي في نفس الدقيقة) يمنع هذا إغراق قاعدة البيانات أو
# تيليجرام بطلبات متزامنة كثيرة جدًا دفعة واحدة، مع تفادي معالجتها
# بالتتابع الكامل (سحب واحد تلو الآخر) الذي يكون بطيئًا جدًا عند الحجم
# الكبير لأن كل سحب يحتاج ثوانٍ لإشعار فائزيه.
MAX_CONCURRENT_DRAWS = 20


async def _process_single_giveaway(client, giveaway_id: int, semaphore: asyncio.Semaphore):
    """
    يعالج سحبًا واحدًا منتهي الوقت بجلسة قاعدة بيانات مستقلة خاصة به، حتى
    لا يبقي بقية الدفعة منتظرة جلسة واحدة مشتركة، ولا تتعطل بقية السحوبات
    إن فشل واحد منها.
    """

    async with semaphore:

        async with SessionLocal() as db:

            try:

                giveaways_repo = GiveawayRepository(db)
                participants_repo = ParticipantRepository(db)

                giveaway = await giveaways_repo.get(giveaway_id)

                if giveaway is None or not giveaway.is_active:
                    return

                available = await participants_repo.get_available(giveaway_id)

                if not available:
                    await giveaways_repo.finish(giveaway)
                    return

                engine = DrawEngine(db, client)

                success, result_data = await engine.draw(giveaway_id)

                if not success:
                    await giveaways_repo.finish(giveaway)
                    return

                giveaway_obj, winners, _has_more = result_data

            except Exception as e:
                logger.exception("[DrawWorker] خطأ أثناء سحب السحب {}", giveaway_id)
                return

        # بقية العمل (إشعارات تيليجرام) لا تحتاج الجلسة مفتوحة، فنُغلقها
        # مبكرًا ونكمل بعدها لتقليل زمن الاحتفاظ باتصال قاعدة البيانات.

        text = f"🏆 انتهى وقت السحب — {safe_excerpt(giveaway_obj.description, 40)}\n\n"

        for i, winner in enumerate(winners, 1):
            name = f"@{winner.username}" if winner.username else winner.first_name
            text += f"{i}. {name}\n"

        try:

            try:
                await ChatService.ensure_resolved(
                    client, giveaway_obj.chat_id, giveaway_obj.chat_link,
                )
            except Exception:
                pass

            await client.send_message(chat_id=giveaway_obj.chat_id, text=text)

            await safe_client_edit_reply_markup(
                client,
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

            if getattr(giveaway_obj, 'flow_kind', 'giveaway') == 'competition':
                await announce_competition_result(client, giveaway_obj, winners)

        except Exception as e:
            logger.warning("[DrawWorker] Error announcing giveaway {}: {}", giveaway_id, e)

        await notify_users(
            client,
            [winner.user_id for winner in winners],
            lambda _uid: {
                "text": (
                    "🎉 مبروك! لقد فزت في السحب.\n\n"
                    f"📢 القناة/المجموعة: {giveaway_obj.chat_title}\n\n"
                    "سيتواصل معك منظّم السحب قريبًا بخصوص جائزتك."
                )
            },
            context=f"auto-draw-time giveaway#{giveaway_obj.id}",
        )

        logger.info("[DrawWorker] Finished giveaway {}", giveaway_id)


async def process_expired_giveaways(client):

    # استعلام خفيف: نجلب فقط المعرّفات المستحقة، ثم نعالج كل سحب بجلسته
    # الخاصة (بدل تحميل كل الكائنات وإبقاء جلسة واحدة مفتوحة للجميع).
    async with SessionLocal() as db:

        result = await db.execute(
            select(Giveaway.id).where(
                Giveaway.is_active.is_(True),
                Giveaway.end_at.isnot(None),
                Giveaway.end_at <= datetime.utcnow(),
                Giveaway.mode == "auto",
            )
        )

        giveaway_ids = list(result.scalars().all())

    if not giveaway_ids:
        return

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DRAWS)

    await asyncio.gather(
        *(
            _process_single_giveaway(client, giveaway_id, semaphore)
            for giveaway_id in giveaway_ids
        )
    )


async def run_worker(client, interval: int = 60):
    """يعمل في الخلفية ويتحقق دوريًا (بديل بسيط عن APScheduler إن لزم)."""
    logger.info("[DrawWorker] Started.")
    while True:
        try:
            await process_expired_giveaways(client)
        except Exception as e:
            logger.exception("[DrawWorker] Error")
        await asyncio.sleep(interval)
