"""
طبقة cache تستخدم Redis فعليًا عند توفره (REDIS_URL في .env)، مع سقوط آمن
تلقائيًا لكاش في الذاكرة إن تعذّر الاتصال بأي سبب.
"""

import time

from config import settings, logger

try:
    import redis.asyncio as redis_asyncio
except ImportError:
    redis_asyncio = None


class MemoryCache:
    def __init__(self):
        self._store = {}

    async def set(self, key: str, value, ttl: int = 300):
        expires_at = time.monotonic() + ttl
        self._store[key] = (value, expires_at)

    async def get(self, key: str):
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    async def delete(self, key: str):
        self._store.pop(key, None)

    async def exists(self, key: str) -> bool:
        return await self.get(key) is not None

    async def incr(self, key: str, ttl: int = 60) -> int:
        value = await self.get(key)
        value = (value or 0) + 1
        await self.set(key, value, ttl=ttl)
        return value


class RedisCache:
    def __init__(self, url: str):
        self._client = redis_asyncio.from_url(url, decode_responses=True)

    async def set(self, key: str, value, ttl: int = 300):
        await self._client.set(key, value, ex=ttl)

    async def get(self, key: str):
        return await self._client.get(key)

    async def delete(self, key: str):
        await self._client.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self._client.exists(key))

    async def incr(self, key: str, ttl: int = 60) -> int:
        value = await self._client.incr(key)
        if value == 1:
            await self._client.expire(key, ttl)
        return value


class FallbackCache:
    def __init__(self, redis_url: str):
        self._memory = MemoryCache()
        self._redis = None
        self._use_memory = False
        self._failure_logged = False

        if redis_asyncio is not None:
            try:
                self._redis = RedisCache(redis_url)
            except Exception:
                self._use_memory = True
        else:
            self._use_memory = True

    async def _run(self, method: str, *args, **kwargs):
        if self._use_memory or self._redis is None:
            return await getattr(self._memory, method)(*args, **kwargs)

        try:
            return await getattr(self._redis, method)(*args, **kwargs)
        except Exception as e:
            self._use_memory = True
            if not self._failure_logged:
                logger.debug(
                    "[CACHE] Redis unavailable; falling back to in-memory cache: {}",
                    repr(e),
                )
                self._failure_logged = True
            return await getattr(self._memory, method)(*args, **kwargs)

    async def set(self, key: str, value, ttl: int = 300):
        return await self._run("set", key, value, ttl=ttl)

    async def get(self, key: str):
        return await self._run("get", key)

    async def delete(self, key: str):
        return await self._run("delete", key)

    async def exists(self, key: str) -> bool:
        return await self._run("exists", key)

    async def incr(self, key: str, ttl: int = 60) -> int:
        return await self._run("incr", key, ttl=ttl)


cache = FallbackCache(settings.REDIS_URL)
