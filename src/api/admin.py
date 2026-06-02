import os
from datetime import datetime, timedelta

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import func, select, text

from src.db.mysql import (
    AdminUser,
    ChatLog,
    FAQ,
    KnowledgeDocument,
    PromptConfig,
    Tenant,
    get_session,
)

router = APIRouter(prefix="/admin")

JWT_SECRET = os.getenv("JWT_SECRET", "jewelry-ai-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

security = HTTPBearer(auto_error=False)


def create_token(payload: dict) -> str:
    payload["exp"] = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    if not credentials:
        raise HTTPException(status_code=401, detail="未登录")
    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的token")
    return payload


# --- Auth ---


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(body: LoginRequest):
    async with get_session() as session:
        result = await session.execute(
            select(AdminUser).where(AdminUser.username == body.username)
        )
        user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not bcrypt.checkpw(body.password.encode(), user.password.encode()):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if user.status != 1:
        raise HTTPException(status_code=403, detail="账号已停用")

    token = create_token({
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "tenant_id": user.tenant_id or "",
    })
    return {
        "code": 200,
        "data": {
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "tenant_id": user.tenant_id,
            },
        },
    }


@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    return {
        "code": 200,
        "data": {
            "user_id": user.get("user_id"),
            "username": user.get("username"),
            "role": user.get("role"),
            "tenant_id": user.get("tenant_id"),
        },
    }


# --- Tenant Management ---

class TenantCreate(BaseModel):
    tenant_id: str
    tenant_name: str
    contact: str = ""
    phone: str = ""


@router.get("/tenants")
async def list_tenants(user=Depends(get_current_user)):
    async with get_session() as session:
        result = await session.execute(select(Tenant))
        tenants = result.scalars().all()
    return {
        "code": 200,
        "data": [
            {
                "id": t.id,
                "tenant_id": t.tenant_id,
                "tenant_name": t.tenant_name,
                "contact": t.contact,
                "phone": t.phone,
                "status": t.status,
            }
            for t in tenants
        ],
    }


@router.post("/tenants")
async def create_tenant(body: TenantCreate, user=Depends(get_current_user)):
    async with get_session() as session:
        existing = await session.execute(
            select(Tenant).where(Tenant.tenant_id == body.tenant_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="租户ID已存在")

        tenant = Tenant(
            tenant_id=body.tenant_id,
            tenant_name=body.tenant_name,
            contact=body.contact,
            phone=body.phone,
        )
        session.add(tenant)
        await session.commit()
    return {"code": 200, "msg": "success"}


class TenantUpdate(BaseModel):
    tenant_name: str = None
    contact: str = None
    phone: str = None
    status: int = None


@router.put("/tenants/{tenant_id}")
async def update_tenant(tenant_id: str, body: TenantUpdate, user=Depends(get_current_user)):
    async with get_session() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.tenant_id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="租户不存在")

        if body.tenant_name is not None:
            tenant.tenant_name = body.tenant_name
        if body.contact is not None:
            tenant.contact = body.contact
        if body.phone is not None:
            tenant.phone = body.phone
        if body.status is not None:
            tenant.status = body.status
        await session.commit()
    return {"code": 200, "msg": "success"}


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(tenant_id: str, user=Depends(get_current_user)):
    async with get_session() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.tenant_id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="租户不存在")

        await session.delete(tenant)
        await session.commit()
    return {"code": 200, "msg": "success"}


# --- Prompt Config ---

class PromptUpdate(BaseModel):
    system_prompt: str


@router.get("/prompts/{tenant_id}")
async def get_prompt(tenant_id: str, user=Depends(get_current_user)):
    async with get_session() as session:
        result = await session.execute(
            select(PromptConfig).where(PromptConfig.tenant_id == tenant_id)
        )
        config = result.scalar_one_or_none()
    if not config:
        return {"code": 200, "data": {"system_prompt": ""}}
    return {"code": 200, "data": {"system_prompt": config.system_prompt or ""}}


