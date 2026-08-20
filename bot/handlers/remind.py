from pyrogram import filters
from pyrogram.handlers import CallbackQueryHandler

from database.session import SessionLocal
from repositories.participant_repository import ParticipantRepository


async def remind_me(client, callback):

    giveaway_id = int(callback.matches[0].group(1))

    async with SessionLocal() as db:

        participants = ParticipantRepository(db)

        participant = await participants.get_by_user(
            giveaway_id,
            callback.from_user.id,
        )

        if participant is None:

            await callback.answer(
                "❌ أنت لست مشاركًا في هذا السحب.",
                show_alert=True,
            )
            return

        participant.remind_on_win = True

        await participants.save()

    await callback.answer(
        "✅ سنقوم بمراسلتك في الخاص إذا فزت.\n\n"
        "📌 لا تحظر البوت ولا تحذف المحادثة معه حتى يصلك إشعار الفوز.",
        show_alert=True,
    )


def register(app):

    app.add_handler(
        CallbackQueryHandler(
            remind_me,
            filters.regex(r"^remind:(\d+)$"),
        )
    )
