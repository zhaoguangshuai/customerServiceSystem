import pytest

from src.agent.deerflow import (
    DeerFlowAgent,
    ChatState,
    HANDOFF_MESSAGE,
    KNOWLEDGE_HIT_NONE,
    KNOWLEDGE_HIT_WEAK,
    _is_knowledge_required_query,
)
from src.config import Settings


class FakeMilvus:
    def __init__(self, results):
        self.results = results

    def search_knowledge(self, tenant_id, query_embedding, top_k=3):
        return self.results[:top_k]


def make_agent(results):
    settings = Settings(
        llm_api_key="test-key",
        mysql_password="test",
        redis_host="localhost",
        mysql_host="localhost",
        milvus_uri="http://localhost:19530",
        knowledge_weak_threshold=0.50,
        knowledge_strong_threshold=0.72,
        knowledge_top_k=3,
    )
    return DeerFlowAgent(settings, FakeMilvus(results))


@pytest.mark.asyncio
async def test_low_score_business_query_hands_off():
    agent = make_agent([
        {"content": "低相关内容", "category": "faq", "source": "doc.md", "score": 0.31}
    ])
    state = ChatState(
        tenant_id="t1",
        user_id="u1",
        session_id="s1",
        query="这个黄金手镯多少钱",
        query_embedding=[0.1],
        intent="price_inquiry",
    )

    result = await agent._search_knowledge(state)

    assert result["need_manual"] is True
    assert result["manual_reason"] == "知识库未命中业务问题"
    assert result["answer"] == HANDOFF_MESSAGE
    assert result["knowledge_results"] == []
    assert result["knowledge_hit_type"] == KNOWLEDGE_HIT_NONE


@pytest.mark.asyncio
async def test_low_score_general_query_drops_knowledge_without_handoff():
    agent = make_agent([
        {"content": "低相关内容", "category": "faq", "source": "doc.md", "score": 0.31}
    ])
    state = ChatState(
        tenant_id="t1",
        user_id="u1",
        session_id="s1",
        query="黄金日常怎么保养",
        query_embedding=[0.1],
        intent="after_sales",
    )

    result = await agent._search_knowledge(state)

    assert "need_manual" not in result
    assert result["knowledge_results"] == []
    assert result["sources"] == []
    assert result["knowledge_hit_type"] == KNOWLEDGE_HIT_NONE


@pytest.mark.asyncio
async def test_weak_score_keeps_reference_content():
    agent = make_agent([
        {"content": "弱相关内容", "category": "faq", "source": "doc.md", "score": 0.61},
        {"content": "低相关内容", "category": "faq", "source": "noise.md", "score": 0.2},
    ])
    state = ChatState(
        tenant_id="t1",
        user_id="u1",
        session_id="s1",
        query="这款有现货吗",
        query_embedding=[0.1],
        intent="product_inquiry",
    )

    result = await agent._search_knowledge(state)

    assert result["knowledge_hit_type"] == KNOWLEDGE_HIT_WEAK
    assert result["sources"] == ["doc.md"]
    assert [r["content"] for r in result["knowledge_results"]] == ["弱相关内容"]


def test_knowledge_required_query_keeps_general_care_available():
    assert _is_knowledge_required_query("这个黄金手镯多少钱", "price_inquiry") is True
    assert _is_knowledge_required_query("这款项链有现货吗", "product_inquiry") is True
    assert _is_knowledge_required_query("黄金日常怎么保养", "after_sales") is False
