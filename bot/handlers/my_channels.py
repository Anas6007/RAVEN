from pyrogram import filters
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import PeerIdInvalid

from database.session import SessionLocal
from repositories.linked_chat_repository import LinkedChatRepository
from repositories.banned_chat_repository import BannedChatRepository

from services.session_manager import session_manager
from services.chat_service import ChatService

from constants.states import GiveawayState
from constants.chat_type import ChatType




async def my_channels(client, callback):

    async with SessionLocal() as db:

        repo = LinkedChatRepository(db)

        chats = await repo.get_by_owner(callback.from_user.id)

        if not chats:

            await callback.answer(
                "📭 لا توجد قنوات أو مجموعات محفوظة بعد.\n"
                "اربط قناة أو مجموعة أولًا وسيتم حفظها هنا تلقائيًا.",
                show_alert=True,
            )
            return

        rows = []

        for chat in chats[:15]:

            icon = "📢" if chat.chat_type == ChatType.CHANNEL else "👥"

            rows.append(
                [
                    InlineKeyboardButton(
                        f"{icon} {chat.chat_title}",
                        callback_data=f"select_chat:{chat.id}",
                    )
                ]
            )

        rows.append(
            [InlineKeyboardButton("⬅️ رجوع", callback_data="create_giveaway")]
        )

        await callback.message.edit_text(
            """
📂 **قنواتي**

اختر القناة أو المجموعة التي تريد إنشاء السحب فيها:

━━━━━━━━━━━━━━━━━━

⚠️ سيتم التحقق من صلاحياتك فور اختيارها.
""",
            reply_markup=InlineKeyboardMarkup(rows),
        )


async def select_chat(client, callback):

    linked_id = int(callback.matches[0].group(1))

    await callback.message.edit_text(
        "⏳ دعني أتحقق أنك ما زلت مشرفًا في هذه الدردشة...\n\nجاري التحقق..."
    )

    async with SessionLocal() as db:

        repo = LinkedChatRepository(db)

        chats = await repo.get_by_owner(callback.from_user.id)
        chat = next((c for c in chats if c.id == linked_id), None)

        if chat is None:
            await callback.message.edit_text("❌ لم يتم العثور على هذه الدردشة.")
            return

        banned_repo = BannedChatRepository(db)

        if await banned_repo.is_banned(chat.chat_id):
            await callback.message.edit_text(
                "🚫 هذه القناة/المجموعة محظورة من استخدام البوت، لا يمكن "
                "استخدامها."
            )
            return

        # إعادة تحليل الدردشة قبل استخدامها — يحل مشكلة "Peer id invalid"
        # التي تظهر بعد إعادة تشغيل البوت مع القنوات/المجموعات الخاصة.
        try:
            resolved_chat = await ChatService.ensure_resolved(
                client, chat.chat_id, chat.chat_link,
            )
        except Exception:
            resolved_chat = None

        if resolved_chat is None:

            await callback.message.edit_text(
                f"""
❌ تعذر الوصول إلى **{chat.chat_title}** بعد إعادة تشغيل البوت.

هذا يحدث عادة مع القنوات/المجموعات الخاصة التي ليس لها رابط محفوظ.

**الحل:** أعد ربط الدردشة من جديد (حوّل رسالة منها أو أرسل رابط الدعوة
الخاص بها)، أو احذفها من القائمة إن لم تعد بحاجتها.
""",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🗑 حذف من القائمة",
                                callback_data=f"unlink_chat:{chat.id}",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "⬅️ رجوع",
                                callback_data="my_channels",
                            )
                        ],
                    ]
                ),
            )
            return

        ok, error = await ChatService.check_bot(client, chat.chat_id)

        if not ok:
            await callback.message.edit_text(error)
            return

        ok, error = await ChatService.check_user(
            client,
            chat.chat_id,
            callback.from_user.id,
        )

        if not ok:
            await callback.message.edit_text(
                "❌ عذرًا، أنت لست مشرفًا في هذه الدردشة حاليًا."
            )
            return

    session = session_manager.get(callback.from_user.id)

    if session is None:
        session = session_manager.create(callback.from_user.id)

    session.chat_id = chat.chat_id
    session.chat_type = chat.chat_type
    session.chat_title = chat.chat_title
    session.chat_link = chat.chat_link
    session.step = GiveawayState.WAITING_DESCRIPTION

    icon = "📢" if chat.chat_type == ChatType.CHANNEL else "👥"

    await callback.message.edit_text(
        f"""
✅ **تم التحقق وربط الدردشة بنجاح**

{icon} **{chat.chat_title}**

━━━━━━━━━━━━━━━━━━

✍️ أرسل الآن وصف السحب (النص الذي سيظهر في رسالة السحب)، أو أرسل "تخطي" لعدم إضافة وصف.

مثال: 50 نجمة لفائز واحد شهريًا 🎁
"""
    )


async def unlink_chat(client, callback):

    linked_id = int(callback.matches[0].group(1))

    async with SessionLocal() as db:

        repo = LinkedChatRepository(db)

        chats = await repo.get_by_owner(callback.from_user.id)
        chat = next((c for c in chats if c.id == linked_id), None)

        if chat is None:
            await callback.answer("❌ غير موجودة.", show_alert=True)
            return

        await repo.delete(chat)

    await callback.answer("✅ تم الحذف من القائمة.", show_alert=True)
    await my_channels(client, callback)


def register(app):

    app.add_handler(
        CallbackQueryHandler(my_channels, filters.regex("^my_channels$"))
    )

    app.add_handler(
        CallbackQueryHandler(select_chat, filters.regex(r"^select_chat:(\d+)$"))
    )

    app.add_handler(
        CallbackQueryHandler(unlink_chat, filters.regex(r"^unlink_chat:(\d+)$"))
    )
