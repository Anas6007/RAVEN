from pyrogram import Client
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import (
    UsernameNotOccupied,
    PeerIdInvalid,
    UserNotParticipant,
    UserAlreadyParticipant,
    RPCError,
)

import re


class ChatService:

    @staticmethod
    async def resolve_chat(client: Client, message):
        """
        استخراج القناة أو المجموعة من:
        - رسالة محولة
        - @username
        - https://t.me/username
        - https://t.me/+invitehash
        - https://t.me/joinchat/invitehash
        - https://t.me/c/chatid/messageid
        """

        # رسالة محولة
        if message.forward_from_chat:
            return message.forward_from_chat

        text = (message.text or message.caption or "").strip()

        if not text:
            raise ValueError("empty")

        # @username
        if text.startswith("@"):
            username = text[1:].strip()
            if not username:
                raise ValueError("invalid")

            return await client.get_chat(username)

        # رابط تيليجرام
        if text.startswith("https://t.me/") or text.startswith("http://t.me/"):
            link = text.replace("http://t.me/", "https://t.me/").strip()

            # رابط داخلي t.me/c/...
            match_internal = re.match(r"^https://t\.me/c/(\d+)/\d+/?$", link)
            if match_internal:
                internal_id = match_internal.group(1)
                chat_id = int(f"-100{internal_id}")
                return await client.get_chat(chat_id)

            # روابط الدعوة الخاصة
            if "/+" in link or "/joinchat/" in link:
                try:
                    return await client.join_chat(link)
                except UserAlreadyParticipant:
                    try:
                        return await client.get_chat(link)
                    except Exception:
                        raise ValueError("invalid")
                except RPCError:
                    raise ValueError("invalid")

            # رابط عام t.me/username
            username = link.replace("https://t.me/", "").strip("/")

            if not username or "/" in username:
                raise ValueError("invalid")

            return await client.get_chat(username)

        raise ValueError("invalid")

    @staticmethod
    async def ensure_resolved(client: Client, chat_id: int, chat_link: str | None = None):
        """
        يتأكد أن Pyrogram يملك بيانات هذه الدردشة (access_hash) في ذاكرة
        الجلسة قبل استخدامها. بعد إعادة تشغيل البوت قد يفشل Pyrogram في
        التعرف على قنوات/مجموعات خاصة برقم المعرّف فقط (PeerIdInvalid /
        KeyError) لأنه لم "يرَ" هذه الدردشة بعد في الجلسة الحالية.

        الحل: إن فشل get_chat(chat_id) مباشرة، نحاول إعادة تحليلها عبر
        الرابط المحفوظ (رابط عام أو رابط دعوة خاص) لأن ذلك يجبر Pyrogram
        على طلب بيانات الدردشة من تيليجرام وتخزينها من جديد.

        يرجع كائن Chat عند النجاح، ويرفع الاستثناء الأصلي عند الفشل.
        """

        try:
            return await client.get_chat(chat_id)

        except (PeerIdInvalid, KeyError) as original_error:

            if not chat_link:
                raise

            try:

                if "/+" in chat_link or "/joinchat/" in chat_link:

                    try:
                        return await client.join_chat(chat_link)

                    except UserAlreadyParticipant:
                        return await client.get_chat(chat_id)

                username = chat_link.replace(
                    "https://t.me/", ""
                ).replace(
                    "http://t.me/", ""
                ).strip("/")

                if not username:
                    raise original_error

                return await client.get_chat(username)

            except (PeerIdInvalid, KeyError, RPCError, UsernameNotOccupied):
                raise original_error

    @staticmethod
    async def get_join_link(client: Client, chat) -> str | None:
        """
        يحاول الحصول على رابط اشتراك صالح لهذه الدردشة حتى تعمل أزرار
        "اشترك" و"تحقق من الاشتراك" مع القنوات/المجموعات الخاصة أيضًا وليس
        فقط العامة:
        - إن كانت الدردشة عامة (لديها username) → رابط t.me/username.
        - إن كانت خاصة والبوت مشرف بصلاحية الدعوة → يُنشئ رابط دعوة تلقائيًا.
        - غير ذلك → None (سيظهر زر بدون رابط يطلب من المستخدم التحقق يدويًا).
        """

        username = getattr(chat, "username", None)

        if username:
            return f"https://t.me/{username}"

        try:
            return await client.export_chat_invite_link(chat.id)

        except RPCError:
            return None

    @staticmethod
    async def check_bot(client: Client, chat_id: int):

        try:
            member = await client.get_chat_member(chat_id, "me")

        except UserNotParticipant:
            return False, "❌ البوت غير موجود داخل هذه القناة أو المجموعة."

        except RPCError:
            return False, "❌ تعذر التحقق من صلاحيات البوت."

        if member.status not in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        ):
            return False, "❌ البوت موجود لكنه ليس مشرفًا."

        return True, None

    @staticmethod
    async def check_user(client: Client, chat_id: int, user_id: int):

        try:
            member = await client.get_chat_member(chat_id, user_id)

        except UserNotParticipant:
            return False, "❌ أنت لست عضوًا داخل هذه القناة أو المجموعة."

        except RPCError:
            return False, "❌ تعذر التحقق من صلاحياتك داخل هذه الدردشة."

        if member.status not in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        ):
            return False, "❌ يجب أن تكون مشرفًا داخل القناة أو المجموعة."

        return True, None

    @staticmethod
    def build_message_link(chat, message_id: int) -> str | None:
        # يبني رابطًا مباشرًا لمنشور داخل قناة/مجموعة عامة أو خاصة.
        username = getattr(chat, "username", None)
        if username:
            return f"https://t.me/{username}/{message_id}"

        chat_id = getattr(chat, "id", None)
        if isinstance(chat_id, int):
            raw = str(chat_id)
            if raw.startswith("-100"):
                return f"https://t.me/c/{raw[4:]}/{message_id}"

        return None


    @staticmethod
    def detect_type(chat):

        if chat.type == ChatType.CHANNEL:
            return "channel"

        if chat.type in (
            ChatType.GROUP,
            ChatType.SUPERGROUP,
        ):
            return "group"

        return None