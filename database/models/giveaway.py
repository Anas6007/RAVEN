from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class Giveaway(Base):
    __tablename__ = "giveaways"

    __table_args__ = (
        Index("ix_giveaways_owner_id", "owner_id"),
        Index("ix_giveaways_chat_id", "chat_id"),
        Index(
            "ix_giveaways_active_auto_end_at",
            "is_active", "mode", "auto_trigger", "end_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chat_type: Mapped[str] = mapped_column(String(20), nullable=False)
    chat_title: Mapped[str] = mapped_column(String(255), nullable=False)
    chat_link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    flow_kind: Mapped[str] = mapped_column(String(20), default="giveaway", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    winners_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    contestant_slots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    required_channels: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    image: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    enable_captcha: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    require_comment: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    discussion_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    discussion_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # معرف مجموعة النقاش المرتبطة فعليًا بالقناة (وليس القناة نفسها).
    # يُستخدم للتأكد أن تعليق التحقق أُرسل داخل المجموعة الصحيحة فعلًا
    # وليس في أي مجموعة أخرى يتواجد فيها البوت.
    discussion_group_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    require_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_winner: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    announce_winner: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    participants_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    auto_trigger: Mapped[str | None] = mapped_column(String(10), nullable=True)
    auto_threshold: Mapped[int | None] = mapped_column(Integer, nullable=True)
    drawn_once: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
