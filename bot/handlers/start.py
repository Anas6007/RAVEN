from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler

from database.session import SessionLocal
from config import logger

from repositories.giveaway_repository import GiveawayRepository
from repositories.participant_repository import ParticipantRepository
from repositories.user_repository import UserRepository
from repositories.competition_request_repository import CompetitionRequestRepository
from repositories.vote_repository import VoteRepository

from services.participant_session_manager import participant_session_manager

from services.engines.join_engine import JoinEngine
from services.engines.captcha_engine import CaptchaEngine
from services.engines.security_engine import SecurityEngine
from services.chat_service import ChatService
from services.competition_flow import complete_competition_vote
from services.comment_service import has_verified_comment, build_comment_instruction

from bot.keyboards.main_menu import main_menu
from bot.keyboards.required_channels import required_channels_keyboard, check_only_keyboard
from bot.keyboards.giveaway import giveaway_keyboard
from bot.keyboards.remind import remind_keyboard
from bot.keyboards.competition_requests import competition_request_keyboard
from services.flow_labels import flow_noun

from utils.safe_edit import safe_client_edit_reply_markup

from config.settings import settings


async def start_handler(client, message):

    try:
        async with SessionLocal() as db:
            users = UserRepository(db)
            await users.remember(
                telegram_id=message.from_user.id,
                first_name=message.from_user.first_name,
                username=message.from_user.username,
            )
    except Exception:
        logger.exception('USER TRACK ERROR')

    if len(message.command) > 1:
        payload = message.command[1]

        if payload.startswith('join_'):
            try:
                giveaway_id = int(payload.replace('join_', ''))
            except ValueError:
                await message.reply_text('❌ رابط السحب غير صحيح.')
                return

            async with SessionLocal() as db:
                giveaways = GiveawayRepository(db)
                giveaway = await giveaways.get(giveaway_id)
                if giveaway is None:
                    await message.reply_text('❌ السحب غير موجود.')
                    return

                noun = flow_noun(giveaway)
                if not giveaway.is_active:
                    await message.reply_text(f'❌ انتهى هذا {noun}.')
                    return

                if getattr(giveaway, 'flow_kind', 'giveaway') == 'competition':
                    participants_repo = ParticipantRepository(db)
                    existing_participant = await participants_repo.get_by_user(giveaway.id, message.from_user.id)
                    if existing_participant:
                        await message.reply_text('✅ أنت متسابق بالفعل في هذه المسابقة.')
                        return

                    if giveaway.participants_count >= (getattr(giveaway, 'contestant_slots', None) or 10**9):
                        await message.reply_text('❌ انتهت المقاعد في هذه المسابقة.')
                        return

                    if not getattr(giveaway, 'require_approval', False):
                        # قبل تسجيل المتسابق مباشرة، نطبّق نفس معايير الحماية
                        # المطبّقة على السحوبات العادية: الكابتشا (إن كانت
                        # مفعّلة) ثم التحقق من الاشتراك الإجباري. بدون هذا،
                        # كان بالإمكان تسجيل حسابات آلية كمتسابقين مباشرة
                        # دون أي تحقق.
                        if giveaway.enable_captcha:
                            question, answer = CaptchaEngine.generate()
                            session = participant_session_manager.create(
                                user_id=message.from_user.id,
                                giveaway_id=giveaway.id,
                                chat_id=giveaway.chat_id,
                                message_id=giveaway.message_id,
                                action='join_competition',
                            )
                            session.question = question
                            session.captcha_answer = answer
                            await message.reply_text(f"""🛡 التحقق الأمني

قبل التسجيل كمتسابق نحتاج للتأكد أنك لست روبوتًا.

{question} = ؟

✍️ أرسل الإجابة بالأرقام فقط.
""")
                            return

                        security = SecurityEngine(client)
                        required_list = SecurityEngine.build_full_required_list(giveaway)
                        ok, channels = await security.check_required_channels(message.from_user.id, required_list)
                        if not ok:
                            participant_session_manager.create(
                                user_id=message.from_user.id,
                                giveaway_id=giveaway.id,
                                chat_id=giveaway.chat_id,
                                message_id=giveaway.message_id,
                                action='join_competition',
                            )
                            await message.reply_text(
                                '📢 قبل التسجيل كمتسابق يجب الاشتراك في القنوات/المجموعات التالية:',
                                reply_markup=required_channels_keyboard(giveaway.id, channels),
                            )
                            return

                        from services.competition_flow import finalize_direct_contestant_join
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
                        await message.reply_text('✅ تم قبول تسجيلك في المسابقة ونشر المتسابق في القناة.')
                        return

                    requests_repo = CompetitionRequestRepository(db)
                    existing_request = await requests_repo.get_by_user(giveaway.id, message.from_user.id)
                    if existing_request and existing_request.status == 'pending':
                        await message.reply_text('✅ طلب مشاركتك في المسابقة قيد المراجعة بالفعل.')
                        return

                    request_obj = existing_request or await requests_repo.create(
                        giveaway_id=giveaway.id,
                        user_id=message.from_user.id,
                        status='pending',
                    )
                    try:
                        await client.send_message(
                            giveaway.owner_id,
                            f"🏆 طلب اشتراك جديد في المسابقة\n\n👤 المستخدم: [{message.from_user.first_name}](tg://user?id={message.from_user.id})\n🆔 المعرف: `{message.from_user.id}`",
                            reply_markup=competition_request_keyboard(request_obj.id),
                        )
                    except Exception:
                        pass
                    await message.reply_text('✅ تم ارسال طلب مشاركتك في المسابقة يرجى الانتظار حتى يتم قبول تسجيلك')
                    return

                participants_repo = ParticipantRepository(db)
                participant = await participants_repo.get_by_user(giveaway.id, message.from_user.id)
                if participant:
                    await message.reply_text(
                        f"✅ أنت {'مصوت' if getattr(giveaway, 'flow_kind', 'giveaway') == 'competition' else 'مشارك'} بالفعل في هذا {noun}."
                    )
                    return

                if giveaway.enable_captcha:
                    question, answer = CaptchaEngine.generate()
                    session = participant_session_manager.create(
                        user_id=message.from_user.id,
                        giveaway_id=giveaway.id,
                        chat_id=giveaway.chat_id,
                        message_id=giveaway.message_id,
                        action='join',
                    )
                    session.question = question
                    session.captcha_answer = answer
                    await message.reply_text(f"""🛡 التحقق الأمني

قبل المشاركة نحتاج للتأكد أنك لست روبوتًا.

{question} = ؟

✍️ أرسل الإجابة بالأرقام فقط.
""")
                    return

                security = SecurityEngine(client)
                required_list = SecurityEngine.build_full_required_list(giveaway)
                ok, channels = await security.check_required_channels(message.from_user.id, required_list)
                if not ok:
                    await message.reply_text(
                        '📢 قبل المشاركة يجب الاشتراك في القنوات/المجموعات التالية:',
                        reply_markup=required_channels_keyboard(giveaway.id, channels),
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
                        giveaway.chat_id,
                        giveaway.message_id,
                        giveaway_keyboard(giveaway.id, participants, giveaway.is_active, giveaway.drawn_once, flow_kind=getattr(giveaway, 'flow_kind', 'giveaway'), contestant_slots=getattr(giveaway, 'contestant_slots', None), management=getattr(giveaway, 'flow_kind', 'giveaway') != 'competition'),
                    )

                reply_markup = remind_keyboard(giveaway.id) if getattr(giveaway, 'flow_kind', 'giveaway') != 'competition' else None
                await message.reply_text(
                    f"🎉 تمت {('تصويتك' if getattr(giveaway, 'flow_kind', 'giveaway') == 'competition' else 'مشاركتك')} بنجاح.",
                    reply_markup=reply_markup,
                )
            return

        if payload.startswith('vote_'):
            try:
                _, giveaway_id_str, participant_id_str = payload.split('_', 2)
                giveaway_id = int(giveaway_id_str)
                participant_id = int(participant_id_str)
            except ValueError:
                await message.reply_text('❌ رابط التصويت غير صحيح.')
                return

            async with SessionLocal() as db:
                giveaways = GiveawayRepository(db)
                participant_repo = ParticipantRepository(db)
                vote_repo = VoteRepository(db)

                giveaway = await giveaways.get(giveaway_id)
                if giveaway is None:
                    await message.reply_text('❌ المسابقة غير موجودة.')
                    return

                if getattr(giveaway, 'flow_kind', 'giveaway') != 'competition':
                    await message.reply_text('❌ هذا الرابط ليس مسابقة.')
                    return

                if not giveaway.is_active:
                    await message.reply_text('❌ انتهت هذه المسابقة.')
                    return

                participant = await participant_repo.get_by_id(participant_id)
                if participant is None or participant.giveaway_id != giveaway.id:
                    await message.reply_text('❌ المتسابق غير موجود.')
                    return

                existing_vote = await vote_repo.get_by_voter(giveaway.id, message.from_user.id)
                if existing_vote:
                    await message.reply_text('❌ لقد قمت بتصويت لشخص في هذه المسابقة بالفعل.')
                    return

                session = participant_session_manager.create(
                    user_id=message.from_user.id,
                    giveaway_id=giveaway.id,
                    chat_id=giveaway.chat_id,
                    message_id=participant.post_message_id,
                    action='vote',
                    participant_id=participant.id,
                )

                if giveaway.enable_captcha:
                    question, answer = CaptchaEngine.generate()
                    session.question = question
                    session.captcha_answer = answer
                    note = 'بعدها سيُطلب منك إكمال الاشتراك ثم التعليق إن كان مطلوبًا.'
                    if not getattr(giveaway, 'require_comment', False):
                        note = 'بعدها سيُطلب منك إكمال الاشتراك إن وُجد.'
                    await message.reply_text(f"""🛡 التحقق الأمني

قبل قبول تصويتك نحتاج للتأكد أنك لست روبوتًا.

{question} = ؟

✍️ أرسل الإجابة بالأرقام فقط.

{note}
""")
                    return

                security = SecurityEngine(client)
                required_list = SecurityEngine.build_full_required_list(giveaway)
                ok, channels = await security.check_required_channels(message.from_user.id, required_list)
                if not ok:
                    prompt = '📢 قبل التصويت يجب الاشتراك في القنوات/المجموعات التالية:'
                    comment_prompt = None
                    if getattr(giveaway, 'require_comment', False):
                        comment_prompt = await build_comment_instruction(client, giveaway)
                    if comment_prompt:
                        prompt += f"\n\n{comment_prompt}"
                    await message.reply_text(
                        prompt,
                        reply_markup=required_channels_keyboard(giveaway.id, channels),
                        parse_mode=ParseMode.HTML if comment_prompt else None,
                        disable_web_page_preview=True,
                    )
                    return

                if getattr(giveaway, 'require_comment', False) and not await has_verified_comment(db, giveaway.id, message.from_user.id):
                    comment_prompt = await build_comment_instruction(client, giveaway)
                    text = comment_prompt or '💬 يجب التعليق على المنشور المطلوب أولًا ثم إعادة محاولة التصويت.'
                    await message.reply_text(
                        text,
                        reply_markup=check_only_keyboard(giveaway.id),
                        parse_mode=ParseMode.HTML if comment_prompt else None,
                        disable_web_page_preview=True,
                    )
                    return

                ok_vote, result = await complete_competition_vote(client, db, giveaway, participant, message.from_user)
                if not ok_vote:
                    await message.reply_text('❌ لقد قمت بتصويت لشخص في هذه المسابقة بالفعل.')
                    return

                participant_session_manager.delete(message.from_user.id)
                await message.reply_text('✅ تم قبول تصويتك بنجاح.')
            return

    text = f"""
🎉 مرحبًا بك في بوت السحوبات والمسابقات

أهلًا {message.from_user.first_name} 👋

أنشئ سحوبات احترافية وقم بإدارة مسابقات التصويت من مكان واحد بكل سهولة.

يمكنك إنشاء السحب أو المسابقة، متابعة المشاركين/المصوتين، اختيار الفائزين، والاطلاع على الإحصائيات من خلال الواجهة الرئيسية.

━━━━━━━━━━━━━━━━━━

✨ ابدأ باختيار الخدمة المناسبة من القائمة أدناه.
"""

    await message.reply_text(text, reply_markup=main_menu())


def register(app):
    app.add_handler(MessageHandler(start_handler, filters.private & filters.command('start')))
