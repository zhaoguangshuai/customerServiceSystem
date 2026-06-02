# Ralph Fix Plan

## High Priority
- [x] Project scaffolding: Python backend structure, Docker setup, .env configuration
- [x] MySQL schema initialization: Create all 8 tables (tenant, user, product, faq, knowledge_document, chat_log, prompt_config, admin_user)
- [x] Milvus integration: Initialize jewelry_knowledge and user_chat_memory collections
- [x] DeerFlow agent pipeline: Implement the 12-step execution flow with LangGraph
- [x] RAG knowledge base: Document ingestion (PDF/Word/Excel/Markdown), vectorization, tenant-scoped retrieval
- [x] Unified chat API: POST /api/v1/jewelry/chat with tenant_id, user_id, session_id, query validation
- [x] Multi-turn memory: Load last 10 rounds of conversation context
- [x] Long-term user memory: Store/retrieve user conversation history from Milvus

## Medium Priority
- [x] Intent recognition: Classify queries (product inquiry, complaint, price negotiation, custom order)
- [x] Human handoff mechanism: 30-minute AI silence lockout, standard handoff message
- [x] Risk control rules: Prompt injection prevention, sensitive word detection, no-fake-pricing enforcement
- [x] Redis caching: Cache hot queries and session context
- [x] Admin backend API: Tenant CRUD, knowledge management, prompt config, chat logs, statistics
- [x] Vue3 admin frontend: Dashboard, tenant management, knowledge base UI, conversation logs, prompt editor
- [x] RBAC permission system: JWT auth, login/me endpoints, route guards, role-based token

## Low Priority
- [x] Data statistics: Chat volume, token usage, handoff rate analytics
- [x] Quality inspection: Chat log review and flagging
- [x] WeChat client integration: wxauto-based message listener with bridge to chat API
- [x] Monitoring and alerting: Health checks (/health liveness, /readiness with MySQL/Redis/Milvus checks)
- [x] Performance optimization: Embedding batch processing, query result caching

## Security & CRUD Improvements (New)
- [x] JWT auth on all admin endpoints: tenants, prompts, chat-logs, faqs, statistics, reviews
- [x] Tenant CRUD: add PUT /admin/tenants/{tenant_id} and DELETE /admin/tenants/{tenant_id}
- [x] FAQ CRUD: add PUT /admin/faqs/{faq_id} and DELETE /admin/faqs/{faq_id}
- [x] Frontend: TenantView edit/delete with dialog and popconfirm
- [x] Frontend: FaqView edit/delete with dialog and popconfirm
- [x] Frontend: admin.js API functions for updateTenant, deleteTenant, updateFaq, deleteFaq

## Completed
- [x] Project initialization
- [x] PRD analysis and Ralph configuration
- [x] Python backend scaffolding with FastAPI, SQLAlchemy, pymilvus
- [x] Docker + docker-compose setup (app, MySQL, Redis, Milvus)
- [x] MySQL models for all 8 tables
- [x] Milvus client with jewelry_knowledge and user_chat_memory collections
- [x] DeerFlow agent pipeline with LangGraph (12-step flow)
- [x] Unified chat API (POST /api/v1/jewelry/chat)
- [x] Intent recognition + risk control + human handoff
- [x] Redis caching for session context and prompt cache
- [x] Admin API (tenants, prompts, chat logs, FAQ, knowledge)
- [x] Document loader (PDF/Word/Excel/Markdown) with chunking + vectorization
- [x] Data statistics: Enhanced statistics API with daily trends, intent distribution, token/user stats, date range filtering
- [x] Chat log enhancements: total count, date range filter, keyword search, intent field persisted from agent
- [x] Dashboard with echarts: 7-day trend line chart, intent pie chart, real statistics API integration
- [x] Chat log UI: detail dialog, intent column, date range picker, keyword search
- [x] Quality inspection: Review fields (status/score/comment), review/flag endpoints, quality review UI with scoring and flagging

## Testing (New)
- [x] Intent classification tests (test_intent.py) - 13 test cases
- [x] Risk control tests (test_risk_control.py) - 18 test cases
- [x] Document loader tests (test_document_loader.py) - 9 test cases
- [x] Config/Settings tests (test_config.py) - 5 test cases
- [x] Chat API validation tests (test_chat_api.py) - 8 test cases
- [x] Admin JWT auth tests (test_admin_auth.py) - 7 test cases

## Production Readiness Fixes
- [x] Add logging infrastructure: replace silent exception swallowing with proper log statements in deerflow.py
- [x] Wrap synchronous Milvus calls in asyncio.to_thread to avoid blocking the event loop
- [x] Fix cache key collision: include session_id in cache key, switch from MD5 to SHA-256
- [x] Add query.strip() validation to reject whitespace-only queries
- [x] Add error handling around agent.chat() in chat.py endpoint
- [x] Fix multi-tenant auth bypass: add tenant_id check on knowledge delete endpoint
- [x] Actually delete Milvus vectors when removing knowledge documents
- [x] Sanitize Milvus filter expressions to prevent injection via special characters
- [x] Add flush() calls after Milvus inserts for immediate searchability
- [x] Add file type allowlist validation on knowledge upload
- [x] Add error logging on Milvus connection failure

## Notes
- **CRITICAL**: Only Phase 1 (WeChat private domain). No Douyin/Taobao/Kuaishou/Xiaohongshu code.
- Channel is always "wechat" - no other values supported.
- LLM and embedding models are configurable via .env (default: gpt-3.5-turbo + text-embedding-ada-002)
- Milvus embedding dimension: 1536
- Human handoff lockout: 30 minutes (configurable via MANUAL_LOCK_MINUTES)
- Context window: 10 rounds max (configurable via MAX_CONTEXT_ROUNDS)
