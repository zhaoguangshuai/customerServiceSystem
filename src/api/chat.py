import hashlib
import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from src.agent.deerflow import DeerFlowAgent
from src.db.redis import cache_query_result, get_cached_query

logger = logging.getLogger(__name__)

router = APIRouter()

QUERY_CACHE_TTL = 300  # 5 minutes


class ChatRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1, max_length=64, description="租户ID")
    channel: Literal["wechat", "web", "admin"] = Field(
        default="web",
        description="渠道：wechat/web/admin",
    )
    user_id: str = Field(..., min_length=1, max_length=100, description="用户ID")
    query: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    session_id: str = Field(..., min_length=1, max_length=100, description="会话ID")

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query不能为空白字符")
        return v.strip()


class ChatResponseData(BaseModel):
    answer: str
    need_manual: bool
    manual_reason: str
    sources: list[str]


class ChatResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    data: ChatResponseData


def _query_cache_key(tenant_id: str, session_id: str, query: str) -> str:
    h = hashlib.sha256(f"{tenant_id}:{session_id}:{query}".encode("utf-8")).hexdigest()
    return h


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest):
    # Check query result cache (skip for sessions with active manual lock)
    cache_key = _query_cache_key(body.tenant_id, body.session_id, body.query)
    cached = await get_cached_query(cache_key)
    if cached and not cached.get("need_manual"):
        return ChatResponse(
            code=200,
            msg="success",
            data=ChatResponseData(**cached),
        )

    try:
        agent: DeerFlowAgent = request.app.state.deerflow_agent
        result = await agent.chat(
            tenant_id=body.tenant_id,
            user_id=body.user_id,
            session_id=body.session_id,
            query=body.query,
        )
    except Exception:
        logger.exception("Agent chat failed")
        result = {
            "answer": "抱歉，系统暂时出现问题，已为您转接人工客服。",
            "need_manual": True,
            "manual_reason": "系统异常",
            "sources": [],
        }

    # Cache non-handoff results
    if not result["need_manual"]:
        await cache_query_result(cache_key, result, ttl=QUERY_CACHE_TTL)

    return ChatResponse(
        code=200,
        msg="success",
        data=ChatResponseData(
            answer=result["answer"],
            need_manual=result["need_manual"],
            manual_reason=result["manual_reason"],
            sources=result["sources"],
        ),
    )
