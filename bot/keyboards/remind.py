from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


def remind_keyboard(giveaway_id: int):

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔔 ذكرني إذا فزت",
                    callback_data=f"remind:{giveaway_id}",
                )
            ]
        ]
    )
