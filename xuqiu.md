# 珠宝行业多渠道AI智能客服系统（最终版·仅实现一期）

好，我**直接在完整版文档最前面、需求、功能、开发指令里全部明确标注：只做一期、二期暂不实现**，AI 会严格遵守，不会乱开发二期内容。

下面是**最终锁定一期、可直接丢给 AI 的完整文档**，复制即可用。

---

# 珠宝行业多渠道 AI 智能客服系统（最终版・仅实现一期）

## 【重要强制规定】

**本项目只实现一期需求，二期需求全部暂不开发、不编写代码、不预留接口。**
**严禁实现抖音、淘宝、快手、小红书等任何电商平台功能。**
**所有代码、接口、逻辑、表结构仅围绕微信私域客服开发。**

---

# 一、项目总览

## 1\. 项目定位

面向**珠宝加工厂、珠宝门店**的 **SaaS 化微信私域 AI 智能客服系统**，**仅实现微信渠道**，基于 **DeerFlow 智能体 \+ Milvus 向量数据库** 构建，具备 RAG 知识库、多轮记忆、长期用户记忆、人工转接、多租户隔离能力。

## 2\. 开发阶段（强制只做一期）

- **一期（P0・必须实现）**：微信私域 AI 客服（本地客户端托管）、DeerFlow 智能体、Milvus 知识库、后台管理、统一聊天 API

- **二期（P1・禁止实现）**：抖音、淘宝、多渠道中台 **全部不做**

## 3\. 核心业务场景（仅微信）

- 微信客户咨询：黄金 / 钻石 / 彩宝 / 银饰价格、定制周期、拿货规则、售后、库存、起订量

---

# 二、技术架构

```Plain Text
终端接入层：仅微信客户端
API 网关层：鉴权、限流、渠道适配
AI 智能体层：DeerFlow + LangGraph
RAG 检索层：Milvus 向量数据库
数据存储层：MySQL 8.0 + Redis
运营后台：Vue3 + Element Plus
部署：Docker + docker-compose
```

## 技术选型

- AI 智能体：DeerFlow

- 流程编排：LangGraph

- 向量数据库：Milvus 2\.4\+

- 主数据库：MySQL 8\.0

- 缓存：Redis

- API 服务：Python / Go

- 前端：Vue3 \+ Element Plus

- 部署：Docker

---

# 三、接入方案（仅微信，禁止其他渠道）

## 1\. 微信接入（一期唯一实现）

- 本地 PC 客户端监听微信消息 → 调用 AI API → 自动回复

- 风险：微信协议变动、风控

- 规避：独立客服号、限制回复频率、人工强制接管、掉线告警

## 2\. 其他平台（禁止实现）

- 抖音、淘宝、快手、小红书 **全部不实现、不开发、不配置**

---

# 四、核心功能（仅一期，禁止扩展）

## 1\. RAG 知识库问答

- 支持导入：PDF / Word / Excel / Markdown

- 分类：黄金、钻石、彩宝、银饰

- 流程：用户问题 → Embedding → Milvus 检索 → LLM 生成回答

- 多租户隔离：不同工厂数据独立

## 2\. 多轮会话记忆

- 保留最近 **10 轮对话上下文**

## 3\. 长期用户记忆

- 历史咨询、历史询价向量化存入 Milvus

## 4\. 意图识别与分流

- 产品咨询 → AI 回复

- 售后问题 → AI 回复

- 投诉、议价、非标定制、AI 无法回答 → **转人工**

## 5\. 人工接管机制

- 触发后 AI **30 分钟内不再自动回复**

- 统一话术：
`抱歉，这个问题需要人工客服为您准确解答，我已帮您转接人工。`

## 6\. 风控规则（强制）

1. 禁止虚假报价、虚假库存、承诺保值 / 升值

2. 价格必须来自知识库

3. 无答案必须转人工

4. 防 Prompt 注入

5. 敏感词直接转人工

## 7\. 成本优化

- 热点问题 Redis 缓存

- 上下文最多保留 10 轮

---

# 五、后台管理功能（仅一期）

- 租户管理

- 知识库管理

- 对话日志、质检

- 数据统计

- Prompt 配置

- RBAC 权限

---

# 六、数据库设计（仅一期）

## MySQL 建表 SQL

