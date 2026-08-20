from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import CallbackQueryHandler

from database.session import SessionLocal

from repositories.giveaway_repository import GiveawayRepository
from repositories.participant_repository import ParticipantRepository
from repositories.vote_repository import VoteRepository
from repositories.competition_request_repository import CompetitionRequestRepository

from services.engines.security_engine import SecurityEngine
from services.engines.join_engine import JoinEngine
from services.competition_flow import complete_competition_vote, post_contestant_entry
from services.participant_session_manager import participant_session_manager
from services.chat_service import ChatService
from services.comment_service import has_verified_comment, build_comment_instruction

from config.settings import settings

from bot.keyboards.giveaway import giveaway_keyboard
from bot.keyboards.required_channels import required_channels_keyboard, check_only_keyboard
from bot.keyboards.remind import remind_keyboard
from bot.keyboards.competition_requests import competition_request_keyboard

from utils.safe_edit import safe_edit_reply_markup, safe_client_edit_reply_markup
from services.flow_labels import flow_noun

from cache.cache import cache


async def participate_click(client, callback):
    matches = callback.matches[0].groups()
    giveaway_id = int(matches[0])
    participant_id = int(matches[1]) if len(matches) > 1 and matches[1] else None

    rate_key = f'rl:participate:{callback.from_user.id}'
    attempts = await cache.incr(rate_key, ttl=10)
    if attempts > 5:
        await callback.answer('⏳ محاولات كثيرة وسريعة، انتظر قليلًا وحاول مجددًا.', show_alert=True)
        return

    async with SessionLocal() as db:
        giveaways = GiveawayRepository(db)
        participants_repo = ParticipantRepository(db)
        votes_repo = VoteRepository(db)
        giveaway = await giveaways.get(giveaway_id)

        if giveaway is None:
            await callback.answer('❌ السحب غير موجود.', show_alert=True)
            return

        noun = flow_noun(giveaway)

        # زر التصويت في المسابقة: يفتح الخاص مباشرة ليكمل التحقق هناك.
        if participant_id is not None:
            if getattr(giveaway, 'flow_kind', 'giveaway') != 'competition':
                await callback.answer('❌ هذا الرابط ليس مسابقة.', show_alert=True)
                return

            if not giveaway.is_active:
                await callback.answer('❌ انتهت هذه المسابقة.', show_alert=True)
                return

            participant = await participants_repo.get_by_id(participant_id)
            if participant is None or participant.giveaway_id != giveaway.id:
                await callback.answer('❌ المتسابق غير موجود.', show_alert=True)
                return

            existing_vote = await votes_repo.get_by_voter(giveaway.id, callback.from_user.id)
            if existing_vote:
                await callback.answer('❌ لقد قمت بتصويت لشخص في هذه المسابقة بالفعل.', show_alert=True)
                return

            if not settings.BOT_USERNAME:
                await callback.answer('❌ اسم مستخدم البوت غير مضبوط.', show_alert=True)
                return

            await callback.answer(
                url=f'https://t.me/{settings.BOT_USERNAME}?start=vote_{giveaway_id}_{participant_id}'
            )
            return

        # زر المشاركة في المسابقة
        if getattr(giveaway, 'flow_kind', 'giveaway') == 'competition':
            if giveaway.participants_count >= (giveaway.contestant_slots or 10**9):
                await callback.answer('❌ انتهت المقاعد في هذه المسابقة.', show_alert=True)
                return

            participant = await participants_repo.get_by_user(giveaway_id, callback.from_user.id)
            if participant:
                await callback.answer('✅ أنت متسابق بالفعل في هذه المسابقة.', show_alert=True)
                return

            if not settings.BOT_USERNAME:
                await callback.answer('❌ اسم مستخدم البوت غير مضبوط.', show_alert=True)
                return

            await callback.answer(url=f'https://t.me/{settings.BOT_USERNAME}?start=join_{giveaway_id}')
            return

        # السحب العادي
        action = 'التصويت' if getattr(giveaway, 'flow_kind', 'giveaway') == 'competition' else 'المشاركة'
        subject = 'مصوت' if getattr(giveaway, 'flow_kind', 'giveaway') == 'competition' else 'مشارك'

        if not giveaway.is_active:
            await callback.answer(f'🔒 هذا {noun} متوقف حاليًا، لا يمكن {action} فيه.', show_alert=True)
            return

        participant = await participants_repo.get_by_user(giveaway_id, callback.from_user.id)
        if participant:
            await callback.answer(f'✅ أنت {subject} بالفعل في هذا {noun}.', show_alert=True)
            return

    await callback.answer(url=f'https://t.me/{settings.BOT_USERNAME}?start=join_{giveaway_id}')


