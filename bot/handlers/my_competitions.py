from math import ceil

from pyrogram import filters
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.session import SessionLocal
from repositories.giveaway_repository import GiveawayRepository
from repositories.participant_repository import ParticipantRepository

from bot.keyboards.manage_giveaway import manage_giveaway_keyboard
from services.flow_labels import flow_main_list_title, flow_empty_list_text

from utils.text import safe_excerpt


PAGE_SIZE = 5


def _back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ رجوع", callback_data="back_home")]])


def _pagination_keyboard(items, page: int):
    total_pages = max(1, ceil(len(items) / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE

    rows = []
    for giveaway in items[start:end]:
        status_icon = "🟢" if giveaway.is_active else "🔴"
        rows.append([
            InlineKeyboardButton(
                f"{status_icon} #{giveaway.id} — {safe_excerpt(giveaway.description, 20)}",
                callback_data=f"competition_manage:{giveaway.id}",
            )
        ])

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"my_competitions_page:{page-1}"))
    nav.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"my_competitions_page:{page+1}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton("⬅️ رجوع", callback_data="back_home")])
    return InlineKeyboardMarkup(rows)


async def my_competitions(client, callback):
    await callback.answer()

    async with SessionLocal() as db:
        giveaways = GiveawayRepository(db)
        items = await giveaways.get_by_owner(callback.from_user.id, flow_kind="competition")

        if not items:
            await callback.message.edit_text(
                f"""
{flow_main_list_title(type('obj', (), {'flow_kind': 'competition'})())}

━━━━━━━━━━━━━━

{flow_empty_list_text(type('obj', (), {'flow_kind': 'competition'})())}
""",
                reply_markup=_back_keyboard(),
            )
            return

        text = f"{flow_main_list_title(type('obj', (), {'flow_kind': 'competition'})())}\\n\\n━━━━━━━━━━━━━━\\n\\n"
        text += f"إجمالي المسابقات: **{len(items)}**\\n\\n"

        for giveaway in items[:PAGE_SIZE]:
            status = "🟢 نشط" if giveaway.is_active else "🔴 منتهي"
            seats = getattr(giveaway, "contestant_slots", None) or "غير محدد"
            text += (
                f"🆔 `{giveaway.id}` | {status}\\n"
                f"📝 {safe_excerpt(giveaway.description, 40)}\\n"
                f"📢 {giveaway.chat_title}\\n"
                f"👥 المشاركون: {giveaway.participants_count}\\n"
                f"🪑 المقاعد: {seats}\\n\\n"
            )

        await callback.message.edit_text(text, reply_markup=_pagination_keyboard(items, 1))


async def my_competitions_page(client, callback):
    page = int(callback.matches[0].group(1))

    async with SessionLocal() as db:
        giveaways = GiveawayRepository(db)
        items = await giveaways.get_by_owner(callback.from_user.id, flow_kind="competition")

    if not items:
        await callback.answer("لا توجد مسابقات.", show_alert=True)
        return

    await callback.answer()
    text = f"{flow_main_list_title(type('obj', (), {'flow_kind': 'competition'})())}\\n\\n━━━━━━━━━━━━━━\\n\\n"
    text += f"إجمالي المسابقات: **{len(items)}**\\n\\n"

    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    for giveaway in items[start:end]:
        status = "🟢 نشط" if giveaway.is_active else "🔴 منتهي"
        seats = getattr(giveaway, "contestant_slots", None) or "غير محدد"
        text += (
            f"🆔 `{giveaway.id}` | {status}\\n"
            f"📝 {safe_excerpt(giveaway.description, 40)}\\n"
            f"📢 {giveaway.chat_title}\\n"
            f"👥 المشاركون: {giveaway.participants_count}\\n"
            f"🪑 المقاعد: {seats}\\n\\n"
        )

    await callback.message.edit_text(text, reply_markup=_pagination_keyboard(items, page))


async def competition_manage(client, callback):
    giveaway_id = int(callback.matches[0].group(1))

    async with SessionLocal() as db:
        giveaways = GiveawayRepository(db)
        participants_repo = ParticipantRepository(db)

        giveaway = await giveaways.get(giveaway_id)

        if giveaway is None:
            await callback.answer("❌ المسابقة غير موجودة.", show_alert=True)
            return

        if giveaway.owner_id != callback.from_user.id:
            await callback.answer("❌ ليس لديك صلاحية.", show_alert=True)
            return

        participants = await participants_repo.get_all(giveaway_id)

        status = "🟢 نشط" if giveaway.is_active else "🔴 منتهي"
        required = (
            "\\n".join(f"• {ch['title']}" for ch in giveaway.required_channels)
            if giveaway.required_channels
            else "لا يوجد."
        )
        captcha = "✅ مفعلة" if giveaway.enable_captcha else "❌ غير مفعلة"
        comment = "✅ مفعّل" if getattr(giveaway, "require_comment", False) else "❌ غير مفعّل"

        text = f"""
📋 **تفاصيل المسابقة #{giveaway.id}**

━━━━━━━━━━━━━━

الحالة: {status}

📝 **الوصف**

{giveaway.description or "بدون وصف"}

━━━━━━━━━━━━━━

👥 **عدد الفائزين**: {giveaway.winners_count}
🪑 **المقاعد**: {getattr(giveaway, "contestant_slots", None) or "غير محدد"}

👥 **المشاركون**: {len(participants)}

📢 **الاشتراك الإجباري**

{required}

🛡 **الكابتشا**: {captcha}
💬 **شرط التعليق**: {comment}

📢 **القناة/المجموعة**: {giveaway.chat_title}
"""

        await callback.answer()
        await callback.message.edit_text(
            text,
            reply_markup=manage_giveaway_keyboard(
                giveaway_id,
                giveaway.is_active,
                getattr(giveaway, "flow_kind", "competition"),
            ),
        )


def register(app):
    app.add_handler(CallbackQueryHandler(my_competitions, filters.regex("^my_competitions$")))
    app.add_handler(CallbackQueryHandler(my_competitions_page, filters.regex(r"^my_competitions_page:(\\d+)$")))
    app.add_handler(CallbackQueryHandler(competition_manage, filters.regex(r"^competition_manage:(\\d+)$")))
