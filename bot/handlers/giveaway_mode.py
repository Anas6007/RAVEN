from datetime import datetime

from pyrogram import filters
from pyrogram.handlers import CallbackQueryHandler, MessageHandler

from services.session_manager import session_manager
from services.engines.giveaway_engine import GiveawayEngine
from services.flow_labels import flow_noun
from constants.states import GiveawayState

from utils.filters import check_state

from bot.keyboards.giveaway_settings import settings_text, settings_menu


async def auto_by_count(client, callback):
    session = session_manager.get(callback.from_user.id)
    if session is None:
        await callback.answer("انتهت الجلسة.", show_alert=True)
        return

    engine = GiveawayEngine(callback.from_user.id)
    engine.set_auto_trigger("count")
    session.step = GiveawayState.WAITING_AUTO_COUNT

    noun = flow_noun(session)
    if getattr(session, "flow_kind", "giveaway") == "competition":
        prompt = """
🔢 المسابقة عند الوصول إلى عدد محدد

✍️ أرسل العدد المطلوب من الأصوات.
ستنتهي المسابقة تلقائيًا عندما يصل أحد المتسابقين إلى هذا العدد.

مثال: 50 25 10
"""
    else:
        prompt = f"""
🔢 **{noun} عند الوصول إلى عدد محدد**

✍️ أرسل العدد المطلوب من المشاركين.

مثال: 50
"""

    await callback.answer()
    await callback.message.edit_text(prompt)


async def auto_by_time(client, callback):
    session = session_manager.get(callback.from_user.id)
    if session is None:
        await callback.answer("انتهت الجلسة.", show_alert=True)
        return

    engine = GiveawayEngine(callback.from_user.id)
    engine.set_auto_trigger("time")
    session.step = GiveawayState.WAITING_AUTO_TIME

    noun = flow_noun(session)
    if getattr(session, "flow_kind", "giveaway") == "competition":
        prompt = """
⏰ **{noun} عند وقت محدد**

✍️ أرسل التاريخ والوقت بصيغة:
YYYY-MM-DD HH:MM

مثال:
2026-08-01 20:00
""".format(noun=noun)
    else:
        prompt = f"""
⏰ **{noun} عند وقت محدد**

✍️ أرسل عدد الساعات من الآن حتى موعد الإعلان.

مثال: 24
"""

    await callback.answer()
    await callback.message.edit_text(prompt)


async def receive_auto_count(client, message):
    session = session_manager.get(message.from_user.id)
    if session is None:
        await message.reply_text("❌ انتهت جلسة الإنشاء، ابدأ من جديد.")
        return

    text = (message.text or "").strip()
    if not text.isdigit() or int(text) < 2:
        await message.reply_text("❌ أرسل رقمًا صحيحًا (2 على الأقل).")
        return

    engine = GiveawayEngine(message.from_user.id)
    engine.set_auto_threshold(int(text))
    session.mode = "auto"
    session.step = GiveawayState.SETTINGS_MENU

    if getattr(session, "flow_kind", "giveaway") == "competition":
        await message.reply_text(f"✅ ستنتهي المسابقة تلقائيًا عند وصول أحد المتسابقين إلى {text} صوتًا.")
    else:
        noun = flow_noun(session)
        await message.reply_text(f"✅ سيتم الإنهاء تلقائيًا عند وصول {text} مشاركًا في {noun}.")
    await message.reply_text(settings_text(session), reply_markup=settings_menu(session))


async def receive_auto_time(client, message):
    session = session_manager.get(message.from_user.id)
    if session is None:
        await message.reply_text("❌ انتهت جلسة الإنشاء، ابدأ من جديد.")
        return

    text = (message.text or "").strip()
    engine = GiveawayEngine(message.from_user.id)

    if getattr(session, "flow_kind", "giveaway") == "competition":
        try:
            end_at = datetime.strptime(text, "%Y-%m-%d %H:%M")
        except ValueError:
            await message.reply_text("❌ الصيغة غير صحيحة. استخدم: YYYY-MM-DD HH:MM")
            return

        engine.set_end_date(end_at)
        session.mode = "auto"
        session.step = GiveawayState.SETTINGS_MENU
        await message.reply_text(f"✅ سيتم إنهاء المسابقة تلقائيًا عند {end_at:%Y-%m-%d %H:%M}.")
        await message.reply_text(settings_text(session), reply_markup=settings_menu(session))
        return

    if not text.isdigit() or int(text) < 1:
        await message.reply_text("❌ أرسل عدد الساعات كرقم صحيح (1 على الأقل).")
        return

    hours = int(text)
    engine.set_auto_hours(hours)
    session.mode = "auto"
    session.step = GiveawayState.SETTINGS_MENU

    await message.reply_text(f"✅ سيتم الإعلان تلقائيًا بعد {hours} ساعة من النشر.")
    await message.reply_text(settings_text(session), reply_markup=settings_menu(session))


def register(app):
    app.add_handler(CallbackQueryHandler(auto_by_count, filters.regex("^auto_by_count$")))
    app.add_handler(CallbackQueryHandler(auto_by_time, filters.regex("^auto_by_time$")))
    app.add_handler(MessageHandler(receive_auto_count, filters.private & filters.text & ~filters.command("start") & check_state(GiveawayState.WAITING_AUTO_COUNT)))
    app.add_handler(MessageHandler(receive_auto_time, filters.private & filters.text & ~filters.command("start") & check_state(GiveawayState.WAITING_AUTO_TIME)))