async def check_join(client, callback):
    giveaway_id = int(callback.matches[0].group(1))

    session = participant_session_manager.get(callback.from_user.id)

    async with SessionLocal() as db:
        giveaways = GiveawayRepository(db)
        giveaway = await giveaways.get(giveaway_id)
        if giveaway is None:
            await callback.answer('❌ السحب غير موجود.', show_alert=True)
            return

        if session and session.action == 'join_competition':
            from services.competition_flow import finalize_direct_contestant_join

            existing = await ParticipantRepository(db).get_by_user(giveaway.id, callback.from_user.id)
            if existing:
                participant_session_manager.delete(callback.from_user.id)
                await callback.answer('✅ أنت متسابق بالفعل في هذه المسابقة.', show_alert=True)
                return

            security = SecurityEngine(client)
            required_list = SecurityEngine.build_full_required_list(giveaway)
            ok, channels = await security.check_required_channels(callback.from_user.id, required_list)
            if not ok:
                await callback.answer('❌ لم تكمل الاشتراك في جميع القنوات/المجموعات المطلوبة.', show_alert=True)
                await safe_edit_reply_markup(callback.message, required_channels_keyboard(giveaway_id, channels))
                return

            giveaway, participant, _created = await finalize_direct_contestant_join(
                client, db, giveaway, callback.from_user,
            )

            if giveaway.is_active:
                try:
                    await ChatService.ensure_resolved(client, giveaway.chat_id, giveaway.chat_link)
                except Exception:
                    pass
                await safe_client_edit_reply_markup(
                    client,
                    giveaway.chat_id,
                    giveaway.message_id,
                    giveaway_keyboard(
                        giveaway.id,
                        giveaway.participants_count,
                        giveaway.is_active,
                        giveaway.drawn_once,
                        flow_kind='competition',
                        contestant_slots=getattr(giveaway, 'contestant_slots', None),
                        management=False,
                    ),
                )

            participant_session_manager.delete(callback.from_user.id)
            await callback.answer('✅ تم قبول تسجيلك في المسابقة.', show_alert=True)
            try:
                await client.send_message(callback.from_user.id, '✅ تم قبول تسجيلك في المسابقة ونشر المتسابق في القناة.')
            except Exception:
                pass
            return

        if session and session.action == 'vote':
            participants_repo = ParticipantRepository(db)
            participant = await participants_repo.get_by_id(session.participant_id) if session.participant_id else None
            if participant is None or participant.giveaway_id != giveaway.id:
                participant_session_manager.delete(callback.from_user.id)
                await callback.answer('❌ المتسابق غير موجود.', show_alert=True)
                return

            if getattr(giveaway, 'require_comment', False):
                if not await has_verified_comment(db, giveaway.id, callback.from_user.id):
                    prompt = await build_comment_instruction(client, giveaway)
                    if prompt:
                        await callback.message.reply_text(prompt, parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=check_only_keyboard(giveaway.id))
                    await callback.answer('❌ يجب التعليق على المنشور المطلوب أولًا ثم إعادة المحاولة.', show_alert=True)
                    return

            security = SecurityEngine(client)
            required_list = SecurityEngine.build_full_required_list(giveaway)
            ok, channels = await security.check_required_channels(callback.from_user.id, required_list)
            if not ok:
                await callback.answer('❌ لم تكمل الاشتراك في جميع القنوات/المجموعات المطلوبة.', show_alert=True)
                await safe_edit_reply_markup(callback.message, required_channels_keyboard(giveaway_id, channels))
                return

            ok_vote, _ = await complete_competition_vote(client, db, giveaway, participant, callback.from_user)
            if not ok_vote:
                participant_session_manager.delete(callback.from_user.id)
                await callback.answer('❌ لقد قمت بتصويت لشخص في هذه المسابقة بالفعل.', show_alert=True)
                return

            participant_session_manager.delete(callback.from_user.id)
            await callback.answer('✅ تم قبول تصويتك بنجاح.', show_alert=True)
            try:
                await client.send_message(callback.from_user.id, '✅ تم قبول تصويتك بنجاح.')
            except Exception:
                pass
            return

        participants_repo = ParticipantRepository(db)
        exists = await participants_repo.get_by_user(giveaway_id, callback.from_user.id)
        flow_word = 'التصويت' if getattr(giveaway, 'flow_kind', 'giveaway') == 'competition' else 'المشاركة'
        done_word = 'تصويتك' if getattr(giveaway, 'flow_kind', 'giveaway') == 'competition' else 'مشاركتك'

        if exists:
            await callback.answer(f"✅ أنت {'مصوت' if getattr(giveaway, 'flow_kind', 'giveaway') == 'competition' else 'مشارك'} بالفعل.", show_alert=True)
            return

        security = SecurityEngine(client)
        required_list = SecurityEngine.build_full_required_list(giveaway)
        ok, channels = await security.check_required_channels(callback.from_user.id, required_list)
        if not ok:
            await callback.answer(f'❌ لم تكمل {flow_word} في جميع القنوات/المجموعات المطلوبة.', show_alert=True)
            await safe_edit_reply_markup(callback.message, required_channels_keyboard(giveaway_id, channels))
            return

        engine = JoinEngine(client, db)
        giveaway, count = await engine.complete_join(giveaway_id, callback.from_user)
        auto_result = await engine.maybe_auto_draw_by_count(giveaway)
        if auto_result is not None:
            giveaway = auto_result

        try:
            await ChatService.ensure_resolved(client, giveaway.chat_id, giveaway.chat_link)
        except Exception:
            pass

        await safe_client_edit_reply_markup(
            client,
            giveaway.chat_id,
            giveaway.message_id,
            giveaway_keyboard(giveaway.id, giveaway.participants_count, giveaway.is_active, giveaway.drawn_once, flow_kind=getattr(giveaway, 'flow_kind', 'giveaway'), contestant_slots=getattr(giveaway, 'contestant_slots', None), management=getattr(giveaway, 'flow_kind', 'giveaway') != 'competition'),
        )

        await callback.answer(f'🎉 تمت {done_word} بنجاح.', show_alert=True)
        try:
            await client.send_message(callback.from_user.id, f'🎉 تمت {done_word} بنجاح.', reply_markup=remind_keyboard(giveaway.id))
        except Exception:
            pass


def register(app):
    app.add_handler(CallbackQueryHandler(participate_click, filters.regex(r'^participate:(\d+)$')))
    app.add_handler(CallbackQueryHandler(participate_click, filters.regex(r'^vote:(\d+)(?::(\d+))?$')))
    app.add_handler(CallbackQueryHandler(check_join, filters.regex(r'^check_join:(\d+)$')))
