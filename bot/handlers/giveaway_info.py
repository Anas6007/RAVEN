from pyrogram import filters
from pyrogram.handlers import CallbackQueryHandler

from database.session import SessionLocal
from repositories.giveaway_repository import GiveawayRepository
from repositories.participant_repository import ParticipantRepository


async def show_participants(client, callback):
    giveaway_id = int(callback.matches[0].group(1))

    async with SessionLocal() as db:
        giveaways = GiveawayRepository(db)
        participants_repo = ParticipantRepository(db)

        giveaway = await giveaways.get(giveaway_id)

        if giveaway is None:
            await callback.answer("❌ السحب غير موجود.", show_alert=True)
            return

        participants = await participants_repo.get_all(giveaway_id)

        if not participants:
            await callback.answer("لا يوجد مشاركون حتى الآن.", show_alert=True)
            return

        text = f"👥 **المشاركون في السحب #{giveaway_id}**\n\n"
        text += f"إجمالي المشاركين: **{len(participants)}**\n\n━━━━━━━━━━━━━━\n\n"

        for i, p in enumerate(participants[:50], 1):
            name = f"@{p.username}" if p.username else p.first_name
            text += f"{i}. {name}\n"

        if len(participants) > 50:
            text += f"\n... و{len(participants) - 50} مشاركاً آخر"

        await callback.message.reply_text(text)
        await callback.answer()


async def giveaway_info(client, callback):
    giveaway_id = int(callback.matches[0].group(1))

    async with SessionLocal() as db:
        giveaways = GiveawayRepository(db)
        giveaway = await giveaways.get(giveaway_id)

        if giveaway is None:
            await callback.answer("❌ السحب غير موجود.", show_alert=True)
            return

        status = "🟢 نشط" if giveaway.is_active else "🔴 منتهي"
        description = giveaway.description or "بدون وصف."
        if giveaway.required_channels:
            required = "\n".join(f"• {ch['title']}" for ch in giveaway.required_channels)
        else:
            required = "لا يوجد اشتراك إجباري."

        captcha = "✅ مفعلة" if giveaway.enable_captcha else "❌ غير مفعلة"

        text = f"""
ℹ️ **معلومات السحب**

━━━━━━━━━━━━━━

🆔 الرقم: `{giveaway.id}`

الحالة: {status}

📝 **الوصف**

{description}

━━━━━━━━━━━━━━

👥 **عدد الفائزين**: {giveaway.winners_count}
🪑 **المقاعد**: {getattr(giveaway, "contestant_slots", None) or "غير محدد"}

👥 **المشاركون**: {giveaway.participants_count}

📢 **الاشتراك الإجباري**

{required}

━━━━━━━━━━━━━━

🛡 **الكابتشا**: {captcha}
"""

        await callback.answer()
        await callback.message.reply_text(text)


def register(app):
    app.add_handler(
        CallbackQueryHandler(
            show_participants,
            filters.regex(r"^participants:(\d+)$"),
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            giveaway_info,
            filters.regex(r"^info:(\d+)$"),
        )
    )
