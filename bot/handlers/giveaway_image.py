from pyrogram import filters
from pyrogram.handlers import CallbackQueryHandler, MessageHandler

from services.session_manager import session_manager
from services.engines.giveaway_engine import GiveawayEngine
from services.flow_labels import flow_noun

from constants.states import GiveawayState

from utils.filters import check_state

from bot.keyboards.giveaway_settings import (
    settings_text,
    settings_menu,
    image_manage_keyboard,
)


async def manage_image(client, callback):

    session = session_manager.get(callback.from_user.id)

    if session is None:
        await callback.answer("انتهت الجلسة.", show_alert=True)
        return

    session.step = GiveawayState.WAITING_IMAGE

    noun = flow_noun(session)

    await callback.answer()

    await callback.message.edit_text(
        f"""
🖼 **صورة أو فيديو {noun}** (اختياري)

أرسل الآن صورة أو فيديو لإرفاقهما مع رسالة {noun} عند النشر، أو احذف الوسائط الحالية إن كانت موجودة.

📌 يمكنك تخطي هذه الخطوة والرجوع للإعدادات مباشرة.
""",
        reply_markup=image_manage_keyboard(bool(session.image)),
    )


async def remove_image(client, callback):

    session = session_manager.get(callback.from_user.id)

    if session is None:
        await callback.answer("انتهت الجلسة.", show_alert=True)
        return

    engine = GiveawayEngine(callback.from_user.id)
    engine.remove_image()

    session.step = GiveawayState.SETTINGS_MENU

    await callback.answer("🗑 تم حذف الصورة.")

    await callback.message.edit_text(
        settings_text(session),
        reply_markup=settings_menu(session),
    )


async def receive_image(client, message):

    session = session_manager.get(message.from_user.id)

    if session is None:
        await message.reply_text("❌ انتهت جلسة الإنشاء، ابدأ من جديد.")
        return

    if message.photo:
        engine = GiveawayEngine(message.from_user.id)
        engine.set_media(message.photo.file_id, "photo")
    elif message.video:
        engine = GiveawayEngine(message.from_user.id)
        engine.set_media(message.video.file_id, "video")
    else:
        await message.reply_text("❌ أرسل صورة أو فيديو فقط (وليس ملفًا أو نصًا).")
        return

    session.step = GiveawayState.SETTINGS_MENU

    await message.reply_text("✅ تم حفظ الوسائط.")

    await message.reply_text(
        settings_text(session),
        reply_markup=settings_menu(session),
    )


def register(app):

    app.add_handler(
        CallbackQueryHandler(
            manage_image,
            filters.regex("^settings_manage_image$"),
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            remove_image,
            filters.regex("^settings_remove_image$"),
        )
    )

    app.add_handler(
        MessageHandler(
            receive_image,
            filters.private
            & (filters.photo | filters.video)
            & check_state(GiveawayState.WAITING_IMAGE),
        )
    )
