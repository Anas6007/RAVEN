from config import settings
from services.flow_labels import flow_title, flow_noun

SEPARATOR = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


def _required_channels_block(required_channels) -> str:
    lines = []
    for channel in required_channels:
        title = channel.get("title") or "قناة"
        link = channel.get("link")
        if link:
            lines.append(f"• [{title}]({link})")
        else:
            lines.append(f"• {title}")
    return "\n".join(lines)


def _links_line(session) -> str:
    parts = []

    if settings.BOT_USERNAME:
        bot_name = settings.BOT_DISPLAY_NAME or "Raven"
        parts.append(f"🤖 [{bot_name}](https://t.me/{settings.BOT_USERNAME})")

    if settings.ALL_GIVEAWAYS_CHANNEL_LINK:
        channel_label = "جميع المسابقات" if getattr(session, "flow_kind", "giveaway") == "competition" else "جميع السحوبات"
        parts.append(f"📢 [{channel_label}]({settings.ALL_GIVEAWAYS_CHANNEL_LINK})")

    return "   |   ".join(parts)


def _auto_line(session) -> str:
    if session.mode != "auto":
        return ""

    noun = flow_noun(session)
    if session.auto_trigger == "count" and session.auto_threshold:
        target_word = "الأصوات" if getattr(session, "flow_kind", "giveaway") == "competition" else "المشاركين"
        return f"⏰ يُعلن {noun} تلقائيًا عند وصول {target_word} إلى {session.auto_threshold}"

    if session.auto_trigger == "time" and getattr(session, "auto_hours", None):
        return f"⏰ يُعلن {noun} تلقائيًا بعد {session.auto_hours} ساعات من النشر"

    if session.auto_trigger == "time" and getattr(session, "end_date", None):
        return f"⏰ يُعلن {noun} تلقائيًا عند {session.end_date:%Y-%m-%d %H:%M}"

    return ""


def build_giveaway_text(session, *, title: str | None = None) -> str:
    is_competition = getattr(session, "flow_kind", "giveaway") == "competition"

    if title is None:
        title = flow_title(session)

    if is_competition:
        seats = getattr(session, "contestant_slots", None) or "غير محدد"
        header = f"{title}          🏆 عدد المقاعد: {seats}"
        blocks = [header]

        description = (getattr(session, "description", None) or "").strip()
        if description:
            blocks.append(f"📝 الوصف: {description}")

        links_line = _links_line(session)
        if links_line:
            blocks.append(links_line)

        return f"\n\n{SEPARATOR}\n\n".join(blocks)

    header = f"{title}          🏆 **عدد الفائزين:** {session.winners_count}"
    blocks = [f"<blockquote>{header}</blockquote>"]

    description = (session.description or "").strip()
    if description:
        blocks.append(f"📝 **الوصف:**\n\n{description}")

    if session.required_channels:
        blocks.append(
            f"📢 **الاشتراك الإجباري:**\n\n{_required_channels_block(session.required_channels)}"
        )
    else:
        blocks.append("🔓 **الاشتراك الإجباري:** غير مطلوب")

    links_line = _links_line(session)
    if links_line:
        blocks.append(f"<blockquote>{links_line}</blockquote>")

    auto_line = _auto_line(session)
    if auto_line:
        blocks.append(f"<blockquote>{auto_line}</blockquote>")

    return f"\n\n{SEPARATOR}\n\n".join(blocks)
