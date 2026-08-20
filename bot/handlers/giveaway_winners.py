from pyrogram import filters
from pyrogram.handlers import MessageHandler

from services.session_manager import session_manager
from services.flow_labels import flow_noun

from constants.states import GiveawayState

from utils.filters import check_state

from bot.keyboards.giveaway_settings import settings_text, settings_menu


async def receive_winners(client, message):

    session = session_manager.get(message.from_user.id)

    if session is None:
        await message.reply_text(
            "❌ انتهت جلسة الإنشاء، ابدأ من جديد."
        )
        return

    noun = flow_noun(session)

    if not message.text or not message.text.isdigit():

        await message.reply_text(
            f"""
❌ أرسل رقمًا صحيحًا فقط لـ {noun}.

أمثلة:

1
3
5
10
"""
        )
        return

    winners = int(message.text)

    if winners < 1:

        await message.reply_text(
            "❌ أقل عدد للفائزين هو 1."
        )
        return

    if winners > 100:

        await message.reply_text(
            "❌ الحد الأقصى لعدد الفائزين هو 100."
        )
        return

    session.winners_count = winners
    session.step = GiveawayState.SETTINGS_MENU

    await message.reply_text(
        f"✅ تم حفظ عدد الفائزين ({winners}).",
    )

    await message.reply_text(
        settings_text(session),
        reply_markup=settings_menu(session),
    )


def register(app):

    app.add_handler(
        MessageHandler(
            receive_winners,
            filters.private
            & filters.text
            & ~filters.command("start")
            & check_state(
                GiveawayState.WAITING_WINNERS
            )
        )
    )
