from pyrogram import filters
from pyrogram.handlers import CallbackQueryHandler

from services.session_manager import session_manager
from services.giveaway_text import build_giveaway_text

from bot.keyboards.preview import preview_keyboard

from utils.safe_edit import safe_edit_text
from utils.media_messages import send_media


async def preview_giveaway(client, callback):

    session = session_manager.get(callback.from_user.id)

    if session is None:

        await callback.answer(
            "انتهت الجلسة.",
            show_alert=True,
        )
        return

    captcha = (
        "✅ مفعلة"
        if session.enable_captcha
        else "❌ غير مفعلة"
    )

    title = "🏆 **معاينة المسابقة النهائية**" if getattr(session, "flow_kind", "giveaway") == "competition" else "🎁 **معاينة السحب النهائية**"
    text = build_giveaway_text(session, title=title)

    text += (
        f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🛡 **الكابتشا:** {captcha}\n\n"
        "📍 هذه مجرد معاينة — يمكنك النشر أو العودة للتعديل."
    )

    has_current_media = bool(getattr(callback.message, "media", None))

    if session.image:

        try:
            await callback.message.delete()
        except Exception:
            pass

        await send_media(
            client,
            chat_id=callback.from_user.id,
            media_type=getattr(session, "media_type", None),
            media_file_id=session.image,
            text=text,
            reply_markup=preview_keyboard(session),
        )
        return

    if has_current_media:
        try:
            await callback.message.delete()
        except Exception:
            pass

        await send_media(
            client,
            chat_id=callback.from_user.id,
            media_type=None,
            media_file_id=None,
            text=text,
            reply_markup=preview_keyboard(session),
        )
        return

    await safe_edit_text(
        callback.message,
        text,
        reply_markup=preview_keyboard(session),
    )


def register(app):

    app.add_handler(
        CallbackQueryHandler(
            preview_giveaway,
            filters.regex("^preview_giveaway$")
        )
    )
