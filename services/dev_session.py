from dataclasses import dataclass


@dataclass
class DevSession:

    user_id: int

    # "waiting_broadcast" | "waiting_ban" | "waiting_unban" | None
    step: str | None = None


class DevSessionManager:

    def __init__(self):
        self.sessions: dict[int, DevSession] = {}

    def create(self, user_id: int) -> DevSession:
        session = DevSession(user_id=user_id)
        self.sessions[user_id] = session
        return session

    def get(self, user_id: int) -> DevSession | None:
        return self.sessions.get(user_id)

    def get_or_create(self, user_id: int) -> DevSession:
        session = self.get(user_id)
        if session is None:
            session = self.create(user_id)
        return session

    def delete(self, user_id: int):
        self.sessions.pop(user_id, None)


dev_session_manager = DevSessionManager()
