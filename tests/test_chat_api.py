from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestChatRequestValidation:
    def test_missing_tenant_id(self, client):
        resp = client.post("/api/v1/jewelry/chat", json={
            "user_id": "u1", "query": "hello", "session_id": "s1",
        })
        assert resp.status_code == 422

    def test_missing_user_id(self, client):
        resp = client.post("/api/v1/jewelry/chat", json={
            "tenant_id": "t1", "query": "hello", "session_id": "s1",
        })
        assert resp.status_code == 422

    def test_missing_query(self, client):
        resp = client.post("/api/v1/jewelry/chat", json={
            "tenant_id": "t1", "user_id": "u1", "session_id": "s1",
        })
        assert resp.status_code == 422

    def test_missing_session_id(self, client):
        resp = client.post("/api/v1/jewelry/chat", json={
            "tenant_id": "t1", "user_id": "u1", "query": "hello",
        })
        assert resp.status_code == 422

    def test_empty_tenant_id_rejected(self, client):
        resp = client.post("/api/v1/jewelry/chat", json={
            "tenant_id": "", "user_id": "u1", "query": "hello", "session_id": "s1",
        })
        assert resp.status_code == 422

    def test_invalid_channel_rejected(self, client):
        resp = client.post("/api/v1/jewelry/chat", json={
            "tenant_id": "t1", "user_id": "u1", "query": "hello",
            "session_id": "s1", "channel": "douyin",
        })
        assert resp.status_code == 422

    def test_wechat_channel_accepted(self, client):
        """WeChat channel should be accepted (though the agent call will fail without services)."""
        with patch("src.api.chat.get_cached_query", new_callable=AsyncMock, return_value=None):
            with patch("src.api.chat.cache_query_result", new_callable=AsyncMock):
                # The agent won't be initialized in test, so this will error
                # but the validation passed
                resp = client.post("/api/v1/jewelry/chat", json={
                    "tenant_id": "t1", "user_id": "u1", "query": "hello",
                    "session_id": "s1", "channel": "wechat",
                })
                # Should get past validation (not 422)
                assert resp.status_code != 422


class TestChatEndpoint:
    def test_cached_response_returned(self, client):
        cached_data = {
            "answer": "cached answer",
            "need_manual": False,
            "manual_reason": "",
            "sources": ["doc1.pdf"],
        }
        with patch("src.api.chat.get_cached_query", new_callable=AsyncMock, return_value=cached_data):
            resp = client.post("/api/v1/jewelry/chat", json={
                "tenant_id": "t1", "user_id": "u1", "query": "test query",
                "session_id": "s1",
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["code"] == 200
            assert data["data"]["answer"] == "cached answer"
            assert data["data"]["sources"] == ["doc1.pdf"]

    def test_handoff_result_not_cached(self, client):
        """Results with need_manual=True should not be cached."""
        mock_result = {
            "answer": "转人工",
            "need_manual": True,
            "manual_reason": "投诉",
            "sources": [],
        }
        mock_agent = AsyncMock()
        mock_agent.chat.return_value = mock_result

        with patch("src.api.chat.get_cached_query", new_callable=AsyncMock, return_value=None):
            with patch("src.api.chat.cache_query_result", new_callable=AsyncMock) as mock_cache:
                # Set the agent on app state
                app.state.deerflow_agent = mock_agent
                resp = client.post("/api/v1/jewelry/chat", json={
                    "tenant_id": "t1", "user_id": "u1", "query": "我要投诉",
                    "session_id": "s1",
                })
                assert resp.status_code == 200
                mock_cache.assert_not_called()
