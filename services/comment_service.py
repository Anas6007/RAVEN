from services.chat_service import ChatService


async def has_verified_comment(db, giveaway_id: int, user_id: int) -> bool:
    from repositories.comment_verification_repository import CommentVerificationRepository

    repo = CommentVerificationRepository(db)
    return await repo.exists(giveaway_id, user_id)


async def build_comment_instruction(client, giveaway) -> str | None:
    # يبني رسالة HTML تطلب من المستخدم التعليق على المنشور المطلوب.
    message_id = getattr(giveaway, "discussion_message_id", None) or getattr(giveaway, "message_id", None)
    if message_id is None:
        return None

    try:
        chat = await ChatService.ensure_resolved(client, giveaway.chat_id, getattr(giveaway, "chat_link", None))
    except Exception:
        chat = type("ChatObj", (), {"id": giveaway.chat_id, "username": None})()

    link = ChatService.build_message_link(chat, message_id)
    if not link:
        return None

    return f'💬 يجب التعليق على <a href="{link}">المنشور</a> أولًا ثم إعادة محاولة التصويت.'
