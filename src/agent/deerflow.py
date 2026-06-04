import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from langgraph.graph import END, StateGraph
from openai import AsyncOpenAI
from sqlalchemy import select

from src.agent.intent import Intent, classify_intent, needs_human_handoff
from src.agent.risk_control import sanitize_response, should_force_handoff
from src.config import Settings
from src.db.milvus import MilvusClient
from src.db.mysql import ChatLog, PromptConfig, get_session
from src.db.redis import (
    cache_chat_context,
    get_chat_context,
    get_redis,
    is_manual_locked,
)
from src.utils.embedding import get_embedding

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """你是珠宝行业专业AI客服，按照以下分层规则回答：

【知识库优先】
如果系统提供了知识库相关内容，优先基于知识库内容回答，确保信息准确。

【通用珠宝知识】
如果没有相关知识库内容，但问题属于通用珠宝知识（如4C标准、材质特性、保养常识、搭配建议等），可以用你自身的珠宝行业知识回答，回答时注明"以下为通用知识参考"。

【必须来自知识库的业务信息】
以下信息严禁猜测，必须有知识库或实时数据支撑，否则转人工：
- 价格、折扣、促销活动、优惠力度
- 库存、到货时间、供货周期
- 定制周期、定制费用、定制流程
- 以旧换新、保修、退换货等具体政策条款
- 拿货政策、批发价格、代理政策

【必须转人工的情况】
- 投诉、退款、退货、纠纷、质疑真假
- 定制设计、私人定制、特殊工艺、来图定制
- 大额议价、渠道价格、合作政策、加盟代理
- 法律、维权、假货质疑、工商投诉

【回答风格】
- 专业、简洁、礼貌，符合珠宝行业B端批发话术
- 必须记住用户历史咨询内容，跨会话保持记忆
- 不承诺保值、升值、保真、权威认证等无法验证的内容

【转人工话术】
需要转人工时统一回复："抱歉，这个问题需要人工客服为您准确解答，我已帮您转接人工。"

你的任务：根据用户问题 + 知识库内容 + 历史对话，给出精准回答。"""

HANDOFF_MESSAGE = "抱歉，这个问题需要人工客服为您准确解答，我已帮您转接人工。"

KNOWLEDGE_HIT_STRONG = "strong"
KNOWLEDGE_HIT_WEAK = "weak"
KNOWLEDGE_HIT_NONE = "none"

KNOWLEDGE_REQUIRED_INTENTS = {
    Intent.PRICE_INQUIRY,
}

KNOWLEDGE_REQUIRED_KEYWORDS = (
    "价格", "多少钱", "报价", "什么价", "几钱", "价位", "克价", "工费", "金价",
    "库存", "现货", "有货", "没货", "到货", "补货", "供货", "货期",
    "活动", "促销", "优惠", "折扣", "满减", "赠品",
    "退换", "退货", "退款", "换货", "维修", "质量问题", "保修", "质保", "售后政策",
    "拿货", "批发", "代理", "加盟", "合作政策",
    "起订", "交期", "周期", "定制费用", "定制流程",
)


@dataclass
class ChatState:
    tenant_id: str = ""
    user_id: str = ""
    session_id: str = ""
    query: str = ""
    query_embedding: Optional[list] = None
    intent: str = "general"
    need_manual: bool = False
    manual_reason: str = ""
    knowledge_results: list = field(default_factory=list)
    knowledge_hit_type: str = KNOWLEDGE_HIT_NONE
    knowledge_score: float = 0.0
    memory_results: list = field(default_factory=list)
    chat_history: list = field(default_factory=list)
    answer: str = ""
    sources: list = field(default_factory=list)
    used_tokens: int = 0


def _is_knowledge_required_query(query: str, intent: str) -> bool:
    try:
        parsed_intent = Intent(intent)
    except ValueError:
        parsed_intent = Intent.UNKNOWN

    if parsed_intent in KNOWLEDGE_REQUIRED_INTENTS:
        return True

    return any(keyword in query for keyword in KNOWLEDGE_REQUIRED_KEYWORDS)


