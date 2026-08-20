from pyrogram import filters
from pyrogram.handlers import CallbackQueryHandler, MessageHandler

from database.session import SessionLocal
from repositories.giveaway_repository import GiveawayRepository

from services.edit_session_manager import edit_session_manager
from services.giveaway_text import build_giveaway_text

from bot.keyboards.manage_giveaway import (
    manage_giveaway_keyboard,
    giveaway_edit_menu_keyboard,
)
from bot.keyboards.giveaway import giveaway_keyboard

from utils.media_messages import edit_media_message
from config import logger


FIELD_PROMPTS = {
    "description": "📝 أرسل الوصف الجديد للسحب.",
    "winners": "👥 أرسل عدد الفائزين الجديد (رقم بين 1 و100).",
}


async def _refresh_published_message(client, giveaway):
    if not giveaway.message_id:
        return

    text = build_giveaway_text(giveaway)

    keyboard = giveaway_keyboard(
        giveaway.id,
        giveaway.participants_count,
        giveaway.is_active,
        giveaway.drawn_once,
        management=getattr(giveaway, 'flow_kind', 'giveaway') != 'competition',
        flow_kind=getattr(giveaway, 'flow_kind', 'giveaway'),
        contestant_slots=getattr(giveaway, 'contestant_slots', None),
    )

    try:
        await edit_media_message(
            client,
            chat_id=giveaway.chat_id,
            message_id=giveaway.message_id,
            media_type=getattr(giveaway, "media_type", None) if giveaway.image else None,
            text=text,
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.debug(f"[EDIT_GIVEAWAY] تعذّر تحديث الرسالة المنشورة: {e!r}")


async def giveaway_edit_menu(client, callback):
    giveaway_id = int(callback.matches[0].group(1))

    async with SessionLocal() as db:
        giveaways = GiveawayRepository(db)
        giveaway = await giveaways.get(giveaway_id)

        if giveaway is None:
            await callback.answer("❌ السحب غير موجود.", show_alert=True)
            return

        if giveaway.owner_id != callback.from_user.id:
            await callback.answer(
                "❌ تعديل بيانات السحب متاح فقط لمنشئ السحب.",
                show_alert=True,
            )
            return

        await callback.answer()
        await callback.message.edit_text(
            f"✏️ **تعديل السحب #{giveaway.id}**\n\n"
            "اختر الحقل الذي تريد تعديله:",
            reply_markup=giveaway_edit_menu_keyboard(giveaway_id),
        )


async def giveaway_edit_field(client, callback):
    giveaway_id = int(callback.matches[0].group(1))
    field = callback.matches[0].group(2)

    if field not in FIELD_PROMPTS:
        await callback.answer("❌ هذا الحقل لم يعد متاحًا.", show_alert=True)
        return

    async with SessionLocal() as db:
        giveaways = GiveawayRepository(db)
        giveaway = await giveaways.get(giveaway_id)

        if giveaway is None:
            await callback.answer("❌ السحب غير موجود.", show_alert=True)
            return

        if giveaway.owner_id != callback.from_user.id:
            await callback.answer(
                "❌ تعديل بيانات السحب متاح فقط لمنشئ السحب.",
                show_alert=True,
            )
            return

    session = edit_session_manager.create(callback.from_user.id, giveaway_id)
    session.field = field

    await callback.answer()
    await callback.message.edit_text(
        FIELD_PROMPTS.get(field, "أرسل القيمة الجديدة."),
        reply_markup=giveaway_edit_menu_keyboard(giveaway_id),
    )


async def receive_edit_value(client, message):
    session = edit_session_manager.get(message.from_user.id)

    if session is None or session.field is None:
        return

    if not message.text:
        await message.reply_text("❌ أرسل نصًا فقط.")
        return

    text = message.text.strip()

    async with SessionLocal() as db:
        giveaways = GiveawayRepository(db)
        giveaway = await giveaways.get(session.giveaway_id)

        if giveaway is None:
            await message.reply_text("❌ السحب لم يعد موجودًا.")
            edit_session_manager.delete(message.from_user.id)
            return

        if giveaway.owner_id != message.from_user.id:
            await message.reply_text("❌ ليست لديك صلاحية تعديل هذا السحب.")
            edit_session_manager.delete(message.from_user.id)
            return

        if session.field == "description":
            if len(text) < 5:
                await message.reply_text("❌ الوصف قصير جدًا.")
                return
            if len(text) > 1024:
                await message.reply_text("❌ الوصف طويل جدًا.")
                return
            await giveaways.update(giveaway, description=text)

        elif session.field == "winners":
            if not text.isdigit() or int(text) < 1 or int(text) > 100:
                await message.reply_text("❌ أرسل رقمًا صحيحًا بين 1 و100.")
                return
            await giveaways.update(giveaway, winners_count=int(text))

        else:
            edit_session_manager.delete(message.from_user.id)
            await message.reply_text("❌ هذا الحقل غير مدعوم حاليًا.")
            return

        await _refresh_published_message(client, giveaway)

    edit_session_manager.delete(message.from_user.id)

    await message.reply_text(
        "✅ تم حفظ التعديل وتحديث رسالة السحب المنشورة.",
        reply_markup=manage_giveaway_keyboard(session.giveaway_id, giveaway.is_active),
    )


def _has_active_edit_session(_, __, message):
    user = getattr(message, "from_user", None)
    if user is None:
        return False

    session = edit_session_manager.get(user.id)
    return session is not None and session.field is not None


edit_field_filter = filters.create(_has_active_edit_session)


def register(app):
    app.add_handler(
        CallbackQueryHandler(
            giveaway_edit_menu,
            filters.regex(r"^giveaway_edit_menu:(\d+)$"),
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            giveaway_edit_field,
            filters.regex(r"^giveaway_edit_field:(\d+):(\w+)$"),
        )
    )

    app.add_handler(
        MessageHandler(
            receive_edit_value,
            filters.private
            & filters.text
            & ~filters.command("start")
            & edit_field_filter,
        )
    )
