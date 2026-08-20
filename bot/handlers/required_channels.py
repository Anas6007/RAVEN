from pyrogram import filters
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.errors import UsernameNotOccupied, PeerIdInvalid, RPCError

from database.session import SessionLocal
from config import logger
from repositories.banned_chat_repository import BannedChatRepository

from services.session_manager import session_manager
from services.engines.giveaway_engine import GiveawayEngine
from services.chat_service import ChatService

from constants.states import GiveawayState

from utils.filters import check_state

from bot.keyboards.giveaway_settings import channels_manage_keyboard


# ------------------------------------
# استقبال القناة أو المجموعة
# ------------------------------------
#
# نستخدم ChatService.resolve_chat نفسها المستخدمة عند ربط القناة/المجموعة
# الرئيسية للسحب، بدل تحليل يدوي محدود، لأنها تدعم أيضًا:
#   - روابط الدعوة الخاصة (t.me/+... أو t.me/joinchat/...)
#   - الروابط الداخلية (t.me/c/...)
#   - الرسائل المحوّلة
# هذا يحل مشكلة عدم إمكانية إضافة قنوات/مجموعات خاصة كاشتراك إجباري.

async def receive_required_channel(client, message):

    session = session_manager.get(message.from_user.id)

    if session is None:
        await message.reply("❌ انتهت الجلسة.")
        return

    engine = GiveawayEngine(message.from_user.id)

    try:

        chat = await ChatService.resolve_chat(client, message)

        # منع إضافة قناة/مجموعة محظورة من قِبل المطور
        async with SessionLocal() as db:

            banned_repo = BannedChatRepository(db)

            if await banned_repo.is_banned(chat.id):

                await message.reply(
                    "🚫 هذه القناة/المجموعة محظورة من استخدام البوت "
                    "بسبب مخالفتها، لا يمكن إضافتها."
                )
                return

        # التحقق من أن البوت مشرف في هذه الدردشة
        ok, error = await ChatService.check_bot(client, chat.id)

        if not ok:
            await message.reply(error)
            return

        # محاولة الحصول على رابط اشتراك صالح (عام أو رابط دعوة تلقائي)
        link = await ChatService.get_join_link(client, chat)

        added = engine.add_required_channel(
            chat_id=chat.id,
            title=chat.title,
            link=link,
        )

        if not added:

            await message.reply(
                f"⚠️ القناة/المجموعة **{chat.title}** مضافة بالفعل ضمن "
                "قنوات الاشتراك الإجباري.",
                reply_markup=channels_manage_keyboard(),
            )
            return

        warning = ""

        if not link:
            warning = (
                "\n\n⚠️ هذه القناة/المجموعة **خاصة** ولم يتمكن البوت من "
                "إنشاء رابط دعوة تلقائي لها (تأكد أن البوت مشرف بصلاحية "
                "\"دعوة المستخدمين\"). سيظهر للمشاركين زر بدون رابط "
                "ويُطلب منهم التحقق يدويًا، لذا تأكد أنك أضفت المشاركين "
                "فعليًا بنفسك."
            )

        await message.reply(
            f"""✅ تمت الإضافة:

📢 {chat.title}

عدد القنوات الحالية:

{len(session.required_channels)}{warning}""",
            reply_markup=channels_manage_keyboard()
        )

    except ValueError as e:

        if str(e) == "empty":
            await message.reply(
                "❌ لم يتم التعرف على البيانات المرسلة.\n\n"
                "أرسل إحدى الطرق التالية:\n\n"
                "• رابط عام أو خاص (دعوة).\n"
                "• معرف (@username).\n"
                "• أو رسالة محولة."
            )
            return

        await message.reply("❌ تعذر التعرف على الرابط.")

    except (
        UsernameNotOccupied,
        PeerIdInvalid,
    ):

        await message.reply(
            "❌ تعذر الوصول إلى القناة أو المجموعة.\n\n"
            "إن كانت خاصة، أرسل رسالة محولة منها أو رابط الدعوة الخاص بها."
        )

    except RPCError as e:

        logger.warning("REQUIRED CHANNEL RPC ERROR: {}", repr(e))

        await message.reply(
            "❌ تعذر الوصول إلى القناة أو المجموعة (خطأ من تيليجرام)."
        )

    except Exception as e:

        logger.exception("REQUIRED CHANNEL ERROR")

        await message.reply(
            "❌ حدث خطأ أثناء إضافة القناة."
        )


# ------------------------------------
# إضافة قناة أخرى
# ------------------------------------

async def add_more(client, callback):

    session = session_manager.get(callback.from_user.id)

    if session is None:
        await callback.answer("انتهت الجلسة.", show_alert=True)
        return

    session.step = GiveawayState.WAITING_REQUIRED_CHANNELS

    await callback.answer()

    await callback.message.edit_text(
        """
📢 أرسل القناة أو المجموعة التالية.

يمكنك إرسال:

• @username
• رابط عام
• رابط دعوة خاص (t.me/+...)
• رسالة محولة
"""
    )


# ------------------------------------
# زر قناة بدون رابط اشتراك متاح
# ------------------------------------

async def no_link_click(client, callback):

    await callback.answer(
        "🔒 هذه القناة/المجموعة خاصة ولا يوجد رابط اشتراك متاح تلقائيًا.\n\n"
        "تواصل مع منظّم السحب للانضمام إليها يدويًا، ثم اضغط "
        "\"✅ تحقق من الاشتراك\" بعد انضمامك.",
        show_alert=True,
    )


# ------------------------------------
# عرض القنوات المضافة حاليًا
# ------------------------------------

async def show_channels(client, callback):

    session = session_manager.get(callback.from_user.id)

    if session is None:
        await callback.answer("انتهت الجلسة.", show_alert=True)
        return

    if not session.required_channels:
        await callback.answer(
            "📭 لا توجد قنوات/مجموعات مضافة حتى الآن.",
            show_alert=True,
        )
        return

    lines = "\n".join(
        f"{index}. {channel['title']}"
        for index, channel in enumerate(session.required_channels, start=1)
    )

    await callback.answer()
    await callback.message.edit_text(
        f"""📂 **القنوات/المجموعات المضافة ({len(session.required_channels)})**

{lines}
""",
        reply_markup=channels_manage_keyboard(),
    )


# ------------------------------------
# حذف جميع القنوات المضافة
# ------------------------------------

async def clear_channels(client, callback):

    session = session_manager.get(callback.from_user.id)

    if session is None:
        await callback.answer("انتهت الجلسة.", show_alert=True)
        return

    if not session.required_channels:
        await callback.answer("📭 لا توجد قنوات لحذفها أصلًا.", show_alert=True)
        return

    engine = GiveawayEngine(callback.from_user.id)
    engine.clear_required_channels()

    await callback.answer("🗑 تم حذف جميع القنوات بنجاح.", show_alert=True)
    await callback.message.edit_text(
        """📢 لا توجد قنوات اشتراك إجباري حاليًا.

أرسل قناة أو مجموعة لإضافتها، أو اضغط رجوع للإعدادات.""",
        reply_markup=channels_manage_keyboard(),
    )


def register(app):

    app.add_handler(
        MessageHandler(
            receive_required_channel,
            filters.private
            & check_state(GiveawayState.WAITING_REQUIRED_CHANNELS)
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            add_more,
            filters.regex("^required_add_more$")
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            no_link_click,
            filters.regex(r"^no_link:(\d+)$"),
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            show_channels,
            filters.regex("^settings_show_channels$"),
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            clear_channels,
            filters.regex("^settings_clear_channels$"),
        )
    )
