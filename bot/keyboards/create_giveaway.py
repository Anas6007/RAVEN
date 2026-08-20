from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def create_giveaway_menu():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📢 ربط قناة",
                    callback_data="link_channel"
                ),
                InlineKeyboardButton(
                    "👥 ربط مجموعة",
                    callback_data="link_group"
                )
            ],
            [
                InlineKeyboardButton(
                    "📂 قنواتي",
                    callback_data="my_channels"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ رجوع",
                    callback_data="back_home"
                )
            ]
        ]
    )