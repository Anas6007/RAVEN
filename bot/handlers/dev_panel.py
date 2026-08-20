from pyrogram import filters
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.errors import FloodWait, RPCError
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import asyncio

from database.session import SessionLocal

from repositories.giveaway_repository import GiveawayRepository
from repositories.participant_repository import ParticipantRepository
from repositories.linked_chat_repository import LinkedChatRepository
from repositories.user_repository import UserRepository
from repositories.banned_chat_repository import BannedChatRepository

from services.dev_session import dev_session_manager

from constants.chat_type import ChatType

from utils.filters import is_dev_filter, check_dev_state

from bot.keyboards.dev_panel import (
    dev_menu_keyboard,
    dev_back_keyboard,
    dev_cancel_keyboard,
    dev_broadcast_confirm_keyboard,
    dev_unban_list_keyboard,
)


DEV_HOME_TEXT = """
🛠 **لوحة تحكم المطور**

مرحبًا بك في لوحة الإدارة الخاصة. اختر أحد الأقسام أدناه:
"""


# ------------------------------------
# الدخول للوحة
# ------------------------------------

async def dev_command(client, message):

    dev_session_manager.delete(message.from_user.id)

    await message.reply_text(
        DEV_HOME_TEXT,
        reply_markup=dev_menu_keyboard(),
    )


async def dev_home(client, callback):

    dev_session_manager.delete(callback.from_user.id)

    await callback.message.edit_text(
        DEV_HOME_TEXT,
        reply_markup=dev_menu_keyboard(),
    )


# ------------------------------------
# الإحصائيات العامة
# ------------------------------------

async def dev_stats(client, callback):

    async with SessionLocal() as db:

        giveaways_repo = GiveawayRepository(db)
        linked_repo = LinkedChatRepository(db)
        users_repo = UserRepository(db)
        banned_repo = BannedChatRepository(db)

        stats = await giveaways_repo.get_stats()
        users_count = await users_repo.count()
        banned_count = await banned_repo.count()

        total_giveaways = stats["total"]
        active_giveaways = stats["active"]
        total_participants = stats["participants"]

        # عدد القنوات/المجموعات المختلفة المرتبطة بالبوت (بدون تكرار)
        all_owners_chats = {}

        # نجلب كل السجلات عبر استعلام مباشر بدل owner-by-owner
        from sqlalchemy import select
        from database.models.linked_chat import LinkedChat

        result = await db.execute(select(LinkedChat))
        all_linked = result.scalars().all()

        unique_chats = {c.chat_id: c for c in all_linked}

        channels_count = sum(
            1 for c in unique_chats.values() if c.chat_type == ChatType.CHANNEL
        )
        groups_count = sum(
            1 for c in unique_chats.values() if c.chat_type == ChatType.GROUP
        )

    text = f"""
📊 **إحصائيات عامة**

━━━━━━━━━━━━━━

🎁 إجمالي السحوبات: **{total_giveaways}**
🟢 السحوبات النشطة: **{active_giveaways}**
👥 إجمالي المشاركات: **{total_participants}**

━━━━━━━━━━━━━━

📢 القنوات المرتبطة: **{channels_count}**
👨‍👩‍👧 المجموعات المرتبطة: **{groups_count}**
🙋 المستخدمون: **{users_count}**

━━━━━━━━━━━━━━

🚫 القنوات/المجموعات المحظورة: **{banned_count}**
"""

    await callback.message.edit_text(text, reply_markup=dev_back_keyboard())


async def dev_channels_or_groups(client, callback, wanted_type: str, title: str, icon: str):

    async with SessionLocal() as db:

        from sqlalchemy import select
        from database.models.linked_chat import LinkedChat

        result = await db.execute(
            select(LinkedChat).where(LinkedChat.chat_type == wanted_type)
        )
        chats = result.scalars().all()

    unique = {}
    for c in chats:
        unique[c.chat_id] = c

    lines = [f"{icon} {title}\n", f"العدد الإجمالي: **{len(unique)}**\n", "━━━━━━━━━━━━━━\n"]

    for c in list(unique.values())[:30]:
        lines.append(f"• {c.chat_title} (`{c.chat_id}`)")

    if len(unique) > 30:
        lines.append(f"\n... و{len(unique) - 30} أخرى")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=dev_back_keyboard(),
    )


async def dev_channels(client, callback):
    await dev_channels_or_groups(client, callback, ChatType.CHANNEL, "القنوات المرتبطة", "📢")


async def dev_groups(client, callback):
    await dev_channels_or_groups(client, callback, ChatType.GROUP, "المجموعات المرتبطة", "👨‍👩‍👧")


async def dev_users(client, callback):

    async with SessionLocal() as db:

        users_repo = UserRepository(db)
        users = await users_repo.get_all()

    lines = [
        "🙋 **المستخدمون**\n",
        f"العدد الإجمالي: **{len(users)}**\n",
        "━━━━━━━━━━━━━━\n",
    ]

    for u in users[-30:]:
        name = f"@{u.username}" if u.username else (u.first_name or str(u.telegram_id))
        lines.append(f"• {name} (`{u.telegram_id}`)")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=dev_back_keyboard(),
    )


