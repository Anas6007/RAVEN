from dataclasses import dataclass


@dataclass
class ParticipantSession:

    user_id: int
    giveaway_id: int

    chat_id: int | None = None
    message_id: int | None = None

    action: str = "join"
    participant_id: int | None = None

    question: str | None = None
    captcha_answer: int | None = None
    captcha_passed: bool = False
    joined: bool = False
