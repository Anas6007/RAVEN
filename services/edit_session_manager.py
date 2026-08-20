from dataclasses import dataclass


@dataclass
class EditGiveawaySession:
    user_id: int
    giveaway_id: int
    field: str | None = None  # "description" | "winners"


class EditSessionManager:

    def __init__(self):
        self.sessions = {}

    def create(self, user_id: int, giveaway_id: int):
        session = EditGiveawaySession(user_id=user_id, giveaway_id=giveaway_id)
        self.sessions[user_id] = session
        return session

    def get(self, user_id: int):
        return self.sessions.get(user_id)

    def delete(self, user_id: int):
        self.sessions.pop(user_id, None)


edit_session_manager = EditSessionManager()
