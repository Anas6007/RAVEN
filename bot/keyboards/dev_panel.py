from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


def dev_menu_keyboard() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📊 إحصائيات عامة", callback_data="dev_stats"),
            ],
            [
                InlineKeyboardButton("📢 القنوات", callback_data="dev_channels"),
                InlineKeyboardButton("👥 القروبات", callback_data="dev_groups"),
            ],
            [
                InlineKeyboardButton("🙋 المستخدمون", callback_data="dev_users"),
            ],
            [
                InlineKeyboardButton("📨 إذاعة", callback_data="dev_broadcast"),
            ],
            [
                InlineKeyboardButton("🚫 حظر قناة/مجموعة", callback_data="dev_ban"),
                InlineKeyboardButton("✅ فك حظر", callback_data="dev_unban"),
            ],
            [
                InlineKeyboardButton("📋 قائمة المحظورين", callback_data="dev_banned_list"),
            ],
        ]
    )


def dev_back_keyboard() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⬅️ رجوع للوحة المطور", callback_data="dev_home")]
        ]
    )


def dev_cancel_keyboard() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("❌ إلغاء", callback_data="dev_home")]
        ]
    )


def dev_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ تأكيد الإرسال للجميع", callback_data="dev_broadcast_confirm"),
            ],
            [
                InlineKeyboardButton("❌ إلغاء", callback_data="dev_home"),
            ],
        ]
    )


def dev_unban_list_keyboard(banned_chats) -> InlineKeyboardMarkup:

    rows = []

    for chat in banned_chats[:25]:

        title = chat.chat_title or str(chat.chat_id)

        rows.append(
            [
                InlineKeyboardButton(
                    f"✅ فك حظر {title}",
                    callback_data=f"dev_unban_id:{chat.chat_id}",
                )
            ]
        )

    rows.append(
        [InlineKeyboardButton("⬅️ رجوع للوحة المطور", callback_data="dev_home")]
    )

    return InlineKeyboardMarkup(rows)
