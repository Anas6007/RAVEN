from services.session_manager import session_manager


class GiveawayEngine:

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.session = session_manager.get(user_id)
        if self.session is None:
            self.session = session_manager.create(user_id)

    def set_mode(self, mode: str):
        self.session.mode = mode

    def set_flow_kind(self, flow_kind: str):
        self.session.flow_kind = flow_kind

    def set_description(self, description: str | None):
        self.session.description = description.strip() if description else None

    def set_winners(self, winners: int):
        self.session.winners_count = winners

    def set_contestant_slots(self, slots: int):
        self.session.contestant_slots = slots

    def add_required_channel(
        self,
        chat_id: int,
        title: str,
        link: str | None = None,
    ):
        for channel in self.session.required_channels:
            if channel["id"] == chat_id:
                return False

        self.session.required_channels.append(
            {
                "id": chat_id,
                "title": title,
                "link": link,
            }
        )
        return True

    def remove_required_channel(self, chat_id: int):
        self.session.required_channels = [
            channel
            for channel in self.session.required_channels
            if channel["id"] != chat_id
        ]

    def clear_required_channels(self):
        self.session.required_channels.clear()

    def enable_captcha(self):
        self.session.enable_captcha = True

    def disable_captcha(self):
        self.session.enable_captcha = False

    def set_media(self, file_id: str, media_type: str):
        self.session.image = file_id
        self.session.media_type = media_type

    def remove_image(self):
        self.session.image = None
        self.session.media_type = None

    def set_discussion(self, chat_id: int | None, message_id: int | None, group_id: int | None = None):
        self.session.discussion_chat_id = chat_id
        self.session.discussion_message_id = message_id
        self.session.discussion_group_id = group_id

    def enable_comment_requirement(self):
        self.session.require_comment = True

    def disable_comment_requirement(self):
        self.session.require_comment = False
        self.session.discussion_chat_id = None
        self.session.discussion_message_id = None
        self.session.discussion_group_id = None

    def toggle_participant_approval(self):
        self.session.require_approval = not getattr(self.session, "require_approval", True)

    def toggle_notify_winner(self):
        self.session.notify_winner = not getattr(self.session, "notify_winner", True)

    def toggle_announce_winner(self):
        self.session.announce_winner = not getattr(self.session, "announce_winner", True)

    def set_end_date(self, end_date):
        self.session.end_date = end_date

    def set_auto_trigger(self, trigger: str):
        self.session.auto_trigger = trigger

    def set_auto_threshold(self, threshold: int):
        self.session.auto_threshold = threshold

    def set_auto_hours(self, hours: int):
        self.session.auto_hours = hours

    def finish(self):
        session_manager.delete(self.user_id)

    def preview(self):
        return self.session
