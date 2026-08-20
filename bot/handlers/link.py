from pyrogram import filters
from pyrogram.handlers import MessageHandler
from pyrogram.errors import (
    UsernameNotOccupied,
    PeerIdInvalid,
)
import re

from database.session import SessionLocal
from config import logger
from repositories.linked_chat_repository import LinkedChatRepository
from repositories.banned_chat_repository import BannedChatRepository

from services.session_manager import session_manager
from services.chat_service import ChatService
from services.flow_labels import flow_noun
from services.engines.giveaway_engine import GiveawayEngine

from constants.states import GiveawayState
from constants.chat_type import ChatType
from utils.filters import check_state



def _parse_post_link(text: str):
    text = text.strip()
    text = text.replace("http://t.me/", "https://t.me/")
    m = re.match(r"^https://t\.me/c/(\d+)/(\d+)/?$", text)
    if m:
        return int(f"-100{m.group(1)}"), int(m.group(2))

    m = re.match(r"^https://t\.me/([A-Za-z0-9_]{5,32})/(\d+)/?$", text)
    if m:
        return m.group(1), int(m.group(2))

    return None, None


def _success_text(chat_title: str, icon: str, link_note: str, noun: str) -> str:
    return f"""
✅ **تم ربط الدردشة بنجاح**

<blockquote>
{icon} **{chat_title}**{link_note}
</blockquote>

✍️ أرسل الآن وصف {noun}، أو أرسل **تخطي** لعدم إضافة وصف.
"""


async def receive_discussion_link(client, message):
    """
    استقبال رابط منشور القناة عند تفعيل "شرط التعليق". يُعالَج بشكل
    مستقل عن ربط القناة/المجموعة الرئيسية لأن الرابط هنا يحتوي على
    معرّف الرسالة أيضًا (t.me/username/123)، وهو شكل لا تدعمه
    ChatService.resolve_chat المخصصة لروابط الدردشة المجرّدة فقط.
    """
    session = session_manager.get(message.from_user.id)

    if session is None:
        await message.reply_text("❌ انتهت الجلسة، ابدأ من جديد.")
        return

    status_message = await message.reply_text("⏳ جارٍ التحقق من رابط المنشور...")

    post_text = (message.text or message.caption or "").strip()
    chat_ref, message_id = _parse_post_link(post_text)

    if chat_ref is None and message.forward_from_chat is not None:
        chat_ref = message.forward_from_chat.id
        message_id = message.forward_from_message_id

    if chat_ref is None or message_id is None:
        await status_message.edit_text(
            "❌ أرسل رابط منشور صحيحًا بصيغة t.me/username/123 أو "
            "t.me/c/123456789/123 أو رسالة محوّلة من المنشور نفسه."
        )
        return

    try:
        chat = await client.get_chat(chat_ref)
    except (PeerIdInvalid, UsernameNotOccupied):
        await status_message.edit_text(
            "❌ تعذر الوصول إلى القناة المرتبطة بهذا المنشور. تأكد أن "
            "الرابط صحيح وأن البوت مشرف فيها، أو أعد توجيه المنشور نفسه."
        )
        return
    except Exception as e:
        logger.exception("DISCUSSION LINK ERROR")
        await status_message.edit_text(f"❌ حدث خطأ غير متوقع: `{e}`")
        return

    async with SessionLocal() as db:
        banned_repo = BannedChatRepository(db)
        if await banned_repo.is_banned(chat.id):
            await status_message.edit_text(
                "🚫 هذه القناة محظورة من استخدام البوت."
            )
            return

    ok, error = await ChatService.check_bot(client, chat.id)
    if not ok:
        await status_message.edit_text(
            "❌ يجب أن يكون البوت مشرفًا في القناة صاحبة هذا المنشور أولًا."
        )
        return

    target_chat_id = chat.id

    # نحصل على معرف مجموعة النقاش الفعلية المرتبطة بالقناة من تيليجرام
    # مباشرة (وليس من بيانات إعادة التوجيه فقط)، لنستخدمه لاحقًا في
    # التحقق من أن تعليق المستخدم أُرسل فعلًا داخل المجموعة الصحيحة،
    # وليس في أي مجموعة أخرى يتواجد فيها البوت.
    discussion_group_id = None
    linked_chat = getattr(chat, "linked_chat", None)
    if linked_chat is not None:
        discussion_group_id = linked_chat.id

    session.chat_id = session.chat_id or chat.id
    session.discussion_chat_id = target_chat_id
    session.discussion_message_id = message_id
    session.discussion_group_id = discussion_group_id
    session.step = GiveawayState.SETTINGS_MENU

    engine_obj = GiveawayEngine(message.from_user.id)
    engine_obj.set_discussion(target_chat_id, message_id, discussion_group_id)

    noun = flow_noun(session)

    warning_note = (
        ""
        if discussion_group_id is not None
        else (
            "\n\n⚠️ تعذّر العثور على مجموعة نقاش مرتبطة بهذه القناة تلقائيًا؛ "
            "تأكد أن للقناة مجموعة نقاش مفعّلة من إعدادات تيليجرام حتى يعمل "
            "التحقق من التعليق بشكل صحيح."
        )
    )

    await status_message.edit_text(
        f"""
✅ **تم حفظ رابط المنشور بنجاح**

<blockquote>
• القناة: **{chat.title}**
• رقم المنشور: `{message_id}`
</blockquote>

✍️ يمكنك الآن الرجوع إلى إعدادات {noun} أو متابعة التهيئة.{warning_note}
"""
    )


