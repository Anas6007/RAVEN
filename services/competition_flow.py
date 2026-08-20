from sqlalchemy.exc import IntegrityError

from bot.keyboards.giveaway import giveaway_keyboard
from repositories.giveaway_repository import GiveawayRepository
from config import logger
from repositories.participant_repository import ParticipantRepository
from repositories.vote_repository import VoteRepository
from services.participant_service import ParticipantService
from services.engines.draw_engine import DrawEngine
from utils.safe_edit import safe_client_edit_reply_markup
from utils.broadcast import notify_users


async def post_contestant_entry(client, giveaway, participant, db):
    participants = ParticipantRepository(db)
    msg = await client.send_message(
        chat_id=giveaway.chat_id,
        text=(
            f"🏆 **متسابق جديد**\n\n"
            f"👤 المتسابق: [{participant.first_name}](tg://user?id={participant.user_id})\n"
            f"🗳️ الأصوات: {participant.votes_count}\n\n"
            f"✍️ اضغط الزر أدناه للتصويت لهذا المتسابق."
        ),
        reply_markup=giveaway_keyboard(
            giveaway.id,
            giveaway.participants_count,
            giveaway.is_active,
            giveaway.drawn_once,
            management=False,
            flow_kind='competition',
            participant_id=participant.id,
            votes_count=participant.votes_count,
        ),
    )

    participant.post_message_id = msg.id
    await participants.save()
    await participants.refresh(participant)
    return msg


async def finalize_direct_contestant_join(client, db, giveaway, user):
    """
    يُستخدم لإتمام انضمام متسابق مباشرة (مسابقة بدون موافقة مسبقة) بعد
    أن يكون قد اجتاز الكابتشا (إن كانت مفعّلة) والتحقق من الاشتراك
    الإجباري بالفعل. هذا يضمن تطبيق نفس معايير الحماية من الحسابات
    الآلية المطبّقة على السحوبات العادية على المسابقات أيضًا.
    """
    participants_repo = ParticipantRepository(db)
    giveaways_repo = GiveawayRepository(db)

    existing = await participants_repo.get_by_user(giveaway.id, user.id)
    if existing:
        return giveaway, existing, False

    participant_service = ParticipantService(participants_repo)
    participant = await participant_service.join(giveaway.id, user)

    await post_contestant_entry(client, giveaway, participant, db)

    giveaway = await giveaways_repo.update(
        giveaway,
        participants_count=(giveaway.participants_count + 1),
    )

    return giveaway, participant, True


async def approve_contestant_request(client, db, giveaway, request_obj):
    participants = ParticipantRepository(db)

    if await participants.get_by_user(giveaway.id, request_obj.user_id):
        return False, 'already_approved'

    participant_service = ParticipantService(participants)
    user = type('UserObj', (), {'id': request_obj.user_id, 'first_name': 'متسابق', 'username': None})()

    # لا نملك اسم المستخدم هنا بشكل موثوق؛ نجلبه من تيليجرام مباشرة.
    try:
        tg_user = await client.get_users(request_obj.user_id)
        user = tg_user
    except Exception:
        pass

    participant = await participant_service.join(giveaway.id, user)
    await post_contestant_entry(client, giveaway, participant, db)
    return True, participant


async def register_competition_vote(client, db, giveaway, participant, voter_user):
    votes = VoteRepository(db)

    existing = await votes.get_by_voter(giveaway.id, voter_user.id)
    if existing:
        return False, 'already_voted'

    try:
        await votes.create(
            giveaway_id=giveaway.id,
            participant_id=participant.id,
            voter_user_id=voter_user.id,
        )
    except IntegrityError:
        await votes.session.rollback()
        return False, 'already_voted'

    participants_repo = ParticipantRepository(db)
    participant = await participants_repo.update_votes_count(participant, participant.votes_count + 1)

    await safe_client_edit_reply_markup(
        client,
        giveaway.chat_id,
        participant.post_message_id,
        giveaway_keyboard(
            giveaway.id,
            giveaway.participants_count,
            giveaway.is_active,
            giveaway.drawn_once,
            management=False,
            flow_kind='competition',
            participant_id=participant.id,
            votes_count=participant.votes_count,
        ),
    )

    logger.info('Vote registered for giveaway=%s participant=%s voter=%s', giveaway.id, participant.id, voter_user.id)
    return True, participant