# ------------------------------------
# الإذاعة العامة
# ------------------------------------

async def dev_broadcast(client, callback):

    session = dev_session_manager.get_or_create(callback.from_user.id)
    session.step = "waiting_broadcast"

    await callback.message.edit_text(
        """
📨 **إذاعة عامة**

أرسل الآن الرسالة التي تريد إذاعتها لجميع مستخدمي البوت (نص، صورة،
فيديو... إلخ). ستُرسل كما هي تمامًا لكل مستخدم.
""",
        reply_markup=dev_cancel_keyboard(),
    )


async def dev_receive_broadcast(client, message):

    session = dev_session_manager.get(message.from_user.id)

    if session is None:
        return

    session.step = "confirm_broadcast"
    session.broadcast_chat_id = message.chat.id
    session.broadcast_message_id = message.id

    await message.reply_text(
        "⚠️ سيتم إرسال هذه الرسالة لجميع المستخدمين. هل تريد المتابعة؟",
        reply_markup=dev_broadcast_confirm_keyboard(),
    )


async def dev_broadcast_confirm(client, callback):

    session = dev_session_manager.get(callback.from_user.id)

    if session is None or session.step != "confirm_broadcast":
        await callback.answer("❌ لا توجد رسالة إذاعة جاهزة.", show_alert=True)
        return

    await callback.answer()

    await callback.message.edit_text("📨 جارٍ الإرسال... قد يستغرق هذا بعض الوقت.")

    async with SessionLocal() as db:

        users_repo = UserRepository(db)
        users = await users_repo.get_all()

    sent = 0
    failed = 0

    for user in users:

        try:

            await client.copy_message(
                chat_id=user.telegram_id,
                from_chat_id=session.broadcast_chat_id,
                message_id=session.broadcast_message_id,
            )

            sent += 1

        except FloodWait as e:

            await asyncio.sleep(e.value)

            try:
                await client.copy_message(
                    chat_id=user.telegram_id,
                    from_chat_id=session.broadcast_chat_id,
                    message_id=session.broadcast_message_id,
                )
                sent += 1
            except Exception:
                failed += 1

        except Exception:
            failed += 1

        # مهلة بسيطة لتفادي القيود (Flood) عند الإرسال لعدد كبير من المستخدمين
        await asyncio.sleep(0.05)

    dev_session_manager.delete(callback.from_user.id)

    await client.send_message(
        callback.from_user.id,
        f"""
✅ **انتهت الإذاعة**

━━━━━━━━━━━━━━

📨 تم الإرسال بنجاح: **{sent}**
❌ فشل الإرسال: **{failed}**
""",
        reply_markup=dev_back_keyboard(),
    )


# ------------------------------------
# حظر قناة/مجموعة
# ------------------------------------

async def dev_ban(client, callback):

    session = dev_session_manager.get_or_create(callback.from_user.id)
    session.step = "waiting_ban"

    await callback.message.edit_text(
        """
🚫 **حظر قناة/مجموعة**

أرسل أحد التالي لتحديد القناة/المجموعة المراد حظرها:

• تحويل رسالة منها (ويمكنك إضافة سبب الحظر ككابشن).
• أو إرسال معرفها الرقمي (Chat ID) متبوعًا بسبب الحظر اختياريًا.
• أو إرسال @username الخاص بها.

مثال: `-1001234567890 محتوى مخالف`
""",
        reply_markup=dev_cancel_keyboard(),
    )


async def _resolve_ban_target(client, message):
    """يحاول استخراج (chat_id, title, reason) من رسالة المطور."""

    if message.forward_from_chat:

        chat = message.forward_from_chat
        reason = (message.caption or message.text or "").strip() or None

        return chat.id, chat.title, reason

    text = (message.text or "").strip()

    if not text:
        return None, None, None

    parts = text.split(maxsplit=1)
    target = parts[0]
    reason = parts[1].strip() if len(parts) > 1 else None

    # معرف رقمي مباشر
    if target.lstrip("-").isdigit():

        chat_id = int(target)
        title = None

        try:
            chat = await client.get_chat(chat_id)
            title = chat.title
        except Exception:
            pass

        return chat_id, title, reason

    # @username أو رابط
    username = target.replace("https://t.me/", "").replace("http://t.me/", "").lstrip("@").strip("/")

    try:
        chat = await client.get_chat(username)
        return chat.id, chat.title, reason
    except Exception:
        return None, None, None


async def dev_receive_ban(client, message):

    session = dev_session_manager.get(message.from_user.id)

    if session is None:
        return

    chat_id, title, reason = await _resolve_ban_target(client, message)

    if chat_id is None:
        await message.reply_text(
            "❌ تعذر التعرف على القناة/المجموعة، حاول مرة أخرى بإرسال "
            "معرف صحيح أو تحويل رسالة منها."
        )
        return

    async with SessionLocal() as db:

        banned_repo = BannedChatRepository(db)

        await banned_repo.ban(
            chat_id=chat_id,
            chat_title=title,
            reason=reason,
            banned_by=message.from_user.id,
        )

    dev_session_manager.delete(message.from_user.id)

    await message.reply_text(
        f"""
🚫 **تم الحظر بنجاح**

📌 القناة/المجموعة: {title or chat_id}
🆔 المعرف: `{chat_id}`
📝 السبب: {reason or "غير محدد"}

لن يتمكن أصحابها من ربطها أو نشر/متابعة سحوبات فيها بعد الآن.
""",
        reply_markup=dev_back_keyboard(),
    )


