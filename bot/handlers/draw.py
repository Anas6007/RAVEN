from pyrogram import filters
from pyrogram.handlers import CallbackQueryHandler

from database.session import SessionLocal
from config import logger
from repositories.giveaway_repository import GiveawayRepository

from services.engines.draw_engine import DrawEngine
from services.engines.security_engine import SecurityEngine

from bot.keyboards.giveaway import giveaway_keyboard
from utils.safe_edit import safe_edit_reply_markup
from utils.text import safe_excerpt
from utils.broadcast import notify_users
from services.flow_labels import flow_noun
from services.competition_flow import announce_competition_result


async def draw_winners(client, callback):

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

        engine = DrawEngine(db, client)

        success, result = await engine.draw(giveaway_id)

        if not success:
            await callback.answer(result, show_alert=True)
            return

        giveaway_obj, winners, has_more = result

        noun = flow_noun(giveaway)
        lines = [f"🏆 **نتائج {noun}**\n"]

        for i, winner in enumerate(winners, 1):
            name = f"@{winner.username}" if winner.username else winner.first_name
            lines.append(f"{i}. {name}")

        lines.append(f"\n📢 السحب: {safe_excerpt(giveaway_obj.description, 50)}")

        text = "\n".join(lines)

        await callback.message.reply_text(text)

        if getattr(giveaway_obj, 'flow_kind', 'giveaway') == 'competition':
            try:
                await announce_competition_result(client, giveaway_obj, winners)
            except Exception:
                pass

        try:

            await safe_edit_reply_markup(
                callback.message,
                giveaway_keyboard(
                    giveaway_obj.id,
                    giveaway_obj.participants_count,
                    giveaway_obj.is_active,
                    giveaway_obj.drawn_once,
                ),
            )

        except Exception as e:
            logger.warning("DRAW UPDATE ERROR: {}", repr(e))

        noun = flow_noun(giveaway_obj)
        await notify_users(
            client,
            [winner.user_id for winner in winners],
            lambda _uid: {
                "text": (
                    f"🎉 مبروك! لقد فزت في {noun}.\n\n"
                    f"📢 القناة/المجموعة: {giveaway_obj.chat_title}\n\n"
                    f"سيتواصل معك منظّم {noun} قريبًا بخصوص جائزتك.\n\n"
                    "📌 لا تحظر البوت حتى تصلك أي تفاصيل إضافية."
                )
            },
            context=f"manual-draw giveaway#{giveaway_obj.id}",
        )

        await callback.answer(
            "✅ تم اختيار الفائزين."
            if has_more
            else "✅ تم اختيار الفائزين. لا يوجد مشاركون آخرون متبقّون.",
            show_alert=True,
        )


def register(app):

    app.add_handler(
        CallbackQueryHandler(
            draw_winners,
            filters.regex(r"^draw:(\d+)$"),
        )
    )
