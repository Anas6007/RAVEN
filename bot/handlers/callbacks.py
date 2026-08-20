from pyrogram import filters
from pyrogram.handlers import CallbackQueryHandler

from bot.keyboards.main_menu import main_menu
from bot.keyboards.create_giveaway import create_giveaway_menu
from bot.keyboards.create_competition import create_competition_menu

from services.session_manager import session_manager
from constants.chat_type import ChatType
from constants.states import GiveawayState


def _creation_guide(flow_kind: str) -> str:
    if flow_kind == 'competition':
        return """
🏆 **إنشاء مسابقة جديدة**

<blockquote>
1) اختر قناة أو مجموعة المسابقة الأساسية
2) أرسل وصف المسابقة
3) حدّد مقاعد المتسابقين
4) فعّل الكابتشا والاشتراك الإجباري والتعليق ووافِق/ارفُض المشاركين
5) اختر الإنهاء عند الأصوات أو عند الوقت ثم انتقل للمعاينة والنشر
</blockquote>

⚠️ يجب أن يكون منشئ المسابقة والبوت مشرفين في قنوات الاشتراك الإجباري، وكذلك في قناة التعليق/المناقشة إذا تم تفعيل شرط التعليق.

اختر الآن نوع الدردشة التي تريد ربطها:
"""
    return """
🎁 **إنشاء سحب جديد**

<blockquote>
1) اختر قناة أو مجموعة السحب الأساسية
2) أضف قنوات الاشتراك الإجباري إن أردت
3) فعّل الكابتشا أو شرط التعليق أو السحب التلقائي
4) انتقل للمعاينة ثم انشر السحب
</blockquote>

اختر الآن نوع الدردشة التي تريد ربطها:
"""


def _link_guide(title: str, icon: str, flow_kind: str) -> str:
    noun = 'المسابقة' if flow_kind == 'competition' else 'السحب'
    return f"""
{icon} **{title}**

<blockquote>
• أرسل @username أو الرابط أو رسالة محوّلة
• يجب أن تكون أنت مشرفًا
• يجب أن يكون البوت مشرفًا أيضًا
</blockquote>

📨 بانتظار بيانات {noun}...
"""


async def create_giveaway_page(client, callback):
    session_manager.delete(callback.from_user.id)
    session = session_manager.create(callback.from_user.id)
    session.flow_kind = 'giveaway'
    session.enable_captcha = False
    session.require_comment = False
    session.require_approval = False
    session.notify_winner = False
    session.announce_winner = False
    session.mode = None
    session.auto_trigger = None
    session.auto_threshold = None
    session.auto_hours = None
    session.description = None
    session.winners_count = None
    session.contestant_slots = None
    session.required_channels.clear()
    session.image = None
    session.media_type = None
    session.discussion_chat_id = None
    session.discussion_message_id = None
    session.chat_id = None
    session.chat_title = None
    session.chat_link = None
    session.step = GiveawayState.WAITING_CHANNEL
    await callback.answer()
    await callback.message.edit_text(_creation_guide('giveaway'), reply_markup=create_giveaway_menu())


async def create_competition_page(client, callback):
    session_manager.delete(callback.from_user.id)
    session = session_manager.create(callback.from_user.id)
    session.flow_kind = 'competition'
    session.enable_captcha = False
    session.require_comment = False
    session.require_approval = False
    session.notify_winner = False
    session.announce_winner = False
    session.mode = 'auto'
    session.auto_trigger = None
    session.auto_threshold = None
    session.auto_hours = None
    session.description = None
    session.winners_count = None
    session.contestant_slots = None
    session.required_channels.clear()
    session.image = None
    session.media_type = None
    session.discussion_chat_id = None
    session.discussion_message_id = None
    session.chat_id = None
    session.chat_title = None
    session.chat_link = None
    session.step = GiveawayState.WAITING_CHANNEL
    await callback.answer()
    await callback.message.edit_text(_creation_guide('competition'), reply_markup=create_competition_menu())


async def back_home(client, callback):
    await callback.answer()
    await callback.message.edit_text(
        '🏠 **القائمة الرئيسية**\n\nاختر الخدمة التي تريد استخدامها.',
        reply_markup=main_menu(),
    )


async def link_channel(client, callback):
    session = session_manager.get(callback.from_user.id) or session_manager.create(callback.from_user.id)
    session.chat_type = ChatType.CHANNEL
    session.step = GiveawayState.WAITING_CHANNEL
    await callback.answer()
    await callback.message.edit_text(_link_guide('ربط قناة', '📢', session.flow_kind))


async def link_group(client, callback):
    session = session_manager.get(callback.from_user.id) or session_manager.create(callback.from_user.id)
    session.chat_type = ChatType.GROUP
    session.step = GiveawayState.WAITING_GROUP
    await callback.answer()
    await callback.message.edit_text(_link_guide('ربط مجموعة', '👥', session.flow_kind))


async def noop(client, callback):
    await callback.answer()


def register(app):
    app.add_handler(CallbackQueryHandler(create_giveaway_page, filters.regex('^create_giveaway$')))
    app.add_handler(CallbackQueryHandler(create_competition_page, filters.regex('^create_competition$')))
    app.add_handler(CallbackQueryHandler(back_home, filters.regex('^back_home$')))
    app.add_handler(CallbackQueryHandler(link_channel, filters.regex('^link_channel$')))
    app.add_handler(CallbackQueryHandler(link_group, filters.regex('^link_group$')))
    app.add_handler(CallbackQueryHandler(noop, filters.regex('^noop$')))
