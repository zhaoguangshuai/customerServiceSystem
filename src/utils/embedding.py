import hashlib
import json

from openai import AsyncOpenAI

from src.config import get_settings

_client: AsyncOpenAI = None

EMBEDDING_CACHE_TTL = 3600  # 1 hour


def get_embedding_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )
    return _client


def _text_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


async def _get_cached_embedding(text: str) -> list[float] | None:
    try:
        from src.db.redis import get_redis

        r = get_redis()
        if r is None:
            return None
        key = f"emb:{_text_hash(text)}"
        data = await r.get(key)
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None


async def _cache_embedding(text: str, embedding: list[float]):
    try:
        from src.db.redis import get_redis

        r = get_redis()
        if r is None:
            return
        key = f"emb:{_text_hash(text)}"
        await r.setex(key, EMBEDDING_CACHE_TTL, json.dumps(embedding))
    except Exception:
        pass


async def get_embedding(text: str) -> list[float]:
    cached = await _get_cached_embedding(text)
    if cached is not None:
        return cached

    settings = get_settings()
    client = get_embedding_client()
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=text,
    )
    embedding = response.data[0].embedding
    await _cache_embedding(text, embedding)
    return embedding


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    # Check cache for each text, collect uncached indices
    results: list[list[float] | None] = [None] * len(texts)
    uncached_indices: list[int] = []
    uncached_texts: list[str] = []

    for i, text in enumerate(texts):
        cached = await _get_cached_embedding(text)
        if cached is not None:
            results[i] = cached
        else:
            uncached_indices.append(i)
            uncached_texts.append(text)

    # Batch compute uncached embeddings
    if uncached_texts:
        settings = get_settings()
        client = get_embedding_client()
        response = await client.embeddings.create(
            model=settings.embedding_model,
            input=uncached_texts,
        )
        for i, (idx, item) in enumerate(zip(uncached_indices, response.data)):
            results[idx] = item.embedding
            await _cache_embedding(uncached_texts[i], item.embedding)

    return results  # type: ignore
