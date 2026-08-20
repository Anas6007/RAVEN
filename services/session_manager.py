from services.create_giveaway_session import CreateGiveawaySession


class SessionManager:

    def __init__(self):
        self.sessions = {}

    def create(self, user_id: int):
        session = CreateGiveawaySession(user_id)
        self.sessions[user_id] = session
        return session

    def get(self, user_id: int):
        return self.sessions.get(user_id)

    def set(self, user_id: int, key: str, value):
        session = self.get(user_id)

        if session is None:
            session = self.create(user_id)

        setattr(session, key, value)

    def delete(self, user_id: int):
        self.sessions.pop(user_id, None)


session_manager = SessionManager()