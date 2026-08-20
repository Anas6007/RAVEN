def safe_excerpt(text: str | None, length: int, fallback: str = "بدون وصف") -> str:
    """
    يقتطع نصًا إلى طول معيّن بأمان، حتى لو كانت القيمة None (سحوبات قديمة
    بدون وصف، أو أي حقل نصي اختياري آخر). يضيف "..." فقط إذا تم القص فعليًا.
    """

    if not text:
        return fallback

    text = text.strip()

    if not text:
        return fallback

    if len(text) <= length:
        return text

    return f"{text[:length]}..."
