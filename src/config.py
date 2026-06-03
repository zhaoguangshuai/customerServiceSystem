from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    deerflow_env: str = "dev"
    prompt_path: str = "./config/jewelry_system_prompt.txt"

    # Milvus
    milvus_uri: str = "http://milvus:19530"
    milvus_user: str = ""
    milvus_password: str = ""
    milvus_collection_know: str = "jewelry_knowledge"
    milvus_collection_memory: str = "user_chat_memory"
    embedding_dim: int = 1024

    # MySQL
    mysql_host: str = "mysql"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "root123456"
    mysql_db: str = "jewelry_ai"

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0

    # LLM (阿里云 DashScope - 通义千问)
    llm_model: str = "qwen3.7-plus"
    llm_api_key: str = ""
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    embedding_model: str = "text-embedding-v3"

    # Business
    max_context_rounds: int = 10
    manual_lock_minutes: int = 30

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}?charset=utf8mb4"
        )

    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