async def receive_link(client, message):
    session = session_manager.get(message.from_user.id)

    if session is None:
        await message.reply_text("❌ انتهت الجلسة، ابدأ من جديد.")
        return

    status_message = await message.reply_text(
        """⏳ جارٍ التحقق من الدردشة...

تأكد أن البوت مشرف وأن الرابط/المعرف صحيح."""
    )

    try:
        chat = await ChatService.resolve_chat(client, message)

        async with SessionLocal() as db:
            banned_repo = BannedChatRepository(db)
            if await banned_repo.is_banned(chat.id):
                await status_message.edit_text(
                    "🚫 هذه القناة/المجموعة محظورة من استخدام البوت."
                )
                return

        detected = ChatService.detect_type(chat)

        if session.step == GiveawayState.WAITING_CHANNEL:
            if detected != "channel":
                await status_message.edit_text(
                    "❌ تم استلام **مجموعة** بدلًا من **قناة**."
                )
                return
            session.chat_type = ChatType.CHANNEL
        else:
            if detected != "group":
                await status_message.edit_text(
                    "❌ تم استلام **قناة** بدلًا من **مجموعة**."
                )
                return
            session.chat_type = ChatType.GROUP

        ok, error = await ChatService.check_bot(client, chat.id)
        if not ok:
            await status_message.edit_text(error)
            return

        ok, error = await ChatService.check_user(client, chat.id, message.from_user.id)
        if not ok:
            await status_message.edit_text(error)
            return

        session.chat_id = chat.id
        session.chat_title = chat.title
        session.chat_link = await ChatService.get_join_link(client, chat)
        session.step = GiveawayState.WAITING_DESCRIPTION

        async with SessionLocal() as db:
            linked_chats = LinkedChatRepository(db)
            await linked_chats.remember(
                owner_id=message.from_user.id,
                chat_id=session.chat_id,
                chat_type=session.chat_type,
                chat_title=session.chat_title,
                chat_link=session.chat_link,
            )

        icon = "📢" if session.chat_type == ChatType.CHANNEL else "👥"
        link_note = (
            ""
            if session.chat_link
            else "\n\n⚠️ هذه الدردشة خاصة ولم يتمكن البوت من إنشاء رابط دخول تلقائي."
        )

        noun = flow_noun(session)
        await status_message.edit_text(
            _success_text(chat.title, icon, link_note, noun)
        )

    except ValueError as e:
        if str(e) == "empty":
            await status_message.edit_text(
                "❌ أرسل رابطًا أو معرفًا صالحًا أو رسالة محوّلة من القناة/المجموعة."
            )
        elif str(e) == "not_admin":
            await status_message.edit_text(
                "❌ يجب أن يكون البوت مشرفًا في هذه الدردشة قبل ربطها."
            )
        elif str(e) == "user_not_admin":
            await status_message.edit_text(
                "❌ يجب أن تكون أنت أيضًا مشرفًا في هذه الدردشة."
            )
        else:
            await status_message.edit_text(
                f"❌ حدث خطأ أثناء ربط الدردشة: `{e}`"
            )

    except PeerIdInvalid:
        await status_message.edit_text(
            "❌ تعذر الوصول إلى هذه الدردشة. تأكد من الرابط أو أعد توجيه رسالة منها."
        )

    except UsernameNotOccupied:
        await status_message.edit_text(
            "❌ اسم المستخدم غير موجود أو غير صالح."
        )

    except Exception as e:
        logger.exception("LINK ERROR")
        await status_message.edit_text(
            f"❌ حدث خطأ غير متوقع: `{e}`"
        )


def register(app):

    app.add_handler(
        MessageHandler(
            receive_discussion_link,
            filters.private
            & ~filters.command("start")
            & check_state(GiveawayState.WAITING_DISCUSSION_LINK)
        )
    )

    app.add_handler(
        MessageHandler(
            receive_link,
            filters.private
            & filters.text
            & ~filters.command("start")
            & (
                check_state(GiveawayState.WAITING_CHANNEL)
                | check_state(GiveawayState.WAITING_GROUP)
            )
        )
    )
