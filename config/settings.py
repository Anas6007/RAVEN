import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent

# تحميل متغيرات البيئة من ملف .env في جذر المشروع
load_dotenv(ROOT_DIR / ".env")


class Settings:
    # بيانات البوت (تُقرأ من .env ولا يجب أبدًا كتابتها هنا مباشرة)
    API_ID = int(os.getenv("API_ID", "0"))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")

    # اسم مستخدم البوت
    BOT_USERNAME = os.getenv("BOT_USERNAME", "")

    # الاسم الظاهر للبوت في رسالة السحب
    BOT_DISPLAY_NAME = os.getenv("BOT_DISPLAY_NAME", "") or BOT_USERNAME

    # قناة "جميع السحوبات"
    ALL_GIVEAWAYS_CHANNEL_ID = int(os.getenv("ALL_GIVEAWAYS_CHANNEL_ID", "0") or "0")
    ALL_GIVEAWAYS_CHANNEL_NAME = os.getenv("ALL_GIVEAWAYS_CHANNEL_NAME", "")
    ALL_GIVEAWAYS_CHANNEL_LINK = os.getenv("ALL_GIVEAWAYS_CHANNEL_LINK", "")
    ALL_GIVEAWAYS_CHANNEL_ENABLED = False

    # معرف المالك
    OWNER_ID = int(os.getenv("OWNER_ID", "0"))

    # معرفات المطورين
    _dev_ids_raw = os.getenv("DEV_IDS", "")
    DEV_IDS = set()
    for _part in _dev_ids_raw.split(","):
        _part = _part.strip()
        if _part.isdigit():
            DEV_IDS.add(int(_part))

    # عدد الـ Workers
    WORKERS = int(os.getenv("WORKERS", "4"))

    # مسار المشروع
    ROOT_DIR = ROOT_DIR

    # قاعدة البيانات
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{ROOT_DIR}/database/database.db",
    )

    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))

    # اتصال Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # فاصل فحص المجدول
    SCHEDULER_INTERVAL_SECONDS = int(
        os.getenv("SCHEDULER_INTERVAL_SECONDS", "30")
    )

    # وضع التطوير
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"


settings = Settings()

# المالك يعتبر مطورًا دائمًا
if settings.OWNER_ID:
    settings.DEV_IDS.add(settings.OWNER_ID)

if not settings.API_ID or not settings.API_HASH or not settings.BOT_TOKEN:
    raise RuntimeError(
        "❌ إعدادات البوت ناقصة. تأكد من إنشاء ملف .env في جذر المشروع "
        "يحتوي على API_ID و API_HASH و BOT_TOKEN و BOT_USERNAME "
        "(انظر .env.example)."
    )
