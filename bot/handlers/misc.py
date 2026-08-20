from pyrogram import filters
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.session import SessionLocal
from repositories.giveaway_repository import GiveawayRepository
from repositories.participant_repository import ParticipantRepository

from config.settings import settings

from services.session_manager import session_manager
from constants.states import GiveawayState
from bot.keyboards.giveaway_settings import settings_text, settings_menu
from bot.keyboards.help import help_menu, help_back_keyboard, HELP_TOPICS


def back_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅️ رجوع", callback_data="back_home")
    ]])


# ------------------------------------
# الإحصائيات
# ------------------------------------

async def statistics(client, callback):

    await callback.answer()

    async with SessionLocal() as db:
        giveaways_repo = GiveawayRepository(db)
        competitions_repo = GiveawayRepository(db)

        my_giveaways = await giveaways_repo.get_by_owner(callback.from_user.id, flow_kind="giveaway")
        my_competitions = await competitions_repo.get_by_owner(callback.from_user.id, flow_kind="competition")

        total_giveaways = len(my_giveaways)
        total_competitions = len(my_competitions)

        active_giveaways = sum(1 for g in my_giveaways if g.is_active)
        active_competitions = sum(1 for g in my_competitions if g.is_active)

        finished_giveaways = total_giveaways - active_giveaways
        finished_competitions = total_competitions - active_competitions

        giveaway_participants = sum(g.participants_count for g in my_giveaways)
        competition_participants = sum(g.participants_count for g in my_competitions)
        total_participants = giveaway_participants + competition_participants

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🏆 مسابقاتي", callback_data="my_competitions"),
                InlineKeyboardButton("🎁 سحوباتي", callback_data="my_giveaways"),
            ],
            [
                InlineKeyboardButton("⬅️ رجوع", callback_data="back_home"),
            ],
        ]
    )

    await callback.message.edit_text(
        f"""
📊 **الإحصائيات**

━━━━━━━━━━━━━━

🏆 **المسابقات**
• الإجمالي: {total_competitions}
• النشطة: {active_competitions}
• المنتهية: {finished_competitions}
• إجمالي المشاركين: {competition_participants}

🎁 **السحوبات**
• الإجمالي: {total_giveaways}
• النشطة: {active_giveaways}
• المنتهية: {finished_giveaways}
• إجمالي المشاركين: {giveaway_participants}

━━━━━━━━━━━━━━

👥 **الإجمالي الكلي للمشاركين:** {total_participants}
""",
        reply_markup=keyboard,
    )


# ------------------------------------
# الإعدادات
# ------------------------------------

def _settings_menu_keyboard():

    rows = [
        [
            InlineKeyboardButton(
                "📖 شرح استخدام البوت بالكامل",
                callback_data="settings_help",
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ رجوع",
                callback_data="back_home",
            )
        ],
    ]

    return InlineKeyboardMarkup(rows)


async def bot_settings(client, callback):

    await callback.answer()

    await callback.message.edit_text(
        """
⚙️ **الإعدادات**

━━━━━━━━━━━━━━

يمكنك من هنا الاطلاع على شرح كامل لطريقة استخدام البوت خطوة بخطوة.

━━━━━━━━━━━━━━
""",
        reply_markup=_settings_menu_keyboard(),
    )


# ------------------------------------
# قسم الشرح (طريقة استخدام البوت بالكامل عبر أزرار)
# ------------------------------------

