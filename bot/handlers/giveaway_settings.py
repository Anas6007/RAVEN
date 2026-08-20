from pyrogram import filters
from pyrogram.handlers import CallbackQueryHandler

from services.session_manager import session_manager
from services.engines.giveaway_engine import GiveawayEngine
from services.giveaway_text import build_giveaway_text

from constants.states import GiveawayState

from bot.keyboards.giveaway_settings import (
    settings_text,
    settings_menu,
    auto_mode_settings_menu,
    channels_manage_keyboard,
)
from bot.keyboards.preview import preview_keyboard
from utils.safe_edit import safe_edit_text
from utils.media_messages import send_media


async def _no_session(callback):
    await callback.answer("انتهت الجلسة.", show_alert=True)


async def show_settings(callback):
    session = session_manager.get(callback.from_user.id)
    if session is None:
        await _no_session(callback)
        return

    session.step = GiveawayState.SETTINGS_MENU
    await callback.message.edit_text(
        settings_text(session),
        reply_markup=settings_menu(session),
    )


async def toggle_captcha(client, callback):
    session = session_manager.get(callback.from_user.id)
    if session is None:
        await _no_session(callback)
        return

    engine = GiveawayEngine(callback.from_user.id)
    if session.enable_captcha:
        engine.disable_captcha()
    else:
        engine.enable_captcha()

    await callback.answer()
    await show_settings(callback)


async def toggle_comment_requirement(client, callback):
    session = session_manager.get(callback.from_user.id)
    if session is None:
        await _no_session(callback)
        return

    engine = GiveawayEngine(callback.from_user.id)
    if getattr(session, "require_comment", False):
        engine.disable_comment_requirement()
        session.step = GiveawayState.SETTINGS_MENU
        await callback.answer("✅ تم تعطيل شرط التعليق.")
        await show_settings(callback)
        return

    engine.enable_comment_requirement()
    session.step = GiveawayState.WAITING_DISCUSSION_LINK
    await callback.answer("✅ تم تفعيل شرط التعليق.")
    await callback.message.edit_text(
        """
💬 **شرط التعليق**

أرسل رابط المنشور المطلوب التعليق عليه.

يمكنك إرسال أحد الأنماط التالية:
• https://t.me/username/123
• https://t.me/c/123456789/123
• رسالة محوّلة من المنشور نفسه

⚠️ يجب أن يكون البوت منشئًا/مشرفًا في القناة المرتبطة، وأن يكون لديه صلاحية الوصول لرسائل المناقشة إن كانت القناة مرتبطة بمجموعة نقاش.
""",
        reply_markup=channels_manage_keyboard(),
    )


async def toggle_participant_approval(client, callback):
    session = session_manager.get(callback.from_user.id)
    if session is None:
        await _no_session(callback)
        return

    engine = GiveawayEngine(callback.from_user.id)
    engine.toggle_participant_approval()
    await callback.answer("✅ تم تحديث قبول المشاركين." if getattr(session, "require_approval", True) else "❌ تم إلغاء قبول المشاركين.")
    await show_settings(callback)


async def toggle_notify_winner(client, callback):
    session = session_manager.get(callback.from_user.id)
    if session is None:
        await _no_session(callback)
        return

    engine = GiveawayEngine(callback.from_user.id)
    engine.toggle_notify_winner()
    await callback.answer("✅ تم تحديث إشعار الفوز." if getattr(session, "notify_winner", True) else "❌ تم تعطيل إشعار الفوز.")
    await show_settings(callback)


async def toggle_announce_winner(client, callback):
    session = session_manager.get(callback.from_user.id)
    if session is None:
        await _no_session(callback)
        return

    engine = GiveawayEngine(callback.from_user.id)
    engine.toggle_announce_winner()
    await callback.answer("✅ تم تحديث إعلان الفائز." if getattr(session, "announce_winner", True) else "❌ تم تعطيل إعلان الفائز.")
    await show_settings(callback)


async def manage_channels(client, callback):
    session = session_manager.get(callback.from_user.id)
    if session is None:
        await _no_session(callback)
        return

    session.step = GiveawayState.WAITING_REQUIRED_CHANNELS
    is_competition = getattr(session, "flow_kind", "giveaway") == "competition"
    noun = "المسابقة" if is_competition else "السحب"

    note = ""
    if is_competition:
        note = "\n\n⚠️ يجب أن يكون البوت والمنشئ مشرفين في قنوات الاشتراك الإجباري، وفي قناة/مجموعة التعليق إذا كان شرط التعليق مفعّلًا."

    await callback.answer()
    await callback.message.edit_text(
        f"""
📢 **قنوات الاشتراك الإجباري**

أرسل قناة أو مجموعة واحدة في كل مرة، وسيتم حفظها داخل {noun}.

يمكنك الإرسال بأحد الأشكال التالية:
• @username
• رابط عام
• رابط دعوة خاص
• رسالة محوّلة من القناة/المجموعة

━━━━━━━━━━━━━━━━━━

✨ هذه القنوات ستظهر في رسالة {noun} تلقائيًا.{note}
""",
        reply_markup=channels_manage_keyboard(),
    )


