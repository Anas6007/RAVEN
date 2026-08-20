from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler

from database.session import SessionLocal

from repositories.giveaway_repository import GiveawayRepository
from repositories.participant_repository import ParticipantRepository

from services.participant_session_manager import participant_session_manager
from services.engines.captcha_engine import CaptchaEngine
from services.engines.join_engine import JoinEngine
from services.engines.security_engine import SecurityEngine
from services.chat_service import ChatService
from services.competition_flow import complete_competition_vote
from services.comment_service import has_verified_comment, build_comment_instruction

from bot.keyboards.giveaway import giveaway_keyboard
from bot.keyboards.remind import remind_keyboard
from bot.keyboards.required_channels import required_channels_keyboard, check_only_keyboard
from services.flow_labels import flow_noun

from utils.safe_edit import safe_client_edit_reply_markup


async def participant_captcha(client, message):
    session = participant_session_manager.get(message.from_user.id)
    if session is None:
        return

    if not message.text or not message.text.strip().isdigit():
        await message.reply_text('❌ أرسل رقمًا فقط.')
        return

    correct = CaptchaEngine.check(session.captcha_answer, message.text.strip())
    if not correct:
        question, answer = CaptchaEngine.generate()
        session.question = question
        session.captcha_answer = answer
        await message.reply_text(f"""
❌ إجابة خاطئة.

حاول مرة أخرى.

{question} = ؟
""")
        return

    giveaway_id = session.giveaway_id

    async with SessionLocal() as db:
        giveaways = GiveawayRepository(db)
        giveaway = await giveaways.get(giveaway_id)

        if giveaway is None:
            participant_session_manager.delete(message.from_user.id)
            await message.reply_text('❌ السحب غير موجود.')
            return

        security = SecurityEngine(client)
        required_list = SecurityEngine.build_full_required_list(giveaway)
        ok, channels = await security.check_required_channels(message.from_user.id, required_list)

        comment_prompt = None
        if getattr(giveaway, 'require_comment', False):
            comment_prompt = await build_comment_instruction(client, giveaway)

        if not ok:
            word = 'التصويت' if getattr(giveaway, 'flow_kind', 'giveaway') == 'competition' else 'المشاركة'
            text = f'✅ تم التحقق بنجاح.\n\n📢 قبل {word} يجب الاشتراك في القنوات/المجموعات التالية:'
            if comment_prompt:
                text += f"\n\n{comment_prompt}"
            await message.reply_text(
                text,
                reply_markup=required_channels_keyboard(giveaway.id, channels),
                parse_mode=ParseMode.HTML if comment_prompt else None,
                disable_web_page_preview=True,
            )
            return

        if session.action == 'join_competition':
            from services.competition_flow import finalize_direct_contestant_join

            existing = await ParticipantRepository(db).get_by_user(giveaway.id, message.from_user.id)
            if existing:
                participant_session_manager.delete(message.from_user.id)
                await message.reply_text('✅ أنت متسابق بالفعل في هذه المسابقة.')
                return

            giveaway, participant, _created = await finalize_direct_contestant_join(
                client, db, giveaway, message.from_user,
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

            participant_session_manager.delete(message.from_user.id)
            await message.reply_text('✅ تم قبول تسجيلك في المسابقة ونشر المتسابق في القناة.')
            return

        if session.action == 'vote':
            participants_repo = ParticipantRepository(db)
            participant = await participants_repo.get_by_id(session.participant_id) if session.participant_id else None
            if participant is None or participant.giveaway_id != giveaway.id:
                participant_session_manager.delete(message.from_user.id)
                await message.reply_text('❌ المتسابق غير موجود.')
                return

            if getattr(giveaway, 'require_comment', False) and not await has_verified_comment(db, giveaway.id, message.from_user.id):
                text = comment_prompt or '💬 يجب التعليق على المنشور المطلوب أولًا ثم إعادة محاولة التصويت.'
                await message.reply_text(
                    text,
                    reply_markup=check_only_keyboard(giveaway.id),
                    parse_mode=ParseMode.HTML if comment_prompt else None,
                    disable_web_page_preview=True,
                )
                return

            ok_vote, _ = await complete_competition_vote(client, db, giveaway, participant, message.from_user)
            if not ok_vote:
                participant_session_manager.delete(message.from_user.id)
                await message.reply_text('❌ لقد قمت بتصويت لشخص في هذه المسابقة بالفعل.')
                return

            participant_session_manager.delete(message.from_user.id)
            await message.reply_text('✅ تم قبول تصويتك بنجاح.')
            return

        if getattr(giveaway, 'require_comment', False) and not await has_verified_comment(db, giveaway.id, message.from_user.id):
            text = comment_prompt or '💬 يجب التعليق على المنشور المطلوب أولًا ثم إعادة محاولة المشاركة.'
            await message.reply_text(
                text,
                reply_markup=check_only_keyboard(giveaway.id),
                parse_mode=ParseMode.HTML if comment_prompt else None,
                disable_web_page_preview=True,
            )
            return

        engine = JoinEngine(client, db)
        giveaway, participants = await engine.complete_join(giveaway.id, message.from_user)
        auto_result = await engine.maybe_auto_draw_by_count(giveaway)
        if auto_result is not None:
            giveaway = auto_result

        if giveaway.is_active:
            try:
                await ChatService.ensure_resolved(client, giveaway.chat_id, giveaway.chat_link)
            except Exception:
                pass
            await safe_client_edit_reply_markup(
                client,
                session.chat_id,
                session.message_id,
                giveaway_keyboard(
                    giveaway.id,
                    participants,
                    giveaway.is_active,
                    giveaway.drawn_once,
                    flow_kind=getattr(giveaway, 'flow_kind', 'giveaway'),
                    contestant_slots=getattr(giveaway, 'contestant_slots', None),
                    management=getattr(giveaway, 'flow_kind', 'giveaway') != 'competition',
                ),
            )

    participant_session_manager.delete(message.from_user.id)
    reply_markup = remind_keyboard(giveaway.id) if getattr(giveaway, 'flow_kind', 'giveaway') != 'competition' else None
    await message.reply_text(
        f"""
✅ تم التحقق بنجاح.

🎉 أصبحت {('مصوتًا' if getattr(giveaway, 'flow_kind', 'giveaway') == 'competition' else 'مشاركًا')} في {flow_noun(giveaway)}.
""",
        reply_markup=reply_markup,
    )


def register(app):
    app.add_handler(MessageHandler(participant_captcha, filters.private & filters.text & ~filters.command('start')))