@router.put("/prompts/{tenant_id}")
async def update_prompt(tenant_id: str, body: PromptUpdate, user=Depends(get_current_user)):
    async with get_session() as session:
        result = await session.execute(
            select(PromptConfig).where(PromptConfig.tenant_id == tenant_id)
        )
        config = result.scalar_one_or_none()
        if config:
            config.system_prompt = body.system_prompt
        else:
            config = PromptConfig(tenant_id=tenant_id, system_prompt=body.system_prompt)
            session.add(config)
        await session.commit()

    # Invalidate cache
    from src.db.redis import get_redis

    try:
        r = get_redis()
        if r:
            await r.delete(f"prompt:{tenant_id}")
    except Exception:
        pass

    return {"code": 200, "msg": "success"}


# --- Chat Logs ---

@router.get("/chat-logs")
async def list_chat_logs(
    tenant_id: str = None,
    user_id: str = None,
    start_date: str = None,
    end_date: str = None,
    keyword: str = None,
    page: int = 1,
    page_size: int = 20,
    user=Depends(get_current_user),
):
    async with get_session() as session:
        base_q = select(ChatLog)
        if tenant_id:
            base_q = base_q.where(ChatLog.tenant_id == tenant_id)
        if user_id:
            base_q = base_q.where(ChatLog.user_id == user_id)
        if start_date:
            base_q = base_q.where(ChatLog.created_at >= start_date)
        if end_date:
            base_q = base_q.where(ChatLog.created_at <= end_date + " 23:59:59")
        if keyword:
            like_pattern = f"%{keyword}%"
            base_q = base_q.where(
                ChatLog.user_query.ilike(like_pattern)
                | ChatLog.ai_answer.ilike(like_pattern)
            )

        # Total count
        count_q = select(func.count()).select_from(base_q.subquery())
        total = (await session.execute(count_q)).scalar() or 0

        # Paginated results
        query = base_q.order_by(ChatLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(query)
        logs = result.scalars().all()

    return {
        "code": 200,
        "data": {
            "total": total,
            "items": [
                {
                    "id": l.id,
                    "tenant_id": l.tenant_id,
                    "user_id": l.user_id,
                    "session_id": l.session_id,
                    "user_query": l.user_query,
                    "ai_answer": l.ai_answer,
                    "intent": l.intent,
                    "need_manual": l.need_manual,
                    "manual_reason": l.manual_reason,
                    "used_tokens": l.used_tokens,
                    "created_at": l.created_at.isoformat() if l.created_at else None,
                }
                for l in logs
            ],
        },
    }


# --- FAQ Management ---

class FAQCreate(BaseModel):
    tenant_id: str
    title: str
    answer: str
    category: str = ""
    sort: int = 0


@router.get("/faqs")
async def list_faqs(tenant_id: str, user=Depends(get_current_user)):
    async with get_session() as session:
        result = await session.execute(
            select(FAQ).where(FAQ.tenant_id == tenant_id).order_by(FAQ.sort.desc())
        )
        faqs = result.scalars().all()
    return {
        "code": 200,
        "data": [
            {
                "id": f.id,
                "title": f.title,
                "answer": f.answer,
                "category": f.category,
                "sort": f.sort,
            }
            for f in faqs
        ],
    }


@router.post("/faqs")
async def create_faq(body: FAQCreate, user=Depends(get_current_user)):
    async with get_session() as session:
        faq = FAQ(
            tenant_id=body.tenant_id,
            title=body.title,
            answer=body.answer,
            category=body.category,
            sort=body.sort,
        )
        session.add(faq)
        await session.commit()
    return {"code": 200, "msg": "success"}


class FAQUpdate(BaseModel):
    title: str = None
    answer: str = None
    category: str = None
    sort: int = None


@router.put("/faqs/{faq_id}")
async def update_faq(faq_id: int, body: FAQUpdate, user=Depends(get_current_user)):
    async with get_session() as session:
        result = await session.execute(select(FAQ).where(FAQ.id == faq_id))
        faq = result.scalar_one_or_none()
        if not faq:
            raise HTTPException(status_code=404, detail="FAQ不存在")

        if body.title is not None:
            faq.title = body.title
        if body.answer is not None:
            faq.answer = body.answer
        if body.category is not None:
            faq.category = body.category
        if body.sort is not None:
            faq.sort = body.sort
        await session.commit()
    return {"code": 200, "msg": "success"}


@router.delete("/faqs/{faq_id}")
async def delete_faq(faq_id: int, user=Depends(get_current_user)):
    async with get_session() as session:
        result = await session.execute(select(FAQ).where(FAQ.id == faq_id))
        faq = result.scalar_one_or_none()
        if not faq:
            raise HTTPException(status_code=404, detail="FAQ不存在")

        await session.delete(faq)
        await session.commit()
    return {"code": 200, "msg": "success"}


# --- Quality Inspection ---


class ReviewSubmit(BaseModel):
    quality_score: int
    review_comment: str = ""


class FlagRequest(BaseModel):
    reason: str = ""


@router.get("/reviews")
async def list_reviews(
    tenant_id: str = None,
    review_status: str = None,
    page: int = 1,
    page_size: int = 20,
    user=Depends(get_current_user),
):
    async with get_session() as session:
        base_q = select(ChatLog)
        if tenant_id:
            base_q = base_q.where(ChatLog.tenant_id == tenant_id)
        if review_status:
            base_q = base_q.where(ChatLog.review_status == review_status)

        count_q = select(func.count()).select_from(base_q.subquery())
        total = (await session.execute(count_q)).scalar() or 0

        query = base_q.order_by(ChatLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(query)
        logs = result.scalars().all()

    return {
        "code": 200,
        "data": {
            "total": total,
            "items": [
                {
                    "id": l.id,
                    "tenant_id": l.tenant_id,
                    "user_id": l.user_id,
                    "session_id": l.session_id,
                    "user_query": l.user_query,
                    "ai_answer": l.ai_answer,
                    "intent": l.intent,
                    "need_manual": l.need_manual,
                    "manual_reason": l.manual_reason,
                    "used_tokens": l.used_tokens,
                    "review_status": l.review_status,
                    "quality_score": l.quality_score,
                    "reviewer_id": l.reviewer_id,
                    "review_comment": l.review_comment,
                    "reviewed_at": l.reviewed_at.isoformat() if l.reviewed_at else None,
                    "created_at": l.created_at.isoformat() if l.created_at else None,
                }
                for l in logs
            ],
        },
    }


@router.put("/reviews/{log_id}")
async def submit_review(log_id: int, body: ReviewSubmit, user=Depends(get_current_user)):
    if body.quality_score < 1 or body.quality_score > 5:
        raise HTTPException(status_code=400, detail="评分必须在1-5之间")

    async with get_session() as session:
        result = await session.execute(select(ChatLog).where(ChatLog.id == log_id))
        log = result.scalar_one_or_none()
        if not log:
            raise HTTPException(status_code=404, detail="对话记录不存在")

        log.review_status = "reviewed"
        log.quality_score = body.quality_score
        log.reviewer_id = user.get("user_id")
        log.review_comment = body.review_comment
        log.reviewed_at = datetime.utcnow()
        await session.commit()

    return {"code": 200, "msg": "success"}


@router.put("/reviews/{log_id}/flag")
async def flag_review(log_id: int, body: FlagRequest, user=Depends(get_current_user)):
    async with get_session() as session:
        result = await session.execute(select(ChatLog).where(ChatLog.id == log_id))
        log = result.scalar_one_or_none()
        if not log:
            raise HTTPException(status_code=404, detail="对话记录不存在")

        log.review_status = "flagged"
        log.reviewer_id = user.get("user_id")
        log.review_comment = body.reason
        log.reviewed_at = datetime.utcnow()
        await session.commit()

    return {"code": 200, "msg": "success"}


@router.get("/reviews/stats")
async def review_stats(tenant_id: str = None, user=Depends(get_current_user)):
    async with get_session() as session:
        base = select(ChatLog)
        if tenant_id:
            base = base.where(ChatLog.tenant_id == tenant_id)

        total = (await session.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0

        pending_q = base.where(ChatLog.review_status == "pending")
        pending = (await session.execute(select(func.count()).select_from(pending_q.subquery()))).scalar() or 0

        reviewed_q = base.where(ChatLog.review_status == "reviewed")
        reviewed = (await session.execute(select(func.count()).select_from(reviewed_q.subquery()))).scalar() or 0

        flagged_q = base.where(ChatLog.review_status == "flagged")
        flagged = (await session.execute(select(func.count()).select_from(flagged_q.subquery()))).scalar() or 0

        score_q = select(func.avg(ChatLog.quality_score)).where(ChatLog.quality_score.isnot(None))
        if tenant_id:
            score_q = score_q.where(ChatLog.tenant_id == tenant_id)
        avg_score = (await session.execute(score_q)).scalar()
        avg_score = round(float(avg_score), 1) if avg_score else 0

    return {
        "code": 200,
        "data": {
            "total": total,
            "pending": pending,
            "reviewed": reviewed,
            "flagged": flagged,
            "avg_score": avg_score,
        },
    }


# --- Statistics ---


@router.get("/statistics")
async def get_statistics(tenant_id: str = None, start_date: str = None, end_date: str = None, user=Depends(get_current_user)):
    async with get_session() as session:
        # Tenant count
        tenant_q = select(func.count()).select_from(Tenant)
        tenant_count = (await session.execute(tenant_q)).scalar() or 0

        # Knowledge doc count
        doc_q = select(func.count()).select_from(KnowledgeDocument).where(KnowledgeDocument.status == 1)
        if tenant_id:
            doc_q = doc_q.where(KnowledgeDocument.tenant_id == tenant_id)
        doc_count = (await session.execute(doc_q)).scalar() or 0

        # Chat base filter
        def chat_base():
            q = select(ChatLog)
            if tenant_id:
                q = q.where(ChatLog.tenant_id == tenant_id)
            return q

        # Today's chat count
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_q = chat_base().where(ChatLog.created_at >= today)
        today_chats = (await session.execute(select(func.count()).select_from(today_q.subquery()))).scalar() or 0

        # Total chats (all time or within date range)
        total_q = chat_base()
        if start_date:
            total_q = total_q.where(ChatLog.created_at >= start_date)
        if end_date:
            total_q = total_q.where(ChatLog.created_at <= end_date + " 23:59:59")
        total_chats = (await session.execute(select(func.count()).select_from(total_q.subquery()))).scalar() or 0

        # Handoff stats
        handoff_q = total_q.where(ChatLog.need_manual == 1)
        handoff_chats = (await session.execute(select(func.count()).select_from(handoff_q.subquery()))).scalar() or 0
        handoff_rate = round(handoff_chats / total_chats * 100, 1) if total_chats > 0 else 0

        # Total tokens consumed
        token_q = select(func.coalesce(func.sum(ChatLog.used_tokens), 0)).select_from(total_q.subquery())
        total_tokens = (await session.execute(token_q)).scalar() or 0

        # Unique users
        users_q = select(func.count(func.distinct(ChatLog.user_id))).select_from(total_q.subquery())
        unique_users = (await session.execute(users_q)).scalar() or 0

        # Daily trend (last 7 days)
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        trend_q = (
            select(
                func.date(ChatLog.created_at).label("date"),
                func.count().label("count"),
            )
            .where(ChatLog.created_at >= seven_days_ago)
            .group_by(func.date(ChatLog.created_at))
            .order_by(func.date(ChatLog.created_at))
        )
        if tenant_id:
            trend_q = trend_q.where(ChatLog.tenant_id == tenant_id)
        trend_rows = (await session.execute(trend_q)).all()
        daily_trend = [{"date": str(r.date), "count": r.count} for r in trend_rows]

        # Intent distribution
        intent_q = (
            select(
                ChatLog.intent,
                func.count().label("count"),
            )
        )
        if tenant_id:
            intent_q = intent_q.where(ChatLog.tenant_id == tenant_id)
        if start_date:
            intent_q = intent_q.where(ChatLog.created_at >= start_date)
        if end_date:
            intent_q = intent_q.where(ChatLog.created_at <= end_date + " 23:59:59")
        intent_q = intent_q.group_by(ChatLog.intent)
        intent_rows = (await session.execute(intent_q)).all()
        intent_distribution = [
            {"intent": r.intent or "general", "count": r.count}
            for r in intent_rows
        ]

    return {
        "code": 200,
        "data": {
            "tenant_count": tenant_count,
            "doc_count": doc_count,
            "today_chats": today_chats,
            "total_chats": total_chats,
            "handoff_rate": handoff_rate,
            "total_tokens": total_tokens,
            "unique_users": unique_users,
            "daily_trend": daily_trend,
            "intent_distribution": intent_distribution,
        },
    }
