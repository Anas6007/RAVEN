from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def competition_request_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('✅ قبول', callback_data=f'competition_request_accept:{request_id}'),
            InlineKeyboardButton('❌ رفض', callback_data=f'competition_request_reject:{request_id}'),
        ]
    ])
