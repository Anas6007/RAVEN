from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from services.flow_labels import flow_noun


def giveaway_keyboard(
    giveaway_id: int,
    participants_count: int = 0,
    is_active: bool = True,
    drawn_once: bool = False,
    management: bool = True,
    flow_kind: str = 'giveaway',
    participant_id: int | None = None,
    votes_count: int | None = None,
    contestant_slots: int | None = None,
):
    noun = flow_noun(type('obj', (), {'flow_kind': flow_kind})())
    is_competition = flow_kind == 'competition'

    if is_competition and participant_id is not None:
        # زر التصويت على منشور المتسابق
        count_label = f" ({votes_count})" if votes_count is not None else ""
        label = f"🗳️ التصويت{count_label}" if is_active else f"🔒 التصويت مغلق{count_label}"
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton(label, callback_data=f"vote:{giveaway_id}:{participant_id}")]]
        )

    if is_competition:
        # زر المشاركة في منشور المسابقة الرئيسي
        label = "🟢 المشاركة في المسابقة" if is_active else "🔒 المسابقة مغلقة"
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton(label, callback_data=f"participate:{giveaway_id}")]]
        )

    action_label = '🎉 المشاركة'
    callback_prefix = 'participate'
    label = f"🟢 {action_label} ({participants_count})" if is_active else f"🔒 {action_label} متوقف ({participants_count})"
    rows = [[InlineKeyboardButton(label, callback_data=f"{callback_prefix}:{giveaway_id}")]]

    if not management:
        return InlineKeyboardMarkup(rows)

    if is_active:
        rows.append(
            [
                InlineKeyboardButton(f"🔴 إيقاف {noun}", callback_data=f"stop:{giveaway_id}"),
                InlineKeyboardButton(
                    "🟡 🎲 سحب الفائزين" if not drawn_once else "🟡 🎲 سحب فائزين آخرين",
                    callback_data=f"draw:{giveaway_id}",
                ),
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton("🟡 🎲 سحب فائزين آخرين", callback_data=f"draw:{giveaway_id}"),
            ]
        )

    return InlineKeyboardMarkup(rows)
