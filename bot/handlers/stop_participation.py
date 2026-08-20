from pyrogram import filters
from pyrogram.handlers import CallbackQueryHandler

from database.session import SessionLocal
from config import logger
from repositories.giveaway_repository import GiveawayRepository

from services.engines.security_engine import SecurityEngine

from bot.keyboards.giveaway import giveaway_keyboard
from utils.safe_edit import safe_edit_reply_markup
from services.flow_labels import flow_noun


async def stop_participation(client, callback):

    giveaway_id = int(callback.matches[0].group(1))

    async with SessionLocal() as db:

        giveaways = GiveawayRepository(db)

        giveaway = await giveaways.get(giveaway_id)

        if giveaway is None:
            await callback.answer("❌ السحب غير موجود.", show_alert=True)
            return

        security = SecurityEngine(client)

        authorized = await security.is_authorized_manager(
            callback.from_user.id,
            giveaway,
        )

        if not authorized:
            await callback.answer(
                "❌ هذا الإجراء متاح فقط لمنشئ السحب أو مشرفي القناة/المجموعة.",
                show_alert=True,
            )
            return

        noun = flow_noun(giveaway)
        if not giveaway.is_active:
            await callback.answer(f"{noun} متوقف بالفعل.", show_alert=True)
            return

        giveaway = await giveaways.finish(giveaway)

        try:

            await safe_edit_reply_markup(
                callback.message,
                giveaway_keyboard(
                    giveaway.id,
                    giveaway.participants_count,
                    giveaway.is_active,
                    giveaway.drawn_once,
                ),
            )

        except Exception as e:
            logger.warning("STOP UPDATE ERROR: {}", repr(e))

        await callback.answer(f"⛔ تم إيقاف هذا {noun}.", show_alert=True)


def register(app):

    app.add_handler(
        CallbackQueryHandler(
            stop_participation,
            filters.regex(r"^stop:(\d+)$"),
        )
    )
