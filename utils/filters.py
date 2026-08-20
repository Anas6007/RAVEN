from pyrogram import filters

from services.session_manager import session_manager
from services.dev_session import dev_session_manager
from config.settings import settings


def check_state(states):

    if not isinstance(states, (list, tuple, set)):
        states = (states,)

    async def func(_, __, message):

        user = getattr(message, "from_user", None)

        if user is None:
            return False

        session = session_manager.get(user.id)

        if session is None:
            return False

        return session.step in states

    return filters.create(func)


async def _is_dev(_, __, update):

    user = getattr(update, "from_user", None)

    if user is None:
        return False

    return user.id in settings.DEV_IDS


is_dev_filter = filters.create(_is_dev)


def check_dev_state(states):

    if not isinstance(states, (list, tuple, set)):
        states = (states,)

    async def func(_, __, message):

        user = getattr(message, "from_user", None)

        if user is None:
            return False

        if user.id not in settings.DEV_IDS:
            return False

        session = dev_session_manager.get(user.id)

        if session is None:
            return False

        return session.step in states

    return filters.create(func)
