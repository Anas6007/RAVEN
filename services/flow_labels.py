from __future__ import annotations

from typing import Any


def flow_kind(obj: Any) -> str:
    return getattr(obj, "flow_kind", "giveaway") or "giveaway"


def is_competition(obj: Any) -> bool:
    return flow_kind(obj) == "competition"


def flow_noun(obj: Any, giveaway: str = "السحب", competition: str = "المسابقة") -> str:
    return competition if is_competition(obj) else giveaway


def flow_gerund(obj: Any, giveaway: str = "سحب", competition: str = "مسابقة") -> str:
    return competition if is_competition(obj) else giveaway


def flow_title(obj: Any, giveaway: str = "🎁 سحب جديد", competition: str = "🏆 مسابقة جديدة") -> str:
    return competition if is_competition(obj) else giveaway


def flow_publish_button(obj: Any) -> str:
    return "✅ نشر المسابقة" if is_competition(obj) else "✅ نشر السحب"


def flow_edit_button(obj: Any) -> str:
    return "✏️ تعديل المسابقة" if is_competition(obj) else "✏️ تعديل السحب"


def flow_cancel_button(obj: Any) -> str:
    return "❌ إلغاء المسابقة" if is_competition(obj) else "❌ إلغاء السحب"


def flow_main_list_title(obj: Any) -> str:
    return "📂 **مسابقاتي**" if is_competition(obj) else "📂 **سحوباتي**"


def flow_empty_list_text(obj: Any) -> str:
    if is_competition(obj):
        return "لا توجد مسابقات حتى الآن.\\n\\nابدأ بإنشاء مسابقتك الأولى! 🏆"
    return "لا توجد سحوبات حتى الآن.\\n\\nابدأ بإنشاء سحبك الأولى! 🎁"


def flow_manage_title(obj: Any) -> str:
    return "📋 **تفاصيل المسابقة**" if is_competition(obj) else "📋 **تفاصيل السحب**"
