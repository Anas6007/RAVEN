from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class Vote(Base):
    __tablename__ = "votes"

    __table_args__ = (
        UniqueConstraint("giveaway_id", "voter_user_id", name="uq_votes_giveaway_voter"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    giveaway_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    participant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    voter_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