HELP_TEXTS = {
    "create": """
🎁 **طريقة إنشاء سحب**

1️⃣ من القائمة الرئيسية اضغط **إنشاء سحب**.

2️⃣ اربط القناة أو المجموعة (أو اخترها من **قنواتي** إن سبق ربطها).

3️⃣ أرسل **وصف السحب** ثم **عدد الفائزين**.

4️⃣ اضبط الإعدادات الإضافية (الكابتشا، قنوات الاشتراك الإجباري، الشروط،
نوع السحب) من قائمة الإعدادات.

5️⃣ اضغط **متابعة** لمعاينة السحب، ثم **نشر السحب** لنشره فورًا في
القناة/المجموعة.
""",
    "link": """
🔗 **طريقة ربط قناة أو مجموعة**

يمكنك ربط القناة/المجموعة بإحدى الطرق التالية:

• إرسال رابطها العام (t.me/username).
• إرسال رابط دعوة خاص (t.me/+... أو t.me/joinchat/...).
• إرسال المعرف (@username).
• تحويل أي رسالة منها إلى البوت.

⚠️ **شروط أساسية**:

👤 يجب أن تكون **مشرفًا** فيها.

🤖 يجب إضافة **البوت كمشرف** أيضًا، مع صلاحية **حذف/تعديل رسائل** على
الأقل (لتحديث لوحة المشاركين)، ويُفضّل أيضًا صلاحية **دعوة المستخدمين**
حتى يتمكن البوت من إنشاء رابط اشتراك تلقائي إن كانت خاصة.
""",
    "required": """
📢 **قنوات الاشتراك الإجباري**

من قائمة إعدادات السحب اضغط **قنوات الاشتراك**، ثم أرسل القنوات
والمجموعات التي تريد إجبار المشاركين على الاشتراك بها (تدعم العامة
والخاصة معًا).

بعد إرسال كل قناة يمكنك إرسال التالية مباشرة أو الضغط **أضف قناة أخرى**،
وعند الانتهاء اضغط **تم — رجوع للإعدادات**.

📌 ملاحظة: البوت يتحقق تلقائيًا من اشتراك المستخدم في **قناة/مجموعة
السحب نفسها** بالإضافة لهذه القنوات، فلا حاجة لإضافتها يدويًا.

⚠️ إن كانت إحدى القنوات **خاصة** ولم يتمكن البوت من إنشاء رابط دعوة
تلقائي لها (بسبب نقص الصلاحيات)، سيظهر للمشاركين زر بلا رابط ويُطلب
منهم التحقق يدويًا من انضمامهم.
""",
    "captcha": """
🛡 **الحماية (الكابتشا)**

عند تفعيل الكابتشا من إعدادات السحب، يجب على كل مشارك حل عملية حسابية
بسيطة قبل المتابعة لخطوات الاشتراك، لمنع الحسابات الآلية (البوتات) من
التلاعب بنتائج السحب.

ترتيب خطوات المشاركة الكاملة:

1️⃣ الضغط على زر **المشاركة**.
2️⃣ حل الكابتشا (إن كانت مفعّلة).
3️⃣ الاشتراك في قناة/مجموعة السحب نفسها (إن لم يكن مشتركًا).
4️⃣ الاشتراك في قنوات الاشتراك الإجباري الإضافية (إن وُجدت).
5️⃣ تسجيل المشاركة تلقائيًا بعد اكتمال كل ما سبق.
""",
    "mode": """
🎲 **السحب اليدوي والتلقائي**

🖐 **يدوي**: تسحب الفائزين بنفسك بالضغط على زر **سحب الفائزين** بالرسالة
المنشورة (أو من "سحوباتي") في أي وقت تريده. يمكنك تكرار السحب أكثر من
مرة لاختيار فائزين إضافيين من بين من لم يفوزوا بعد.

⏰ **تلقائي**: يسحب البوت الفائزين تلقائيًا بإحدى طريقتين تختارها عند
الإنشاء:

🔢 عند وصول عدد معيّن من المشاركين.
⏰ عند حلول وقت محدد (بعد عدد ساعات تحدده من لحظة النشر).
""",
    "manage": """
✏️ **إدارة وتعديل السحب**

من **سحوباتي** اختر السحب المطلوب للاطلاع على تفاصيله، وستجد أزرارًا
لـ:

🎲 سحب الفائزين يدويًا.
⛔ إيقاف المشاركة في السحب.
📊 عرض قائمة المشاركين.

يمكن لمنشئ السحب، وأي مشرف داخل القناة/المجموعة نفسها، القيام بهذه
الإجراءات من رسالة السحب المنشورة مباشرة.
""",
    "participant": """
🙋 **كيف يشارك المستخدم في السحب؟**

1️⃣ يضغط زر **🎉 المشاركة** أسفل رسالة السحب.
2️⃣ يُفتح للبوت في الخاص تلقائيًا.
3️⃣ يحل الكابتشا إن كانت مفعّلة.
4️⃣ يشترك في القناة/المجموعة المستضيفة للسحب وأي قنوات إجبارية أخرى.
5️⃣ يضغط **✅ تحقق من الاشتراك** بعد الانضمام لتُسجَّل مشاركته تلقائيًا.

يمكنه أيضًا الضغط على **🔔 ذكرني إذا فزت** لضمان وصول إشعار الفوز في
الخاص.
""",
}


async def settings_help(client, callback):

    await callback.answer()

    await callback.message.edit_text(
        """
📖 **شرح استخدام البوت**

اختر الموضوع الذي تريد معرفة المزيد عنه:
""",
        reply_markup=help_menu(),
    )


async def help_topic(client, callback):

    topic = callback.matches[0].group(1)

    text = HELP_TEXTS.get(topic)

    if text is None:
        await callback.answer("❌ هذا الموضوع غير متاح.", show_alert=True)
        return

    title = HELP_TOPICS.get(topic, "📖 شرح")

    await callback.answer()

    await callback.message.edit_text(
        f"{title}\n{text}",
        reply_markup=help_back_keyboard(),
    )


# ------------------------------------
# الدعم الفني
# ------------------------------------

async def support(client, callback):

    await callback.answer()

    await callback.message.edit_text(
        """
💬 **الدعم الفني**

━━━━━━━━━━━━━━

للتواصل المباشر مع الدعم الفني، استخدم الزر أدناه.
""",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 فتح الدعم", url="https://t.me/tn_tc")],
            [InlineKeyboardButton("⬅️ رجوع", callback_data="back_home")],
        ]),
    )


# ------------------------------------
# قناة التحديثات
# ------------------------------------

async def updates(client, callback):

    await callback.answer()

    await callback.message.edit_text(
        """
📢 **قناة التحديثات**

━━━━━━━━━━━━━━

تابع آخر التحديثات والمميزات الجديدة من الرابط أدناه.
""",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 فتح قناة التحديثات", url="https://t.me/aeaeeaa")],
            [InlineKeyboardButton("⬅️ رجوع", callback_data="back_home")],
        ]),
    )


# ------------------------------------
# تعديل السحب (أثناء الإنشاء، قبل النشر)
# ------------------------------------

async def edit_giveaway(client, callback):

    session = session_manager.get(callback.from_user.id)

    if session is None:
        await callback.answer("انتهت الجلسة.", show_alert=True)
        return

    session.step = GiveawayState.SETTINGS_MENU

    await callback.answer()

    await callback.message.edit_text(
        settings_text(session),
        reply_markup=settings_menu(session),
    )


def register(app):

    app.add_handler(
        CallbackQueryHandler(
            statistics,
            filters.regex("^statistics$"),
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            bot_settings,
            filters.regex("^settings$"),
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            settings_help,
            filters.regex("^settings_help$"),
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            help_topic,
            filters.regex(r"^help:(\w+)$"),
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            support,
            filters.regex("^support$"),
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            updates,
            filters.regex("^updates$"),
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            edit_giveaway,
            filters.regex("^edit_giveaway$"),
        )
    )
