import json
from typing import Optional

import redis.asyncio as redis

from src.config import Settings

_redis_pool: Optional[redis.Redis] = None


async def init_redis(settings: Settings) -> redis.Redis:
    global _redis_pool
    _redis_pool = redis.from_url(
        settings.redis_url,
        decode_responses=True,
        max_connections=20,
    )
    return _redis_pool


async def close_redis():
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()


def get_redis() -> redis.Redis:
    return _redis_pool


async def cache_chat_context(session_id: str, messages: list[dict], ttl: int = 3600):
    r = get_redis()
    key = f"chat:context:{session_id}"
    await r.setex(key, ttl, json.dumps(messages, ensure_ascii=False))


async def get_chat_context(session_id: str) -> list[dict]:
    r = get_redis()
    key = f"chat:context:{session_id}"
    data = await r.get(key)
    return json.loads(data) if data else []


async def set_manual_lock(tenant_id: str, user_id: str, ttl: int = 1800):
    r = get_redis()
    key = f"manual_lock:{tenant_id}:{user_id}"
    await r.setex(key, ttl, "1")


async def is_manual_locked(tenant_id: str, user_id: str) -> bool:
    r = get_redis()
    key = f"manual_lock:{tenant_id}:{user_id}"
    return await r.exists(key) > 0


async def cache_query_result(query_hash: str, result: dict, ttl: int = 300):
    r = get_redis()
    key = f"query_cache:{query_hash}"
    await r.setex(key, ttl, json.dumps(result, ensure_ascii=False))


async def get_cached_query(query_hash: str) -> Optional[dict]:
    r = get_redis()
    key = f"query_cache:{query_hash}"
    data = await r.get(key)
    return json.loads(data) if data else None


async def check_redis_health() -> dict:
    """Check Redis connectivity. Returns {"status": "ok"/"error", "detail": ...}."""
    r = get_redis()
    if r is None:
        return {"status": "error", "detail": "Redis not initialized"}
    try:
        await r.ping()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