async def close_competition_participant_buttons(client, giveaway, participants):
    for participant in participants:
        if not participant.post_message_id:
            continue
        try:
            await safe_client_edit_reply_markup(
                client,
                giveaway.chat_id,
                participant.post_message_id,
                giveaway_keyboard(
                    giveaway.id,
                    giveaway.participants_count,
                    False,
                    giveaway.drawn_once,
                    management=False,
                    flow_kind='competition',
                    participant_id=participant.id,
                    votes_count=participant.votes_count,
                ),
            )
        except Exception:
            pass


async def announce_competition_result(client, giveaway, winners):
    winner_lines = []
    for i, winner in enumerate(winners, 1):
        name = f"@{winner.username}" if winner.username else winner.first_name
        winner_lines.append(f"{i}. {name} — `{winner.user_id}`")

    text = (
        "🏆 انتهت المسابقة\n\n"
        + "\n".join(winner_lines)
        + "\n\n🎉 مبروك للفائزين!"
    )

    if getattr(giveaway, "announce_winner", True):
        try:
            await client.send_message(chat_id=giveaway.chat_id, text=text)
        except Exception:
            pass

    if getattr(giveaway, "notify_winner", True):
        try:
            await client.send_message(
                chat_id=giveaway.owner_id,
                text=text,
            )
        except Exception:
            pass




async def complete_competition_vote(client, db, giveaway, participant, voter_user):
    votes = VoteRepository(db)
    existing = await votes.get_by_voter(giveaway.id, voter_user.id)
    if existing:
        return False, 'already_voted'

    try:
        await votes.create(
            giveaway_id=giveaway.id,
            participant_id=participant.id,
            voter_user_id=voter_user.id,
        )
    except IntegrityError:
        await votes.session.rollback()
        return False, 'already_voted'

    participants_repo = ParticipantRepository(db)
    participant = await participants_repo.update_votes_count(participant, participant.votes_count + 1)

    await safe_client_edit_reply_markup(
        client,
        giveaway.chat_id,
        participant.post_message_id,
        giveaway_keyboard(
            giveaway.id,
            giveaway.participants_count,
            giveaway.is_active,
            giveaway.drawn_once,
            management=False,
            flow_kind='competition',
            participant_id=participant.id,
            votes_count=participant.votes_count,
        ),
    )

    # إذا كانت المسابقة مضبوطة على الإنهاء عند عدد أصوات معيّن، نفّذ الإنهاء
    # مباشرة بعد احتساب الصوت الجديد.
    if (
        getattr(giveaway, 'flow_kind', 'giveaway') == 'competition'
        and giveaway.is_active
        and giveaway.mode == 'auto'
        and giveaway.auto_trigger == 'count'
        and giveaway.auto_threshold
    ):
        total_votes = await votes.count_for_giveaway(giveaway.id)
        if total_votes >= giveaway.auto_threshold:
            engine = DrawEngine(db, client)
            success, result = await engine.draw(giveaway.id)
            if success:
                giveaway_obj, winners, _has_more = result
                await announce_competition_result(client, giveaway_obj, winners)
                try:
                    await notify_users(
                        client,
                        [winner.user_id for winner in winners],
                        lambda _uid: {
                            "text": (
                                "🎉 مبروك! لقد فزت في المسابقة.\n\n"
                                f"📢 القناة/المجموعة: {giveaway_obj.chat_title}\n\n"
                                "سيتم التواصل معك من المنشئ بخصوص التفاصيل."
                            )
                        },
                        context=f"auto-draw-count competition#{giveaway_obj.id}",
                    )
                except Exception:
                    pass

    return True, participant
