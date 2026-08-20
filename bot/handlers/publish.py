from datetime import datetime, timedelta

from pyrogram import filters
from pyrogram.handlers import CallbackQueryHandler

from config import settings, logger

from database.session import SessionLocal

from repositories.giveaway_repository import GiveawayRepository
from repositories.linked_chat_repository import LinkedChatRepository
from repositories.banned_chat_repository import BannedChatRepository

from services.session_manager import session_manager
from services.giveaway_text import build_giveaway_text

from bot.keyboards.giveaway import giveaway_keyboard
from services.flow_labels import flow_title, flow_noun

from utils.safe_edit import safe_edit_text
from utils.media_messages import send_media


def _build_giveaway_text(session):
    return build_giveaway_text(session)


def _validate_session_ready(session) -> str | None:
    if not session.chat_id or not session.chat_title:
        return "⚠️ لم يتم ربط قناة/مجموعة صالحة بهذا السحب."

    if getattr(session, 'flow_kind', 'giveaway') == 'competition':
        if not session.contestant_slots or session.contestant_slots < 1:
            return "⚠️ عدد مقاعد المتسابقين غير محدد بشكل صحيح."
    else:
        if not session.winners_count or session.winners_count < 1:
            return "⚠️ عدد الفائزين غير محدد بشكل صحيح."

    if session.mode not in ("manual", "auto"):
        return "⚠️ نوع السحب (يدوي/تلقائي) غير محدد."

    if session.mode == "auto":
        if session.auto_trigger == "count" and not session.auto_threshold:
            return "⚠️ السحب التلقائي بالعدد يحتاج عددًا مستهدفًا للمشاركين."

        if session.auto_trigger == "time":
            if getattr(session, 'flow_kind', 'giveaway') == 'competition':
                if not session.end_date:
                    return "⚠️ المسابقة التلقائية بالوقت تحتاج تاريخًا ووقتًا محددين."
            elif not session.auto_hours:
                return "⚠️ السحب التلقائي بالوقت يحتاج مدة زمنية محددة."

        if session.auto_trigger is None:
            return "⚠️ لم يتم اختيار طريقة تفعيل السحب التلقائي."

    return None


async def _publish_to_all_giveaways_channel(client, giveaway, text, media_file_id=None):
    if not settings.ALL_GIVEAWAYS_CHANNEL_ENABLED:
        return

    try:
        await send_media(
            client,
            chat_id=settings.ALL_GIVEAWAYS_CHANNEL_ID,
            media_type=getattr(giveaway, "media_type", None),
            media_file_id=media_file_id,
            text=text,
            reply_markup=giveaway_keyboard(
                giveaway.id,
                0,
                True,
                False,
                management=False,
                flow_kind=getattr(giveaway, "flow_kind", "giveaway"),
                contestant_slots=getattr(giveaway, 'contestant_slots', None),
            ),
        )

    except Exception as e:
        logger.debug(f"[ALL_GIVEAWAYS_CHANNEL] publish skipped: {e!r}")


async def check_all_giveaways_channel(client):
    if not settings.ALL_GIVEAWAYS_CHANNEL_ID:
        settings.ALL_GIVEAWAYS_CHANNEL_ENABLED = False
        return

    try:
        await client.get_chat(settings.ALL_GIVEAWAYS_CHANNEL_ID)
        settings.ALL_GIVEAWAYS_CHANNEL_ENABLED = True
        logger.info("[ALL_GIVEAWAYS_CHANNEL] enabled.")
    except Exception as e:
        settings.ALL_GIVEAWAYS_CHANNEL_ENABLED = False
        logger.debug(
            "[ALL_GIVEAWAYS_CHANNEL] disabled due to configuration: {}",
            repr(e),
        )


