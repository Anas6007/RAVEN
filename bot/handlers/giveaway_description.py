from pyrogram import filters
from pyrogram.handlers import MessageHandler

from services.session_manager import session_manager
from services.engines.giveaway_engine import GiveawayEngine
from services.flow_labels import flow_noun

from constants.states import GiveawayState

from utils.filters import check_state


async def receive_description(client, message):
    session = session_manager.get(message.from_user.id)

    if session is None:
        await message.reply_text('❌ انتهت جلسة الإنشاء، ابدأ من جديد.')
        return

    noun = flow_noun(session)

    if not message.text:
        await message.reply_text(f"❌ أرسل وصفًا نصيًا فقط، أو 'تخطي' لعدم إضافة وصف {noun}.")
        return

    text = message.text.strip()
    engine = GiveawayEngine(message.from_user.id)

    if text == 'تخطي':
        engine.set_description(None)
    else:
        if len(text) < 5:
            await message.reply_text('❌ الوصف قصير جدًا، حاول كتابة وصف أوضح.')
            return
        if len(text) > 1024:
            await message.reply_text('❌ الوصف طويل جدًا.')
            return
        engine.set_description(text)

    if getattr(session, 'flow_kind', 'giveaway') == 'competition':
        session.step = GiveawayState.WAITING_CONTESTANT_SLOTS
        await message.reply_text(
            f"""
✅ تم حفظ وصف المسابقة.

━━━━━━━━━━━━━━

🪑 أرسل الآن عدد مقاعد المتسابقين.

مثال:

10
25
50

✍️ أرسل رقمًا فقط.
"""
        )
        return

    session.step = GiveawayState.WAITING_WINNERS

    await message.reply_text(
        f"""
✅ تم حفظ الوصف.

━━━━━━━━━━━━━━

👥 أرسل الآن عدد الفائزين لـ {noun}.

مثال:

1
3
5

✍️ أرسل رقمًا فقط.
"""
    )


def register(app):
    app.add_handler(
        MessageHandler(
            receive_description,
            filters.text & ~filters.command('start') & check_state(GiveawayState.WAITING_DESCRIPTION)
        )
    )
