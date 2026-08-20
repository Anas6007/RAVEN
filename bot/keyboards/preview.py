from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from services.flow_labels import flow_publish_button, flow_edit_button, flow_cancel_button


def preview_keyboard(session=None):

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    flow_publish_button(session),
                    callback_data="publish_giveaway",
                )
            ],
            [
                InlineKeyboardButton(
                    flow_edit_button(session),
                    callback_data="edit_giveaway",
                ),
                InlineKeyboardButton(
                    flow_cancel_button(session),
                    callback_data="cancel_giveaway",
                ),
            ],
        ]
    )
