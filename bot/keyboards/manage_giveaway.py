\
from pyrogram.types import InlineKeyboardButton
from pyrogram.types import InlineKeyboardMarkup

from services.flow_labels import flow_noun, flow_gerund


def manage_giveaway_keyboard(giveaway_id: int, is_active: bool = True, flow_kind: str = "giveaway"):
    noun = flow_noun(type("obj", (), {"flow_kind": flow_kind})())
    gerund = flow_gerund(type("obj", (), {"flow_kind": flow_kind})())

    rows = [
        [
            InlineKeyboardButton(
                f"🎲 {gerund} الفائزين",
                callback_data=f"draw:{giveaway_id}",
            )
        ],
        [
            InlineKeyboardButton(
                f"✏️ تعديل {noun}",
                callback_data=f"giveaway_edit_menu:{giveaway_id}",
            )
        ],
        [
            InlineKeyboardButton(
                "📊 المشاركون",
                callback_data=f"participants:{giveaway_id}",
            )
        ],
    ]

    if is_active:
        rows.insert(
            1,
            [
                InlineKeyboardButton(
                    f"⛔ إيقاف {noun}",
                    callback_data=f"stop:{giveaway_id}",
                )
            ],
        )

    return InlineKeyboardMarkup(rows)


def giveaway_edit_menu_keyboard(giveaway_id: int, flow_kind: str = "giveaway"):
    noun = flow_noun(type("obj", (), {"flow_kind": flow_kind})())
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"📝 تعديل وصف {noun}",
                    callback_data=f"giveaway_edit_field:{giveaway_id}:description",
                )
            ],
            [
                InlineKeyboardButton(
                    "👥 تعديل عدد الفائزين",
                    callback_data=f"giveaway_edit_field:{giveaway_id}:winners",
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ رجوع",
                    callback_data=f"giveaway_manage:{giveaway_id}",
                )
            ],
        ]
    )
