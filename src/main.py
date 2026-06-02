from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.config import get_settings
from src.db.mysql import init_db, close_db, ensure_admin_user, check_mysql_health
from src.db.milvus import MilvusClient
from src.db.redis import init_redis, close_redis, check_redis_health
from src.agent.deerflow import DeerFlowAgent
from src.api.chat import router as chat_router
from src.api.knowledge import router as knowledge_router
from src.api.admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # Initialize MySQL
    await init_db(settings.mysql_url)

    # Ensure default admin user exists
    await ensure_admin_user()

    # Initialize Redis
    await init_redis(settings)

    # Initialize Milvus
    milvus_client = MilvusClient(settings)
    milvus_client.init_collections()

    # Initialize DeerFlow agent
    agent = DeerFlowAgent(settings, milvus_client)
    app.state.deerflow_agent = agent
    app.state.milvus_client = milvus_client

    yield

    await close_redis()
    await close_db()
    milvus_client.close()


app = FastAPI(
    title="珠宝行业AI智能客服系统",
    description="微信私域 AI 智能客服 - WeChat Private Domain AI Customer Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api/v1/jewelry", tags=["chat"])
app.include_router(knowledge_router, prefix="/api/v1/jewelry", tags=["knowledge"])
app.include_router(admin_router, prefix="/api/v1", tags=["admin"])


@app.get("/health")
async def health():
    """Basic liveness check - always returns 200 if the app is running."""
    return {"status": "ok", "channel": "wechat"}


@app.get("/readiness")
async def readiness():
    """Readiness probe - checks all dependencies are reachable.

    Returns 200 if all dependencies are healthy, 503 if any are down.
    Used by container orchestrators (k8s, docker-compose) to decide
    if the service can receive traffic.
    """
    mysql_status = await check_mysql_health()
    redis_status = await check_redis_health()
    milvus_status = app.state.milvus_client.check_health()

    checks = {
        "mysql": mysql_status,
        "redis": redis_status,
        "milvus": milvus_status,
    }

    all_ok = all(c["status"] == "ok" for c in checks.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        content={
            "status": "ready" if all_ok else "not_ready",
            "checks": checks,
        },
        status_code=status_code,
    )


# Serve Vue frontend static files (after build)
_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