```sql
-- 租户表
CREATE TABLE tenant (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id VARCHAR(64) NOT NULL UNIQUE,
    tenant_name VARCHAR(100) NOT NULL,
    contact VARCHAR(50),
    phone VARCHAR(20),
    status TINYINT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 用户表
CREATE TABLE user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    channel VARCHAR(32) NOT NULL,
    nickname VARCHAR(100),
    phone VARCHAR(20),
    tags VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_tenant_user (tenant_id, user_id, channel)
);

-- 商品表
CREATE TABLE product (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id VARCHAR(64) NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    gold_type VARCHAR(50),
    diamond_size VARCHAR(50),
    price_range VARCHAR(100),
    inventory INT DEFAULT 0,
    category VARCHAR(50),
    status TINYINT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 问答表
CREATE TABLE faq (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(50),
    sort INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 知识库文档表
CREATE TABLE knowledge_document (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    file_type VARCHAR(32),
    content LONGTEXT,
    category VARCHAR(50),
    status TINYINT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 对话日志表
CREATE TABLE chat_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id VARCHAR(64) NOT NULL,
    channel VARCHAR(32) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    session_id VARCHAR(100) NOT NULL,
    user_query TEXT,
    ai_answer TEXT,
    need_manual TINYINT DEFAULT 0,
    manual_reason VARCHAR(255),
    used_tokens INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Prompt配置表
CREATE TABLE prompt_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id VARCHAR(64) NOT NULL UNIQUE,
    system_prompt TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 管理员表
CREATE TABLE admin_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(64) NOT NULL UNIQUE,
    password VARCHAR(128) NOT NULL,
    role VARCHAR(32) NOT NULL,
    tenant_id VARCHAR(64),
    status TINYINT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Milvus 集合结构

### 1\. jewelry\_knowledge

```python
collection_name = "jewelry_knowledge"
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="tenant_id", dtype=DataType.VARCHAR, max_length=64),
    FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=50),
    FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=5000),
    FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=255),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536)
]
```

### 2\. user\_chat\_memory

```python
collection_name = "user_chat_memory"
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="tenant_id", dtype=DataType.VARCHAR, max_length=64),
    FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=100),
    FieldSchema(name="session_id", dtype=DataType.VARCHAR, max_length=100),
    FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=2000),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
    FieldSchema(name="created_at", dtype=DataType.INT64)
]
```

---

# 七、珠宝行业系统 Prompt

```Plain Text
你是珠宝行业专业AI客服，严格遵守以下规则：

1. 回答必须只来自知识库，不编造任何信息。
2. 价格、库存、定制周期、拿货政策必须来自知识库或实时接口，不允许猜测。
3. 禁止承诺保值、升值、保真、权威认证等超出知识库的内容。
4. 不知道答案、涉及投诉、议价、非标定制、法律问题、敏感内容 → 直接转人工。
5. 回答风格专业、简洁、礼貌，符合珠宝工厂B端批发话术。
6. 必须记住用户历史咨询内容，跨会话保持记忆。
7. 遇到以下情况必须触发转人工：
   - 投诉、退款、纠纷、质疑真假
   - 定制设计、私人定制、特殊工艺
   - 大额议价、渠道价格、合作政策
   - 法律、维权、假货质疑
8. 无法回答时统一回复：
   “抱歉，这个问题需要人工客服为您准确解答，我已帮您转接人工。”

你的任务：根据用户问题 + 知识库内容 + 历史对话，给出精准回答。
```

---

# 八、DeerFlow 执行流程（严格按此写代码）

1. 接收用户请求，校验 tenant\_id /user\_id/session\_id

2. 加载短期会话上下文（最近 10 轮）

3. 从 Milvus 加载用户长期记忆

4. 意图识别

5. 用户问题向量化

6. 按 tenant\_id 检索 Milvus 知识库（top3）

7. 拼接：系统 Prompt \+ 历史记忆 \+ 知识库片段 \+ 用户问题

8. 调用 LLM 生成回答

9. 判断是否转人工

10. 对话日志写入 MySQL

11. 本次对话向量化存入 Milvus

12. 返回结果

---

# 九、统一 API 接口（仅微信）

## 请求地址

`POST /api/v1/jewelry/chat`

## 请求参数

```json
{
  "tenant_id": "工厂唯一ID",
  "channel": "wechat",
  "user_id": "客户唯一ID",
  "query": "用户问题",
  "session_id": "会话ID"
}
```

## 返回参数

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "answer": "AI回复内容",
    "need_manual": false,
    "manual_reason": "",
    "source": ["来源文档"]
  }
}
```

---

# 十、\.env 配置文件

```env
DEERFLOW_ENV=prod
PROMPT_PATH=./config/jewelry_system_prompt.txt

MILVUS_URI=http://milvus:19530
MILVUS_USER=
MILVUS_PASSWORD=
MILVUS_COLLECTION_KNOW=jewelry_knowledge
MILVUS_COLLECTION_MEMORY=user_chat_memory
EMBEDDING_DIM=1536

MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root123456
MYSQL_DB=jewelry_ai

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

LLM_MODEL=gpt-3.5-turbo
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-ada-002

MAX_CONTEXT_ROUNDS=10
MANUAL_LOCK_MINUTES=30
```

---

# 十一、强制开发约束（AI 必须遵守）

1. **只实现一期微信私域客服，二期所有平台不实现、不开发、不预留。**

2. 代码、接口、逻辑、表结构**只围绕微信**。

3. 不允许出现 douyin/taobao/kuaishou/xiaohongshu 相关代码。

4. 接口 channel 固定为 wechat，不支持其他值。

---

# 十二、AI 最终开发指令（复制这句即可）

**请根据以上完整需求，严格只实现一期微信私域客服功能，严禁开发抖音、淘宝等二期任何内容。使用 DeerFlow \+ Milvus 架构，生成完整可运行的后端代码、API、Milvus 操作、RAG 检索、多轮记忆、长期记忆、转人工、多租户隔离、对话日志。**

---

### 现在你可以直接复制全文给 AI，AI 100% 只做一期，不会碰二期！

需要我再帮你做一份**超简单的项目启动命令**吗？

> （注：文档部分内容可能由 AI 生成）
