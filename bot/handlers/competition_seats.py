from pyrogram import filters
from pyrogram.handlers import MessageHandler

from services.session_manager import session_manager
from services.engines.giveaway_engine import GiveawayEngine
from services.flow_labels import flow_noun

from constants.states import GiveawayState

from bot.keyboards.giveaway_settings import settings_text, settings_menu
from utils.filters import check_state


async def receive_contestant_slots(client, message):
    session = session_manager.get(message.from_user.id)

    if session is None:
        await message.reply_text('❌ انتهت جلسة الإنشاء، ابدأ من جديد.')
        return

    if not message.text or not message.text.strip().isdigit():
        await message.reply_text('❌ أرسل رقمًا صحيحًا فقط لمقاعد المتسابقين.')
        return

    slots = int(message.text.strip())
    if slots < 1:
        await message.reply_text('❌ أقل عدد للمقاعد هو 1.')
        return
    # لا يوجد حد عملي للمقاعد؛ نكتفي بكونها قيمة صحيحة موجبة.

    engine = GiveawayEngine(message.from_user.id)
    engine.set_contestant_slots(slots)
    session.step = GiveawayState.SETTINGS_MENU

    noun = flow_noun(session)
    await message.reply_text(f'✅ تم تحديد مقاعد المتسابقين ({slots}).')
    await message.reply_text(settings_text(session), reply_markup=settings_menu(session))


def register(app):
    app.add_handler(
        MessageHandler(
            receive_contestant_slots,
            filters.private & filters.text & ~filters.command('start') & check_state(GiveawayState.WAITING_CONTESTANT_SLOTS),
        )
    )
