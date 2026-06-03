# 珠宝行业AI智能客服系统

> 基于 LangGraph + Milvus 向量检索 + 大模型的多租户珠宝行业智能客服系统，支持知识库管理、微信自动回复、意图识别、风险控制、人工转接及质检。

---

## 快速开始

### 1. 环境准备

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose

### 2. 启动基础服务

```bash
docker-compose up -d
```

启动后会自动运行以下服务：

| 服务 | 端口 | 说明 |
|------|------|------|
| MySQL 8.0 | 3306 | 主数据库，自动执行 `init.sql` 初始化表结构 |
| Redis 7 | 6379 | 缓存（对话上下文、Embedding、锁） |
| Milvus 2.4 | 19530 / 9091 | 向量数据库（知识库 + 用户记忆） |

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入大模型 API Key：

```env
LLM_API_KEY=sk-your-dashscope-api-key
```

### 4. 启动后端

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 本地开发（连接 docker-compose 中的服务）
MILVUS_URI=http://127.0.0.1:19530 MYSQL_HOST=127.0.0.1 REDIS_HOST=127.0.0.1 \
  uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

后端默认管理员账号：`admin` / `admin123`

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000，登录后即可使用管理后台。

### 6. Docker 一键部署（生产）

```bash
docker-compose build
docker-compose up -d
```

前端构建产物会自动嵌入后端容器，访问 http://localhost:8000。

---

## 系统架构

```
┌─────────────┐     ┌──────────────────────────────────────────┐
│  微信桌面端  │────▶│          WeChat Listener                 │
│  (wxauto)   │◀────│  (client.py / mock_client.py)            │
└─────────────┘     └──────────────┬───────────────────────────┘
                                   │ HTTP
┌─────────────┐     ┌──────────────▼───────────────────────────┐
│  管理后台    │────▶│          FastAPI Backend                 │
│  Vue 3 +    │◀────│  ┌─────────────────────────────────────┐ │
│  Element Plus│     │  │  LangGraph Agent (deerflow.py)      │ │
└─────────────┘     │  │  validate → load_context → intent    │ │
                    │  │  → risk_check → search_knowledge     │ │
                    │  │  → generate_answer → write_log       │ │
                    │  └─────────────────────────────────────┘ │
                    └────┬──────────┬──────────┬───────────────┘
                         │          │          │
                    ┌────▼───┐ ┌────▼───┐ ┌────▼────┐
                    │ Milvus │ │ MySQL  │ │  Redis  │
                    │ 向量库 │ │ 主数据 │ │  缓存   │
                    └────────┘ └────────┘ └─────────┘
```

### AI Agent 处理流程

1. **参数校验** — 检查 tenant_id、query 等必填字段
2. **加载上下文** — 从 Redis 读取最近对话记录
3. **加载用户记忆** — Milvus 向量搜索历史相关对话
4. **意图识别** — 关键词分类（8 种意图）
5. **风险控制** — 提示词注入检测、敏感词过滤、违禁话术拦截
6. **知识库检索** — Milvus 向量搜索匹配知识条目（COSINE 相似度）
7. **生成回答** — 调用大模型，结合知识库 + 上下文 + 系统提示词
8. **写入日志** — MySQL 记录完整对话日志
9. **存储记忆** — 将本轮对话向量化存入 Milvus

### 回答策略

- 命中知识库 → 优先使用知识库内容回答
- 未命中知识库 → 大模型使用自身知识回答（标注"以下为通用知识参考"）
- 涉及投诉/砍价/定制/注入攻击 → 自动转人工

---

## 目录结构

