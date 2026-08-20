from services.participant_session import ParticipantSession


class ParticipantSessionManager:

    def __init__(self):
        self.sessions = {}

    def create(
        self,
        user_id: int,
        giveaway_id: int,
        chat_id: int | None = None,
        message_id: int | None = None,
        action: str = "join",
        participant_id: int | None = None,
    ):
        session = ParticipantSession(
            user_id=user_id,
            giveaway_id=giveaway_id,
            action=action,
            participant_id=participant_id,
        )
        session.chat_id = chat_id
        session.message_id = message_id
        self.sessions[user_id] = session
        return session

    def get(self, user_id: int):
        return self.sessions.get(user_id)

    def delete(self, user_id: int):
        self.sessions.pop(user_id, None)

    def exists(self, user_id: int):
        return user_id in self.sessions

    def clear(self):
        self.sessions.clear()


participant_session_manager = ParticipantSessionManager()
