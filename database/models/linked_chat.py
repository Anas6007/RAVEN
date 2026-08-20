from datetime import datetime

from sqlalchemy import BigInteger
from sqlalchemy import DateTime
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from database.base import Base


class LinkedChat(Base):
    """
    قناة أو مجموعة سبق لمالك ما أن ربطها ببوت السحوبات.
    تُستخدم لتعبئة زر "قنواتي" بدون الحاجة لإعادة الربط في كل مرة.
    """

    __tablename__ = "linked_chats"

    __table_args__ = (
        Index(
            "uq_linked_chats_owner_chat",
            "owner_id", "chat_id",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    owner_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )

    chat_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    chat_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    chat_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    chat_link: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
