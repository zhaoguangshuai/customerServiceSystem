# Agent Build Instructions

## Project Setup

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- MySQL 8.0
- Redis 7+
- Milvus 2.4+

### Local Development

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy env file and configure
cp .env.example .env
# Edit .env with your API keys and database credentials
```

### Docker Deployment

```bash
# Build and start all services
docker-compose up -d --build

# Check service status
docker-compose ps

# View logs
docker-compose logs -f app
```

### Running the API Server

```bash
# Development
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Running the Frontend (Development)

```bash
cd frontend
npm install
npm run dev
# Frontend runs on http://localhost:3000, proxies /api to backend on :8000
```

### Building Frontend for Production

```bash
cd frontend
npm run build
# Output in frontend/dist/ - served automatically by FastAPI
```

### Running the WeChat Listener (Windows Only)

```bash
# Requires: Windows + WeChat desktop running + wxauto installed
pip install wxauto

# Option 1: Configure targets in .env, then run
python3 run_wechat_listener.py

# Option 2: Add targets interactively
python3 run_wechat_listener.py --interactive
```

**Environment variables for WeChat listener:**
- `WECHAT_API_URL` - FastAPI server URL (default: http://localhost:8000)
- `WECHAT_POLL_INTERVAL` - Seconds between message checks (default: 2)
- `WECHAT_MAX_RESPONSE_LEN` - Max AI response length (default: 500)
- `WECHAT_WATCH_TARGETS` - Comma-separated "chat_name:tenant_id:user_id" entries

### Default Admin Login

- Username: `admin`
- Password: `admin123`
- Auto-created on first app startup

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/jewelry/chat` | Unified chat API (WeChat only) |
| POST | `/api/v1/jewelry/knowledge/upload` | Upload knowledge document |
| GET | `/api/v1/jewelry/knowledge/list` | List knowledge documents |
| DELETE | `/api/v1/jewelry/knowledge/{doc_id}` | Delete knowledge document |
| POST | `/api/v1/admin/login` | Admin login (returns JWT) |
| GET | `/api/v1/admin/me` | Get current user info (JWT required) |
| GET | `/api/v1/admin/tenants` | List tenants |
| POST | `/api/v1/admin/tenants` | Create tenant |
| GET | `/api/v1/admin/prompts/{tenant_id}` | Get prompt config |
| PUT | `/api/v1/admin/prompts/{tenant_id}` | Update prompt config |
| GET | `/api/v1/admin/chat-logs` | List chat logs |
| GET | `/api/v1/admin/faqs` | List FAQs |
| POST | `/api/v1/admin/faqs` | Create FAQ |
| GET | `/api/v1/admin/statistics` | Dashboard statistics |
| GET | `/health` | Liveness check (always 200) |
| GET | `/readiness` | Readiness probe (checks MySQL/Redis/Milvus) |

### Database Initialization

```bash
# MySQL tables are auto-created via docker-compose init script
# Or manually:
mysql -u root -p < src/migrations/init.sql
```

### Milvus Collections

Auto-initialized on app startup:
- `jewelry_knowledge` - Knowledge base vectors (1536 dim)
- `user_chat_memory` - User conversation vectors (1536 dim)

## Project Structure

```
src/
├── main.py                 # FastAPI app entry point
├── config.py               # Settings from .env
├── api/
│   ├── chat.py             # POST /api/v1/jewelry/chat
│   ├── knowledge.py        # Knowledge document CRUD + upload
│   └── admin.py            # Admin API (auth, tenants, prompts, logs, FAQ, stats)
├── agent/
│   ├── deerflow.py         # DeerFlow pipeline (LangGraph 12-step flow)
│   ├── intent.py           # Intent recognition
│   └── risk_control.py     # Risk control rules
├── db/
│   ├── mysql.py            # SQLAlchemy models + session management
│   ├── milvus.py           # Milvus client wrapper
│   └── redis.py            # Redis caching utilities
├── utils/
│   ├── embedding.py        # OpenAI embedding API wrapper
│   └── document_loader.py  # PDF/Word/Excel/Markdown loader
├── wechat/
│   ├── __init__.py
│   ├── client.py           # wxauto WeChat desktop client wrapper
│   └── listener.py         # Message listener bridge to chat API
└── migrations/
    └── init.sql            # MySQL schema initialization

frontend/
├── package.json            # Vue3 + Element Plus + Vite
├── vite.config.js          # Dev server with API proxy
├── index.html
└── src/
    ├── main.js             # App entry
    ├── App.vue
    ├── api/admin.js        # API service layer (axios)
    ├── utils/
    │   ├── request.js      # Axios instance with JWT interceptor
    │   └── auth.js         # Pinia auth store
    ├── router/index.js     # Vue Router with auth guards
    ├── components/
    │   └── AdminLayout.vue # Sidebar + header layout
    └── views/
        ├── login/LoginView.vue
        ├── dashboard/DashboardView.vue
        ├── tenant/TenantView.vue
        ├── knowledge/KnowledgeView.vue
        ├── prompt/PromptView.vue
        ├── chatlog/ChatLogView.vue
        └── faq/FaqView.vue
```

## Key Learnings

- LangGraph nodes should return dicts (partial state updates), not full state objects
- Milvus IVF_FLAT index with COSINE metric works well for 1536-dim embeddings
- Redis caching for session context (10 rounds) and prompt config (1hr TTL)
- Document chunking: 500 chars with 50 char overlap for knowledge base

## Performance Optimizations

- **Embedding cache**: Redis-based cache (1hr TTL) for embedding vectors, keyed by MD5 hash of input text. Avoids recomputing embeddings for identical queries.
- **Query result cache**: Redis-based cache (5min TTL) for chat API responses. Caches non-handoff results keyed by tenant_id + query hash. Skips cache for handoff/manual-lock scenarios.
- **Batch embedding**: `get_embeddings()` checks cache per-text first, then batch-computes only uncached embeddings in a single API call.
- **Milvus batch insert**: Knowledge documents are inserted in a single batch call instead of one-by-one per chunk.

## Feature Development Quality Standards

### Testing Requirements

- **Minimum Coverage**: 85% code coverage ratio required for all new code
- **Test Pass Rate**: 100% - all tests must pass
- **Test Types Required**:
  - Unit tests for all business logic and services
  - Integration tests for API endpoints
  - End-to-end tests for critical user workflows

### Git Workflow Requirements

1. **Committed with Clear Messages**:
   ```bash
   git add .
   git commit -m "feat(module): descriptive message following conventional commits"
   ```

2. **Branch Hygiene**:
   - Work on feature branches, not directly on `main`
   - Branch naming: `feature/<name>`, `fix/<name>`, `docs/<name>`

3. **Ralph Integration**:
   - Update .ralph/fix_plan.md with new tasks before starting
   - Mark items complete in .ralph/fix_plan.md upon completion
