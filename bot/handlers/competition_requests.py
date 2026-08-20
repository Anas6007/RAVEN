from pyrogram import filters
from pyrogram.handlers import CallbackQueryHandler

from database.session import SessionLocal
from repositories.competition_request_repository import CompetitionRequestRepository
from repositories.giveaway_repository import GiveawayRepository
from repositories.participant_repository import ParticipantRepository

from bot.keyboards.competition_requests import competition_request_keyboard
from services.competition_flow import post_contestant_entry
from services.engines.security_engine import SecurityEngine
from services.flow_labels import flow_noun
from utils.safe_edit import safe_client_edit_reply_markup
from bot.keyboards.giveaway import giveaway_keyboard


async def competition_request_accept(client, callback):
    request_id = int(callback.matches[0].group(1))
    async with SessionLocal() as db:
        requests_repo = CompetitionRequestRepository(db)
        giveaways_repo = GiveawayRepository(db)
        giveaway = None
        request_obj = await requests_repo.get(request_id)
        if request_obj is None:
            await callback.answer('❌ الطلب غير موجود.', show_alert=True)
            return
        giveaway = await giveaways_repo.get(request_obj.giveaway_id)
        if giveaway is None:
            await callback.answer('❌ المسابقة غير موجودة.', show_alert=True)
            return
        if giveaway.owner_id != callback.from_user.id:
            sec = SecurityEngine(client)
            if not await sec.is_authorized_manager(callback.from_user.id, giveaway):
                await callback.answer('❌ ليس لديك صلاحية.', show_alert=True)
                return
        if request_obj.status != 'pending':
            await callback.answer('⚠️ تم التعامل مع هذا الطلب مسبقًا.', show_alert=True)
            return
        if giveaway.participants_count >= (getattr(giveaway, 'contestant_slots', None) or 10**9):
            await callback.answer('❌ انتهت المقاعد في هذه المسابقة.', show_alert=True)
            return
        await requests_repo.set_status(request_obj, 'approved')
        participants_repo = ParticipantRepository(db)
        existing = await participants_repo.get_by_user(giveaway.id, request_obj.user_id)
        if existing:
            await callback.answer('⚠️ هذا المتسابق مضاف بالفعل.', show_alert=True)
            return
        user = await client.get_users(request_obj.user_id)
        participant = await participants_repo.create(
            giveaway_id=giveaway.id,
            user_id=user.id,
            first_name=user.first_name,
            username=getattr(user, 'username', None),
            passed_captcha=False,
            votes_count=0,
            post_message_id=None,
        )
        await post_contestant_entry(client, giveaway, participant, db)
        giveaway = await giveaways_repo.update(giveaway, participants_count=(giveaway.participants_count + 1))
        try:
            await safe_client_edit_reply_markup(
                client,
                giveaway.chat_id,
                giveaway.message_id,
                giveaway_keyboard(
                    giveaway.id,
                    giveaway.participants_count,
                    giveaway.is_active,
                    giveaway.drawn_once,
                    management=False,
                    flow_kind='competition',
                    contestant_slots=getattr(giveaway, 'contestant_slots', None),
                ),
            )
        except Exception:
            pass
        await callback.answer('✅ تم قبول المتسابق ونشره في القناة.', show_alert=True)
        try:
            await client.send_message(request_obj.user_id, f'✅ تم قبول طلب اشتراكك في {flow_noun(giveaway)}.')
        except Exception:
            pass
        try:
            await callback.message.edit_reply_markup(competition_request_keyboard(request_id))
        except Exception:
            pass


async def competition_request_reject(client, callback):
    request_id = int(callback.matches[0].group(1))
    async with SessionLocal() as db:
        requests_repo = CompetitionRequestRepository(db)
        request_obj = await requests_repo.get(request_id)
        if request_obj is None:
            await callback.answer('❌ الطلب غير موجود.', show_alert=True)
            return
        giveaways_repo = GiveawayRepository(db)
        giveaway = await giveaways_repo.get(request_obj.giveaway_id)
        if giveaway is None:
            await callback.answer('❌ المسابقة غير موجودة.', show_alert=True)
            return
        if giveaway.owner_id != callback.from_user.id:
            sec = SecurityEngine(client)
            if not await sec.is_authorized_manager(callback.from_user.id, giveaway):
                await callback.answer('❌ ليس لديك صلاحية.', show_alert=True)
                return
        if request_obj.status != 'pending':
            await callback.answer('⚠️ تم التعامل مع هذا الطلب مسبقًا.', show_alert=True)
            return
        await requests_repo.set_status(request_obj, 'rejected')
        await callback.answer('✅ تم رفض الطلب.', show_alert=True)
        try:
            await client.send_message(request_obj.user_id, f'❌ تم رفض طلب الاشتراك في {flow_noun(giveaway)}.')
        except Exception:
            pass
        try:
            await callback.message.edit_reply_markup(competition_request_keyboard(request_id))
        except Exception:
            pass


def register(app):
    app.add_handler(CallbackQueryHandler(competition_request_accept, filters.regex(r'^competition_request_accept:(\d+)$')))
    app.add_handler(CallbackQueryHandler(competition_request_reject, filters.regex(r'^competition_request_reject:(\d+)$')))