class DeerFlowAgent:
    def __init__(self, settings: Settings, milvus: MilvusClient):
        self.settings = settings
        self.milvus = milvus
        self.llm = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )
        self.graph = self._build_graph()

    def _build_graph(self):
        g = StateGraph(ChatState)

        g.add_node("validate", self._validate)
        g.add_node("load_context", self._load_context)
        g.add_node("load_memory", self._load_memory)
        g.add_node("intent_recognize", self._intent_recognize)
        g.add_node("risk_check", self._risk_check)
        g.add_node("search_knowledge", self._search_knowledge)
        g.add_node("generate_answer", self._generate_answer)
        g.add_node("write_log", self._write_log)
        g.add_node("store_memory", self._store_memory)

        g.set_entry_point("validate")
        g.add_edge("validate", "load_context")
        g.add_edge("load_context", "load_memory")
        g.add_edge("load_memory", "intent_recognize")
        g.add_conditional_edges(
            "intent_recognize",
            lambda s: "risk_check" if not s.need_manual else "generate_answer",
        )
        g.add_conditional_edges(
            "risk_check",
            lambda s: "search_knowledge" if not s.need_manual else "generate_answer",
        )
        g.add_edge("search_knowledge", "generate_answer")
        g.add_edge("generate_answer", "write_log")
        g.add_edge("write_log", "store_memory")
        g.add_edge("store_memory", END)

        return g.compile()

    async def _validate(self, state: ChatState) -> dict:
        if not state.tenant_id or not state.user_id or not state.session_id:
            return {"need_manual": True, "manual_reason": "参数校验失败", "answer": HANDOFF_MESSAGE}
        return {"tenant_id": state.tenant_id}

    async def _load_context(self, state: ChatState) -> dict:
        key = f"{state.tenant_id}:{state.user_id}:{state.session_id}"
        cached = await get_chat_context(key)
        if cached:
            return {"chat_history": cached[-self.settings.max_context_rounds * 2 :]}
        return {"chat_history": []}

    async def _load_memory(self, state: ChatState) -> dict:
        try:
            query_embedding = await get_embedding(state.query)
            memory_results = await asyncio.to_thread(
                self.milvus.search_memory,
                state.tenant_id, state.user_id, query_embedding, top_k=3,
            )
            return {"memory_results": memory_results, "query_embedding": query_embedding}
        except Exception:
            logger.exception("Failed to load user memory for tenant=%s user=%s", state.tenant_id, state.user_id)
            return {"memory_results": []}

    async def _intent_recognize(self, state: ChatState) -> dict:
        intent = classify_intent(state.query)
        if needs_human_handoff(intent):
            return {
                "intent": intent.value,
                "need_manual": True,
                "manual_reason": f"意图识别: {intent.value}",
                "answer": HANDOFF_MESSAGE,
            }
        return {"intent": intent.value}

    async def _risk_check(self, state: ChatState) -> dict:
        force, reason = should_force_handoff(state.query)
        if force:
            return {"need_manual": True, "manual_reason": reason, "answer": HANDOFF_MESSAGE}

        locked = await is_manual_locked(state.tenant_id, state.user_id)
        if locked:
            return {"need_manual": True, "manual_reason": "人工接管锁定中", "answer": HANDOFF_MESSAGE}
        return {"need_manual": False}

    async def _search_knowledge(self, state: ChatState) -> dict:
        try:
            query_embedding = state.query_embedding
            if query_embedding is None:
                query_embedding = await get_embedding(state.query)
            raw_results = await asyncio.to_thread(
                self.milvus.search_knowledge,
                state.tenant_id, query_embedding, top_k=self.settings.knowledge_top_k,
            )
            max_score = max((float(r.get("score") or 0) for r in raw_results), default=0.0)
            knowledge_results = [
                r for r in raw_results
                if float(r.get("score") or 0) >= self.settings.knowledge_weak_threshold
            ]

            if max_score >= self.settings.knowledge_strong_threshold:
                hit_type = KNOWLEDGE_HIT_STRONG
            elif max_score >= self.settings.knowledge_weak_threshold:
                hit_type = KNOWLEDGE_HIT_WEAK
            else:
                hit_type = KNOWLEDGE_HIT_NONE

            if hit_type == KNOWLEDGE_HIT_NONE and _is_knowledge_required_query(state.query, state.intent):
                return {
                    "knowledge_results": [],
                    "knowledge_hit_type": hit_type,
                    "knowledge_score": max_score,
                    "sources": [],
                    "need_manual": True,
                    "manual_reason": "知识库未命中业务问题",
                    "answer": HANDOFF_MESSAGE,
                }

            sources = [r["source"] for r in knowledge_results]
            return {
                "knowledge_results": knowledge_results,
                "knowledge_hit_type": hit_type,
                "knowledge_score": max_score,
                "sources": sources,
            }
        except Exception:
            logger.exception("Failed to search knowledge for tenant=%s", state.tenant_id)
            if _is_knowledge_required_query(state.query, state.intent):
                return {
                    "knowledge_results": [],
                    "knowledge_hit_type": KNOWLEDGE_HIT_NONE,
                    "knowledge_score": 0.0,
                    "sources": [],
                    "need_manual": True,
                    "manual_reason": "知识库检索失败",
                    "answer": HANDOFF_MESSAGE,
                }
            return {"knowledge_results": [], "knowledge_hit_type": KNOWLEDGE_HIT_NONE, "knowledge_score": 0.0}

    async def _generate_answer(self, state: ChatState) -> dict:
        if state.need_manual:
            return {"answer": state.answer or HANDOFF_MESSAGE}

        system_prompt = await self._get_system_prompt(state.tenant_id)

        knowledge_text = "\n".join(
            f"[{r.get('category', '')}] {r['content']}"
            for r in state.knowledge_results
        )
        memory_text = "\n".join(r["content"] for r in state.memory_results)

        messages = [{"role": "system", "content": system_prompt}]

        if knowledge_text:
            if state.knowledge_hit_type == KNOWLEDGE_HIT_WEAK:
                messages.append({
                    "role": "system",
                    "content": (
                        "知识库弱相关参考内容，仅可作为辅助参考；"
                        "不得据此编造价格、库存、活动、政策、交期等业务信息。\n"
                        f"{knowledge_text}"
                    ),
                })
            else:
                messages.append({"role": "system", "content": f"知识库强相关命中内容:\n{knowledge_text}"})
        if memory_text:
            messages.append({"role": "system", "content": f"用户历史记忆:\n{memory_text}"})

        for msg in state.chat_history:
            messages.append(msg)

        messages.append({"role": "user", "content": state.query})

        try:
            response = await self.llm.chat.completions.create(
                model=self.settings.llm_model,
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
            )
            raw_answer = response.choices[0].message.content
            answer = sanitize_response(raw_answer)
            used_tokens = response.usage.total_tokens if response.usage else 0
            return {"answer": answer, "used_tokens": used_tokens}
        except Exception:
            logger.exception("LLM call failed for tenant=%s", state.tenant_id)
            return {"answer": HANDOFF_MESSAGE, "need_manual": True, "manual_reason": "LLM调用失败"}

    async def _write_log(self, state: ChatState) -> dict:
        try:
            async with get_session() as session:
                log = ChatLog(
                    tenant_id=state.tenant_id,
                    channel="wechat",
                    user_id=state.user_id,
                    session_id=state.session_id,
                    user_query=state.query,
                    ai_answer=state.answer,
                    intent=state.intent,
                    need_manual=1 if state.need_manual else 0,
                    manual_reason=state.manual_reason,
                    used_tokens=state.used_tokens,
                )
                session.add(log)
                await session.commit()
        except Exception:
            logger.exception("Failed to write chat log for tenant=%s user=%s", state.tenant_id, state.user_id)

        key = f"{state.tenant_id}:{state.user_id}:{state.session_id}"
        history = state.chat_history + [
            {"role": "user", "content": state.query},
            {"role": "assistant", "content": state.answer},
        ]
        await cache_chat_context(key, history[-self.settings.max_context_rounds * 2 :])
        return {"used_tokens": state.used_tokens}

    async def _store_memory(self, state: ChatState) -> dict:
        try:
            content = f"用户: {state.query}\n客服: {state.answer}"
            embedding = await get_embedding(content)
            await asyncio.to_thread(
                self.milvus.insert_memory,
                tenant_id=state.tenant_id,
                user_id=state.user_id,
                session_id=state.session_id,
                content=content,
                embedding=embedding,
                created_at=int(time.time()),
            )
        except Exception:
            logger.exception("Failed to store memory for tenant=%s user=%s", state.tenant_id, state.user_id)
        return {"session_id": state.session_id}

    async def _get_system_prompt(self, tenant_id: str) -> str:
        try:
            r = get_redis()
            if r:
                cached = await r.get(f"prompt:{tenant_id}")
                if cached:
                    return cached
        except Exception:
            logger.debug("Redis prompt cache miss for tenant=%s", tenant_id)

        try:
            async with get_session() as session:
                result = await session.execute(
                    select(PromptConfig).where(PromptConfig.tenant_id == tenant_id)
                )
                config = result.scalar_one_or_none()
                if config and config.system_prompt:
                    try:
                        r = get_redis()
                        if r:
                            await r.setex(f"prompt:{tenant_id}", 3600, config.system_prompt)
                    except Exception:
                        logger.debug("Failed to cache prompt for tenant=%s", tenant_id)
                    return config.system_prompt
        except Exception:
            logger.warning("Failed to load prompt config for tenant=%s, using default", tenant_id)

        return DEFAULT_SYSTEM_PROMPT

    async def chat(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str,
        query: str,
    ) -> dict:
        state = ChatState(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            query=query,
        )
        result = await self.graph.ainvoke(state)

        # LangGraph may return AddableValuesDict instead of ChatState
        get = result.get if hasattr(result, "get") else lambda k, d=None: getattr(result, k, d)
        return {
            "answer": get("answer", ""),
            "need_manual": get("need_manual", False),
            "manual_reason": get("manual_reason", ""),
            "sources": get("sources", []),
        }
