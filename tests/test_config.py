import pytest

from src.config import Settings


class TestSettings:
    def test_default_values(self):
        s = Settings(
            llm_api_key="test-key",
            mysql_password="test",
            redis_host="localhost",
            mysql_host="localhost",
            milvus_uri="http://localhost:19530",
        )
        assert s.app_host == "0.0.0.0"
        assert s.app_port == 8000
        assert s.llm_model == "gpt-3.5-turbo"
        assert s.embedding_dim == 1536
        assert s.max_context_rounds == 10
        assert s.manual_lock_minutes == 30

    def test_mysql_url_property(self):
        s = Settings(
            llm_api_key="test-key",
            mysql_host="dbhost",
            mysql_port=3307,
            mysql_user="myuser",
            mysql_password="mypass",
            mysql_db="mydb",
            redis_host="localhost",
            milvus_uri="http://localhost:19530",
        )
        url = s.mysql_url
        assert "aiomysql" in url
        assert "myuser:mypass@dbhost:3307/mydb" in url
        assert "charset=utf8mb4" in url

    def test_redis_url_no_password(self):
        s = Settings(
            llm_api_key="test-key",
            redis_host="redishost",
            redis_port=6380,
            redis_password="",
            mysql_host="localhost",
            mysql_password="test",
            milvus_uri="http://localhost:19530",
        )
        assert s.redis_url == "redis://redishost:6380/0"

    def test_redis_url_with_password(self):
        s = Settings(
            llm_api_key="test-key",
            redis_host="redishost",
            redis_port=6380,
            redis_password="secret",
            redis_db=2,
            mysql_host="localhost",
            mysql_password="test",
            milvus_uri="http://localhost:19530",
        )
        assert s.redis_url == "redis://:secret@redishost:6380/2"

    def test_milvus_collections(self):
        s = Settings(
            llm_api_key="test-key",
            mysql_host="localhost",
            mysql_password="test",
            redis_host="localhost",
            milvus_uri="http://localhost:19530",
        )
        assert s.milvus_collection_know == "jewelry_knowledge"
        assert s.milvus_collection_memory == "user_chat_memory"