async def set_manual_mode(client, callback):
    session = session_manager.get(callback.from_user.id)
    if session is None:
        await _no_session(callback)
        return

    engine = GiveawayEngine(callback.from_user.id)
    engine.set_mode("manual")
    await callback.answer("✅ تم اختيار السحب اليدوي.")
    await show_settings(callback)


async def set_auto_mode(client, callback):
    session = session_manager.get(callback.from_user.id)
    if session is None:
        await _no_session(callback)
        return

    engine = GiveawayEngine(callback.from_user.id)
    engine.set_mode("auto")
    await callback.answer()
    await callback.message.edit_text(
        """
⏰ **الوضع التلقائي**

اختر طريقة الإنهاء:
• عند بلوغ عدد محدد
• عند وقت محدد
""",
        reply_markup=auto_mode_settings_menu(session),
    )


async def settings_back(client, callback):
    await callback.answer()
    await show_settings(callback)


async def settings_continue(client, callback):
    session = session_manager.get(callback.from_user.id)
    if session is None:
        await _no_session(callback)
        return

    is_competition = getattr(session, "flow_kind", "giveaway") == "competition"

    if is_competition:
        if session.mode != "auto":
            session.mode = "auto"

        if session.auto_trigger not in ("count", "time"):
            await callback.answer("⚠️ اختر طريقة إنهاء المسابقة أولًا.", show_alert=True)
            return

        if session.auto_trigger == "count" and not session.auto_threshold:
            await callback.answer("⚠️ حدّد عدد الأصوات أولًا.", show_alert=True)
            return

        if session.auto_trigger == "time" and not session.end_date:
            await callback.answer("⚠️ حدّد التاريخ والوقت أولًا.", show_alert=True)
            return

    else:
        if session.mode not in ("manual", "auto"):
            await callback.answer(
                "⚠️ اختر نوع السحب (يدوي أو تلقائي) قبل المتابعة.",
                show_alert=True,
            )
            return

        if session.mode == "auto":
            if session.auto_trigger == "count" and not session.auto_threshold:
                await callback.answer("⚠️ حدّد عدد المشاركين أولًا.", show_alert=True)
                return
            if session.auto_trigger == "time" and not session.auto_hours:
                await callback.answer("⚠️ حدّد عدد الساعات أولًا.", show_alert=True)
                return
            if session.auto_trigger is None:
                await callback.answer("⚠️ اختر طريقة التفعيل أولًا.", show_alert=True)
                return

    session.step = GiveawayState.WAITING_PREVIEW

    title = "🏆 **معاينة المسابقة النهائية**" if is_competition else "🎁 **معاينة السحب النهائية**"
    text = build_giveaway_text(session, title=title)
    if is_competition:
        text += (
            "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🛡 **الكابتشا:** {'✅ مفعلة' if session.enable_captcha else '❌ غير مفعلة'}\n"
            f"📢 **الاشتراك الإجباري:** {len(session.required_channels)}\n"
            f"💬 **شرط التعليق:** {'✅ مفعّل' if getattr(session, 'require_comment', False) else '❌ غير مفعّل'}\n"
            f"👤 **قبول المشاركين:** {'✅ مفعّل' if getattr(session, 'require_approval', True) else '❌ غير مفعّل'}\n"
            f"🔔 **إشعار الفوز:** {'✅ مفعّل' if getattr(session, 'notify_winner', True) else '❌ غير مفعّل'}\n"
            f"📢 **إعلان الفائز:** {'✅ مفعّل' if getattr(session, 'announce_winner', True) else '❌ غير مفعّل'}\n"
            f"🎯 **طريقة الانتهاء:** {'عند بلوغ الأصوات' if session.auto_trigger == 'count' else 'عند الوقت'}\n"
            "📍 راجع التفاصيل بدقة، ثم انشر المسابقة أو عدّل ما تريد."
        )
    else:
        text += (
            "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🛡 **الكابتشا:** {'✅ مفعلة' if session.enable_captcha else '❌ غير مفعلة'}\n\n"
            "📍 راجع التفاصيل بدقة، ثم انشر السحب أو عدّل ما تريد."
        )

    await callback.answer()

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

    await safe_edit_text(
        callback.message,
        text,
        reply_markup=preview_keyboard(session),
    )


def register(app):
    app.add_handler(CallbackQueryHandler(toggle_captcha, filters.regex("^settings_toggle_captcha$")))
    app.add_handler(CallbackQueryHandler(manage_channels, filters.regex("^settings_manage_channels$")))
    app.add_handler(CallbackQueryHandler(toggle_comment_requirement, filters.regex("^settings_manage_comment$")))
    app.add_handler(CallbackQueryHandler(toggle_participant_approval, filters.regex("^settings_toggle_approval$")))
    app.add_handler(CallbackQueryHandler(toggle_notify_winner, filters.regex("^settings_toggle_notify_winner$")))
    app.add_handler(CallbackQueryHandler(toggle_announce_winner, filters.regex("^settings_toggle_announce_winner$")))
    app.add_handler(CallbackQueryHandler(set_manual_mode, filters.regex("^settings_manual_mode$")))
    app.add_handler(CallbackQueryHandler(set_auto_mode, filters.regex("^settings_auto_mode$")))
    app.add_handler(CallbackQueryHandler(settings_back, filters.regex("^settings_back$")))
    app.add_handler(CallbackQueryHandler(settings_continue, filters.regex("^settings_continue$")))
