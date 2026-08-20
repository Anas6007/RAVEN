import re

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import logger, settings


def _mask_database_url(url: str) -> str:
    if "@" not in url:
        return url
    return re.sub(r"//([^/@:]+)(?::[^/@]*)?@", "//***:***@", url)


_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs = {"echo": settings.DEBUG}

if not _is_sqlite:
    # ضبط pool مفيد فقط مع قاعدة بيانات حقيقية بخادم منفصل (Postgres/MySQL).
    # SQLite ملف محلي بدون pool فعلي، وتمرير هذه الخيارات له يسبب خطأ.
    # القيم الافتراضية هنا مناسبة لحمل متوسط-كبير؛ تُضبط فعليًا عبر .env
    # حسب موارد الخادم وعدد نسخ البوت العاملة.
    _engine_kwargs.update(
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,
    )

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

if settings.DEBUG:
    logger.debug("DATABASE_URL = {}", _mask_database_url(settings.DATABASE_URL))
    logger.debug("ENGINE_URL = {}", _mask_database_url(str(engine.url)))


SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
