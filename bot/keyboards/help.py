from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


HELP_TOPICS = {
    "create": "🎁 طريقة إنشاء سحب",
    "link": "🔗 طريقة ربط قناة/مجموعة",
    "required": "📢 قنوات الاشتراك الإجباري",
    "captcha": "🛡 الحماية (الكابتشا)",
    "mode": "🎲 السحب اليدوي والتلقائي",
    "manage": "✏️ إدارة وتعديل السحب",
    "participant": "🙋 كيف يشارك المستخدم؟",
}


def help_menu() -> InlineKeyboardMarkup:

    rows = [
        [InlineKeyboardButton(label, callback_data=f"help:{key}")]
        for key, label in HELP_TOPICS.items()
    ]

    rows.append(
        [InlineKeyboardButton("⬅️ رجوع", callback_data="settings")]
    )

    return InlineKeyboardMarkup(rows)


def help_back_keyboard() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⬅️ رجوع لقائمة الشرح", callback_data="settings_help")]
        ]
    )
