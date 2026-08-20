from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def required_channels_keyboard(
    giveaway_id: int,
    channels: list[dict],
):
    keyboard = []

    for channel in channels:
        title = channel.get("title", "قناة")
        link = channel.get("link")

        if link:
            keyboard.append([InlineKeyboardButton(f"📢 {title}", url=link)])
        else:
            keyboard.append([InlineKeyboardButton(f"📢 {title}", callback_data=f"no_link:{giveaway_id}")])

    keyboard.append([InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data=f"check_join:{giveaway_id}")])

    return InlineKeyboardMarkup(keyboard)


def check_only_keyboard(giveaway_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ تحقق من المشاركة", callback_data=f"check_join:{giveaway_id}")]]
    )
