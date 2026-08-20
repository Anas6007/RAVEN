from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CreateGiveawaySession:

    user_id: int

    step: str | None = None

    chat_type: str | None = None
    chat_id: int | None = None
    chat_title: str | None = None
    chat_link: str | None = None

    flow_kind: str = "giveaway"

    mode: str | None = None

    description: str | None = None
    winners_count: int | None = None
    contestant_slots: int | None = None

    required_channels: list[dict] = field(default_factory=list)

    enable_captcha: bool = False
    image: str | None = None
    media_type: str | None = None

    require_comment: bool = False
    discussion_chat_id: int | None = None
    discussion_message_id: int | None = None
    discussion_group_id: int | None = None

    require_approval: bool = False
    notify_winner: bool = False
    announce_winner: bool = False

    end_date: datetime | None = None
    auto_trigger: str | None = None
    auto_threshold: int | None = None
    auto_hours: int | None = None

    preview_message_id: int | None = None
    giveaway_chat_id: int | None = None
    giveaway_message_id: int | None = None