```
customerServiceSystem/
├── .env.example                  # 环境变量模板
├── docker-compose.yml            # 服务编排（app + mysql + redis + milvus）
├── Dockerfile                    # 多阶段构建（Node 编译 + Python 运行）
├── requirements.txt              # Python 依赖
├── run_wechat_listener.py        # 微信监听独立入口
├── config/
│   └── jewelry_system_prompt.txt # 默认系统提示词
├── src/
│   ├── main.py                   # FastAPI 应用入口
│   ├── config.py                 # 配置管理（Pydantic Settings）
│   ├── agent/
│   │   ├── deerflow.py           # LangGraph AI Agent 核心
│   │   ├── intent.py             # 意图识别（8 类）
│   │   └── risk_control.py       # 风险控制（注入检测 + 敏感词 + 违禁话术）
│   ├── api/
│   │   ├── chat.py               # 对话 API
│   │   ├── knowledge.py          # 知识库 CRUD + 上传
│   │   └── admin.py              # 管理后台 API（认证、租户、提示词、FAQ、质检）
│   ├── db/
│   │   ├── mysql.py              # SQLAlchemy 模型（8 张表）
│   │   ├── redis.py              # Redis 缓存操作
│   │   └── milvus.py             # Milvus 向量库客户端
│   ├── utils/
│   │   ├── document_loader.py    # 文档解析（PDF/DOCX/XLSX/MD/TXT）+ 分块
│   │   └── embedding.py          # Embedding 生成（OpenAI 兼容 + Redis 缓存）
│   └── wechat/
│       ├── client.py             # wxauto 微信客户端封装
│       ├── listener.py           # 消息监听 → AI → 回复桥接
│       └── mock_client.py        # 终端 Mock（macOS/Linux 开发用）
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── api/admin.js          # Axios API 封装
│       ├── components/
│       │   └── AdminLayout.vue   # 后台布局 + 侧边栏
│       ├── router/index.js       # 路由配置
│       └── views/
│           ├── dashboard/        # 工作台（统计图表）
│           ├── tenant/           # 租户管理
│           ├── knowledge/        # 知识库管理
│           ├── prompt/           # 提示词配置
│           ├── chat/             # 对话测试
│           ├── chatlog/          # 对话日志
│           ├── faq/              # FAQ 管理
│           └── review/           # 质检中心
└── tests/                        # 单元测试
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| AI Agent | LangGraph 0.2 + LangChain 0.3 |
| 大模型 | 阿里通义千问 qwen3.7-plus（DashScope OpenAI 兼容接口） |
| Embedding | text-embedding-v3（1024 维） |
| 向量数据库 | Milvus 2.4（IVF_FLAT 索引，COSINE 相似度） |
| 后端框架 | FastAPI 0.115 + Pydantic 2.9 |
| 数据库 | MySQL 8.0（SQLAlchemy 2.0 + aiomysql） |
| 缓存 | Redis 7（对话上下文 / Embedding 缓存 / 分布式锁） |
| 前端框架 | Vue 3.5 + Vue Router 4 + Element Plus 2.8 |
| 构建工具 | Vite 5.4 |
| 图表 | ECharts 5.5 |
| 认证 | JWT（HS256，24h 有效期）+ bcrypt |
| 微信集成 | wxauto（Windows 桌面自动化） |

---

## 管理后台功能

| 模块 | 路由 | 功能 |
|------|------|------|
| 工作台 | `/dashboard` | 统计概览：租户数、文档数、对话量、转人工率、Token 消耗、7 日趋势、意图分布 |
| 租户管理 | `/tenants` | 多租户 CRUD，每个租户独立的知识库、提示词、对话数据 |
| 知识库管理 | `/knowledge` | 文档上传（PDF/DOCX/XLSX/MD/TXT，10MB 限制）、自动向量化、按租户隔离 |
| 提示词配置 | `/prompts` | 每租户独立系统提示词，修改后实时生效 |
| 对话测试 | `/chat` | 浏览器内选择租户直接对话测试，无需微信环境 |
| 对话日志 | `/chatlogs` | 分页查询，支持租户/用户/日期/关键词筛选 |
| FAQ 管理 | `/faqs` | 常见问题 CRUD |
| 质检中心 | `/reviews` | 对话质量评分（1-5 分）、标记复查、质检统计 |

---

## API 接口

### 对话

```bash
curl -X POST http://localhost:8001/api/v1/jewelry/chat \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant_001",
    "channel": "web",
    "user_id": "user_001",
    "session_id": "session_001",
    "query": "3D硬金和足金有什么区别？"
  }'
```

### 知识库上传

```bash
curl -X POST http://localhost:8001/api/v1/jewelry/knowledge/upload \
  -F "tenant_id=tenant_001" \
  -F "category=product" \
  -F "@./knowledge.pdf"
```

### 管理员认证

```bash
curl -X POST http://localhost:8001/api/v1/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

---

## 配置说明

### 环境变量（.env）

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `APP_PORT` | 后端端口 | 8000 |
| `MILVUS_URI` | Milvus 地址 | http://milvus:19530 |
| `EMBEDDING_DIM` | 向量维度 | 1024 |
| `MYSQL_HOST` | MySQL 地址 | mysql |
| `REDIS_HOST` | Redis 地址 | redis |
| `LLM_MODEL` | 大模型名称 | qwen3.7-plus |
| `LLM_API_KEY` | DashScope API Key | （必填） |
| `LLM_BASE_URL` | DashScope 兼容接口 | https://dashscope.aliyuncs.com/compatible-mode/v1 |
| `EMBEDDING_MODEL` | Embedding 模型 | text-embedding-v3 |
| `MAX_CONTEXT_ROUNDS` | 上下文轮数 | 10 |
| `MANUAL_LOCK_MINUTES` | 转人工锁定时长（分钟） | 30 |

### 微信监听配置

| 变量 | 说明 |
|------|------|
| `WECHAT_API_URL` | 后端 API 地址 |
| `WECHAT_POLL_INTERVAL` | 消息轮询间隔（秒） |
| `WECHAT_WATCH_TARGETS` | 监听目标，格式：`聊天名称:租户ID:用户ID,...` |

---

## 微信监听

### Windows 真实模式

需要在 Windows 上运行微信桌面端：

```bash
pip install wxauto
python run_wechat_listener.py --chat-name "客户群"
```

### macOS/Linux Mock 模式

开发环境使用终端模拟：

```bash
python run_wechat_listener.py --mock
```

支持命令：
- 直接输入文字发送消息
- `/switch <聊天名称>` — 切换聊天对象
- `/status` — 查看当前状态
- `/quit` — 退出

---

## 测试

```bash
# 运行全部测试
pytest

# 运行指定测试
pytest tests/test_intent.py
pytest tests/test_risk_control.py
pytest tests/test_chat_api.py
```

---

## 端口参考

| 服务 | 端口 |
|------|------|
| 前端开发服务器 | 3000 |
| 后端 API | 8000（Docker）/ 8001（本地开发） |
| MySQL | 3306 |
| Redis | 6379 |
| Milvus gRPC | 19530 |
| Milvus Metrics | 9091 |

---

## License

MIT
