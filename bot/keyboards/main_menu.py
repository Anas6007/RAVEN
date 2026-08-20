from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🏆 إنشاء مسابقة", callback_data="create_competition"),
                InlineKeyboardButton("🎁 إنشاء سحب", callback_data="create_giveaway"),
            ],
            [
                InlineKeyboardButton("📊 الإحصائيات", callback_data="statistics"),
            ],
            [
                InlineKeyboardButton("💬 الدعم الفني", url="https://t.me/tn_tc"),
                InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings"),
            ],
            [
                InlineKeyboardButton("📢 قناة التحديثات", url="https://t.me/aeaeeaa"),
            ],
        ]
    )
