from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class Participant(Base):
    __tablename__ = "participants"

    __table_args__ = (
        UniqueConstraint("giveaway_id", "user_id", name="uq_participant_giveaway_user"),
        Index("ix_participants_giveaway_id", "giveaway_id"),
        Index("ix_participants_giveaway_winner", "giveaway_id", "is_winner"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    giveaway_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    passed_captcha: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_winner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    votes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed_comment: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    remind_on_win: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    post_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
