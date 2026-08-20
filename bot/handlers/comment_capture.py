from pyrogram import filters
from pyrogram.handlers import MessageHandler

from database.session import SessionLocal
from repositories.giveaway_repository import GiveawayRepository
from repositories.comment_verification_repository import CommentVerificationRepository


async def capture_comment(client, message):
    if not message.from_user or message.from_user.is_bot:
        return

    reply = message.reply_to_message
    if reply is None:
        return

    source = getattr(reply, "forward_from_chat", None)
    source_msg_id = getattr(reply, "forward_from_message_id", None)
    if source is None or source_msg_id is None:
        return

    async with SessionLocal() as db:
        giveaways_repo = GiveawayRepository(db)
        comments_repo = CommentVerificationRepository(db)

        giveaways = await giveaways_repo.get_active()
        for giveaway in giveaways:
            if not getattr(giveaway, "require_comment", False):
                continue
            if getattr(giveaway, "discussion_chat_id", None) != source.id:
                continue
            if getattr(giveaway, "discussion_message_id", None) != source_msg_id:
                continue

            # يجب أن يكون التعليق قد أُرسل فعليًا داخل مجموعة النقاش
            # الحقيقية المرتبطة بالقناة، وليس في أي مجموعة أخرى يتواجد
            # فيها البوت (تُجلب discussion_group_id من تيليجرام مباشرة
            # عند ربط رابط المنشور). السحوبات القديمة التي لا تملك هذا
            # الحقل محفوظًا (أُنشئت قبل هذا التحقق) تبقى تعمل كالسابق
            # اتقاءً لكسرها فجأة.
            required_group_id = getattr(giveaway, "discussion_group_id", None)
            if required_group_id is not None and message.chat.id != required_group_id:
                continue

            await comments_repo.remember(giveaway.id, message.from_user.id)


def register(app):
    app.add_handler(MessageHandler(capture_comment, filters.group))