async def publish_giveaway(client, callback):
    session = session_manager.get(callback.from_user.id)

    if session is None:
        await callback.answer("انتهت الجلسة.", show_alert=True)
        return

    error = _validate_session_ready(session)
    if error:
        await callback.answer(error, show_alert=True)
        return

    chat_type = (
        session.chat_type.value
        if hasattr(session.chat_type, "value")
        else str(session.chat_type)
    )

    end_at = None
    if session.mode == "auto" and session.auto_trigger == "time":
        if getattr(session, 'flow_kind', 'giveaway') == 'competition' and session.end_date:
            end_at = session.end_date
        elif session.auto_hours:
            end_at = datetime.utcnow() + timedelta(hours=session.auto_hours)

    try:
        async with SessionLocal() as db:
            banned_repo = BannedChatRepository(db)
            if await banned_repo.is_banned(session.chat_id):
                await safe_edit_text(
                    callback.message,
                    "🚫 هذه القناة/المجموعة محظورة من استخدام البوت، لا يمكن نشر سحب فيها.",
                )
                return

            giveaways = GiveawayRepository(db)
            giveaway = await giveaways.create(
                owner_id=callback.from_user.id,
                chat_id=session.chat_id,
                chat_type=chat_type,
                chat_title=session.chat_title,
                chat_link=session.chat_link,
                mode=session.mode,
                description=session.description,
                winners_count=session.winners_count,
                contestant_slots=getattr(session, 'contestant_slots', None),
                required_channels=session.required_channels,
                image=session.image,
                media_type=getattr(session, "media_type", None),
                enable_captcha=session.enable_captcha,
                require_comment=getattr(session, "require_comment", False),
                discussion_chat_id=getattr(session, "discussion_chat_id", None),
                discussion_message_id=getattr(session, "discussion_message_id", None),
                discussion_group_id=getattr(session, "discussion_group_id", None),
                require_approval=getattr(session, "require_approval", True),
                notify_winner=getattr(session, "notify_winner", True),
                announce_winner=getattr(session, "announce_winner", True),
                flow_kind=getattr(session, "flow_kind", "giveaway"),
                is_active=True,
                auto_trigger=session.auto_trigger,
                auto_threshold=session.auto_threshold,
                end_at=end_at,
            )

            text = _build_giveaway_text(session)

            message = await send_media(
                client,
                chat_id=session.chat_id,
                media_type=getattr(session, "media_type", None),
                media_file_id=session.image,
                text=text,
                reply_markup=giveaway_keyboard(
                    giveaway.id,
                    0,
                    True,
                    False,
                    management=getattr(giveaway, 'flow_kind', 'giveaway') != 'competition',
                    flow_kind=getattr(giveaway, "flow_kind", "giveaway"),
                    contestant_slots=getattr(giveaway, 'contestant_slots', None),
                ),
            )

            await giveaways.update_message_id(giveaway, message.id)

            await _publish_to_all_giveaways_channel(
                client,
                giveaway,
                text,
                session.image,
            )

            linked_chats = LinkedChatRepository(db)
            await linked_chats.remember(
                owner_id=callback.from_user.id,
                chat_id=session.chat_id,
                chat_type=chat_type,
                chat_title=session.chat_title,
                chat_link=session.chat_link,
            )

    except Exception:
        logger.exception("PUBLISH ERROR")
        await safe_edit_text(
            callback.message,
            "❌ فشل نشر السحب بسبب خطأ داخلي. تمت كتابة التفاصيل في السجل.",
        )
        return

    session_manager.delete(callback.from_user.id)

    noun = flow_noun(session)

    await callback.answer("✅ تم النشر بنجاح")

    await safe_edit_text(
        callback.message,
        f"""
✅ تم نشر {noun} بنجاح.

🆔 الرقم:
`{giveaway.id}`

📢 تم النشر في:

{session.chat_title}
""",
    )


async def cancel_giveaway(client, callback):
    session_manager.delete(callback.from_user.id)
    await safe_edit_text(callback.message, "❌ تم إلغاء إنشاء السحب.")


def register(app):
    app.add_handler(
        CallbackQueryHandler(publish_giveaway, filters.regex("^publish_giveaway$"))
    )

    app.add_handler(
        CallbackQueryHandler(cancel_giveaway, filters.regex("^cancel_giveaway$"))
    )
