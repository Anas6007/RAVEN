from sqlalchemy import text

from database.base import Base
from database.session import engine

from database.models.giveaway import Giveaway
from database.models.participant import Participant
from database.models.linked_chat import LinkedChat
from database.models.bot_user import BotUser
from database.models.banned_chat import BannedChat
from database.models.comment_verification import CommentVerification
from database.models.vote import Vote
from database.models.competition_request import CompetitionRequest


async def _migrate_add_missing_columns(conn):
    """
    ترقية خفيفة لقواعد بيانات SQLite القديمة.
    """

    statements = [
        "ALTER TABLE giveaways ADD COLUMN chat_link VARCHAR(255)",
        "ALTER TABLE giveaways ADD COLUMN media_type VARCHAR(20)",
        "ALTER TABLE giveaways ADD COLUMN require_comment BOOLEAN DEFAULT 0",
        "ALTER TABLE giveaways ADD COLUMN discussion_chat_id BIGINT",
        "ALTER TABLE giveaways ADD COLUMN discussion_message_id BIGINT",
        "ALTER TABLE giveaways ADD COLUMN discussion_group_id BIGINT",
        "ALTER TABLE giveaways ADD COLUMN contestant_slots INTEGER",
        "ALTER TABLE giveaways ADD COLUMN require_approval BOOLEAN DEFAULT 1",
        "ALTER TABLE giveaways ADD COLUMN notify_winner BOOLEAN DEFAULT 1",
        "ALTER TABLE giveaways ADD COLUMN announce_winner BOOLEAN DEFAULT 1",
        "ALTER TABLE participants ADD COLUMN passed_comment BOOLEAN DEFAULT 0",
        "ALTER TABLE participants ADD COLUMN votes_count INTEGER DEFAULT 0",
        "ALTER TABLE participants ADD COLUMN post_message_id BIGINT",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_participant_giveaway_user ON participants (giveaway_id, user_id)",
        "CREATE INDEX IF NOT EXISTS ix_participants_giveaway_id ON participants (giveaway_id)",
        "CREATE INDEX IF NOT EXISTS ix_participants_giveaway_winner ON participants (giveaway_id, is_winner)",
        "CREATE INDEX IF NOT EXISTS ix_giveaways_owner_id ON giveaways (owner_id)",
        "CREATE INDEX IF NOT EXISTS ix_giveaways_chat_id ON giveaways (chat_id)",
        "CREATE INDEX IF NOT EXISTS ix_giveaways_active_auto_end_at ON giveaways (is_active, mode, auto_trigger, end_at)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_linked_chats_owner_chat ON linked_chats (owner_id, chat_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_votes_giveaway_voter ON votes (giveaway_id, voter_user_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_competition_requests_giveaway_user ON competition_requests (giveaway_id, user_id)",
    ]

    for statement in statements:
        try:
            await conn.execute(text(statement))
        except Exception:
            pass


async def _enable_performance_pragmas(conn):
    await conn.execute(text("PRAGMA journal_mode=WAL"))
    await conn.execute(text("PRAGMA synchronous=NORMAL"))


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_add_missing_columns(conn)

        if engine.url.get_backend_name() == "sqlite":
            try:
                await _enable_performance_pragmas(conn)
            except Exception:
                pass