# ------------------------------------
# فك الحظر
# ------------------------------------

async def dev_unban(client, callback):

    session = dev_session_manager.get_or_create(callback.from_user.id)
    session.step = "waiting_unban"

    await callback.message.edit_text(
        """
✅ **فك حظر قناة/مجموعة**

أرسل المعرف الرقمي (Chat ID) الخاص بالقناة/المجموعة المراد فك حظرها،
أو استخدم زر "📋 قائمة المحظورين" من اللوحة الرئيسية لاختيارها مباشرة.
""",
        reply_markup=dev_cancel_keyboard(),
    )


async def dev_receive_unban(client, message):

    session = dev_session_manager.get(message.from_user.id)

    if session is None:
        return

    text = (message.text or "").strip()

    if not text.lstrip("-").isdigit():
        await message.reply_text("❌ أرسل معرفًا رقميًا صحيحًا.")
        return

    chat_id = int(text)

    async with SessionLocal() as db:

        banned_repo = BannedChatRepository(db)
        ok = await banned_repo.unban(chat_id)

    dev_session_manager.delete(message.from_user.id)

    if ok:
        await message.reply_text(
            f"✅ تم فك الحظر عن `{chat_id}`.",
            reply_markup=dev_back_keyboard(),
        )
    else:
        await message.reply_text(
            "❌ لم يتم العثور على هذا المعرف ضمن القائمة المحظورة.",
            reply_markup=dev_back_keyboard(),
        )


async def dev_banned_list(client, callback):

    async with SessionLocal() as db:

        banned_repo = BannedChatRepository(db)
        banned = await banned_repo.get_all()

    if not banned:
        await callback.answer("📋 لا توجد قنوات/مجموعات محظورة حاليًا.", show_alert=True)
        return

    await callback.message.edit_text(
        f"📋 **القنوات/المجموعات المحظورة ({len(banned)})**\n\nاضغط لفك الحظر:",
        reply_markup=dev_unban_list_keyboard(banned),
    )


async def dev_unban_id_click(client, callback):

    chat_id = int(callback.matches[0].group(1))

    async with SessionLocal() as db:

        banned_repo = BannedChatRepository(db)
        await banned_repo.unban(chat_id)

    await callback.answer("✅ تم فك الحظر.", show_alert=True)
    await dev_banned_list(client, callback)


def register(app):

    app.add_handler(
        MessageHandler(
            dev_command,
            filters.private & filters.command(["dev", "admin"]) & is_dev_filter,
        )
    )

    app.add_handler(
        CallbackQueryHandler(dev_home, filters.regex("^dev_home$") & is_dev_filter)
    )

    app.add_handler(
        CallbackQueryHandler(dev_stats, filters.regex("^dev_stats$") & is_dev_filter)
    )

    app.add_handler(
        CallbackQueryHandler(dev_channels, filters.regex("^dev_channels$") & is_dev_filter)
    )

    app.add_handler(
        CallbackQueryHandler(dev_groups, filters.regex("^dev_groups$") & is_dev_filter)
    )

    app.add_handler(
        CallbackQueryHandler(dev_users, filters.regex("^dev_users$") & is_dev_filter)
    )

    app.add_handler(
        CallbackQueryHandler(dev_broadcast, filters.regex("^dev_broadcast$") & is_dev_filter)
    )

    app.add_handler(
        CallbackQueryHandler(
            dev_broadcast_confirm,
            filters.regex("^dev_broadcast_confirm$") & is_dev_filter,
        )
    )

    app.add_handler(
        CallbackQueryHandler(dev_ban, filters.regex("^dev_ban$") & is_dev_filter)
    )

    app.add_handler(
        CallbackQueryHandler(dev_unban, filters.regex("^dev_unban$") & is_dev_filter)
    )

    app.add_handler(
        CallbackQueryHandler(
            dev_banned_list,
            filters.regex("^dev_banned_list$") & is_dev_filter,
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            dev_unban_id_click,
            filters.regex(r"^dev_unban_id:(-?\d+)$") & is_dev_filter,
        )
    )

    app.add_handler(
        MessageHandler(
            dev_receive_broadcast,
            filters.private
            & is_dev_filter
            & ~filters.command(["start", "dev"])
            & check_dev_state("waiting_broadcast"),
        )
    )

    app.add_handler(
        MessageHandler(
            dev_receive_ban,
            filters.private
            & is_dev_filter
            & ~filters.command(["start", "dev"])
            & check_dev_state("waiting_ban"),
        )
    )

    app.add_handler(
        MessageHandler(
            dev_receive_unban,
            filters.private
            & is_dev_filter
            & filters.text
            & ~filters.command(["start", "dev"])
            & check_dev_state("waiting_unban"),
        )
    )
