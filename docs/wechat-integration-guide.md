# 微信交互与客户环境演示部署说明

本文说明本项目如何与微信交互、启动前需要配置哪些内容、`.env` 中各类配置的含义，以及如何在客户环境中做演示部署。

## 1. 整体架构

这个项目可以理解成两个服务加三个基础依赖。

两个服务：

```text
1. 后端 AI 服务：FastAPI
   负责知识库、聊天接口、管理后台接口、大模型调用。

2. 微信监听服务：run_wechat_listener.py
   负责操作微信桌面端，把微信消息转发给后端，再把后端回答发回微信。
```

三个基础依赖：

```text
MySQL   存租户、知识库文档记录、聊天日志、prompt 配置
Redis   存会话上下文、缓存、人工接管状态
Milvus  存知识库向量、用户历史记忆向量
```

完整消息链路：

```text
客户微信消息
  ↓
Windows 桌面微信
  ↓
wxauto 读取消息
  ↓
run_wechat_listener.py
  ↓
POST http://后端地址/api/v1/jewelry/chat
  ↓
FastAPI 后端
  ↓
查 Redis 上下文
  ↓
查 Milvus 知识库
  ↓
调用大模型
  ↓
返回回答
  ↓
run_wechat_listener.py
  ↓
wxauto SendMsg 发回微信
```

项目不是接入微信官方接口，也不是公众号或企业微信回调，而是通过 Windows 桌面微信自动化工具 `wxauto` 操作微信客户端。

核心代码位置：

- `src/wechat/client.py`：封装 `wxauto.WeChat`
- `src/wechat/listener.py`：微信监听器，负责轮询微信消息并调用后端 AI 接口
- `run_wechat_listener.py`：微信监听服务独立启动入口

## 2. 后端服务和微信监听服务的关系

后端服务负责“怎么回答”。

微信监听服务负责“怎么从微信拿消息、怎么把回答发回微信”。

二者通过 HTTP 接口连接：

```text
run_wechat_listener.py
  -> POST /api/v1/jewelry/chat
  -> FastAPI 后端返回 answer
  -> run_wechat_listener.py 发回微信
```

后端接口请求体大致是：

```json
{
  "tenant_id": "zh123",
  "user_id": "user_demo",
  "session_id": "zh123_user_demo_xxx",
  "query": "客户发来的微信消息",
  "channel": "wechat"
}
```

后端返回大致是：

```json
{
  "answer": "AI 客服回答",
  "need_manual": false,
  "manual_reason": "",
  "sources": ["知识库来源文件"]
}
```

## 3. `.env` 配置说明

`.env` 可以按用途分成几组。

### 3.1 应用服务配置

```env
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8001
DEERFLOW_ENV=dev
PROMPT_PATH=./config/jewelry_system_prompt.txt
```

说明：

| 变量 | 含义 |
| --- | --- |
| `APP_ENV` | 当前运行环境，通常是 `development` 或生产环境标识 |
| `APP_HOST` | 后端监听地址，`0.0.0.0` 表示允许局域网或容器访问 |
| `APP_PORT` | 后端 API 端口，本地开发常用 `8001`，Docker 部署常用 `8000` |
| `DEERFLOW_ENV` | Agent 运行环境标识 |
| `PROMPT_PATH` | 默认系统提示词文件路径，但当前主流程优先读取数据库里的租户 prompt |

### 3.2 Milvus 向量库配置

```env
MILVUS_URI=http://localhost:19530
MILVUS_USER=
MILVUS_PASSWORD=
MILVUS_COLLECTION_KNOW=jewelry_knowledge
MILVUS_COLLECTION_MEMORY=user_chat_memory
EMBEDDING_DIM=1024
```

说明：

| 变量 | 含义 |
| --- | --- |
| `MILVUS_URI` | Milvus 服务地址 |
| `MILVUS_USER` | Milvus 用户名，没有鉴权时留空 |
| `MILVUS_PASSWORD` | Milvus 密码，没有鉴权时留空 |
| `MILVUS_COLLECTION_KNOW` | 知识库向量集合名 |
| `MILVUS_COLLECTION_MEMORY` | 用户历史记忆向量集合名 |
| `EMBEDDING_DIM` | 向量维度，当前 `text-embedding-v3` 使用 `1024` |

Milvus 主要用于两类检索：

```text
1. 用户问题 -> embedding -> 搜索知识库 Top K
2. 用户问题 -> embedding -> 搜索历史聊天记忆
```

### 3.3 MySQL 配置

```env
MYSQL_HOST=localhost
MYSQL_PORT=3307
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DB=jewelry_ai
```

说明：

| 变量 | 含义 |
| --- | --- |
| `MYSQL_HOST` | MySQL 地址 |
| `MYSQL_PORT` | MySQL 端口 |
| `MYSQL_USER` | MySQL 用户 |
| `MYSQL_PASSWORD` | MySQL 密码 |
| `MYSQL_DB` | 数据库名 |

MySQL 存储业务数据，例如：

```text
租户
管理员账号
prompt 配置
知识库文档记录
聊天日志
FAQ
质检记录
```

### 3.4 Redis 配置

```env
REDIS_HOST=localhost
REDIS_PORT=6380
REDIS_PASSWORD=
REDIS_DB=0
```

说明：

| 变量 | 含义 |
| --- | --- |
| `REDIS_HOST` | Redis 地址 |
| `REDIS_PORT` | Redis 端口 |
| `REDIS_PASSWORD` | Redis 密码，没有密码时留空 |
| `REDIS_DB` | Redis DB 编号 |

Redis 主要存储短期状态：

```text
最近聊天上下文
问题结果缓存
embedding 缓存
租户 prompt 缓存
人工接管锁
```

### 3.5 大模型和 Embedding 配置

```env
LLM_MODEL=qwen3.7-plus
LLM_API_KEY=your-dashscope-api-key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v3
```

说明：

| 变量 | 含义 |
| --- | --- |
| `LLM_MODEL` | 聊天大模型名称 |
| `LLM_API_KEY` | 大模型 API Key |
| `LLM_BASE_URL` | OpenAI 兼容接口地址 |
| `EMBEDDING_MODEL` | 向量模型名称 |

注意：当前代码里聊天模型和 embedding 共用同一个 `LLM_API_KEY` 和 `LLM_BASE_URL`。

因此，如果把 `LLM_BASE_URL` 换成不支持 `text-embedding-v3` 的供应商，知识库检索会失败。当前推荐保持通义千问 DashScope 配置：

```env
LLM_MODEL=qwen3.7-plus
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v3
```

### 3.6 业务策略配置

```env
MAX_CONTEXT_ROUNDS=10
MANUAL_LOCK_MINUTES=30
KNOWLEDGE_TOP_K=3
KNOWLEDGE_STRONG_THRESHOLD=0.72
KNOWLEDGE_WEAK_THRESHOLD=0.50
```

说明：

| 变量 | 含义 |
| --- | --- |
| `MAX_CONTEXT_ROUNDS` | 保留多少轮上下文 |
| `MANUAL_LOCK_MINUTES` | 转人工后锁定 AI 自动回复的分钟数 |
| `KNOWLEDGE_TOP_K` | Milvus 知识库最多返回几条 |
| `KNOWLEDGE_STRONG_THRESHOLD` | 强命中阈值 |
| `KNOWLEDGE_WEAK_THRESHOLD` | 弱命中阈值 |

当前知识库命中策略：

```text
相似度 >= 0.72：
  强命中，作为强相关知识库内容传给 LLM。

0.50 <= 相似度 < 0.72：
  弱命中，只作为参考内容传给 LLM，并限制不能编造价格、库存、活动、政策、交期等业务信息。

相似度 < 0.50：
  未命中，不传知识库内容。

业务问题未命中：
  直接转人工。

通用问题未命中：
  允许 LLM 用通用知识回答。
```

业务问题示例：

```text
价格、库存、活动、优惠、保修、退换货、批发拿货、代理政策、交期、定制费用等。
```

通用问题示例：

```text
黄金怎么保养、18K 金和足金区别、钻石 4C、银饰为什么发黑、珍珠怎么存放等。
```

### 3.7 微信监听配置

```env
WECHAT_API_URL=http://localhost:8001
WECHAT_POLL_INTERVAL=2
WECHAT_MAX_RESPONSE_LEN=500
WECHAT_WATCH_TARGETS=客户A:zh123:user_a
```

说明：

| 变量 | 含义 |
| --- | --- |
| `WECHAT_API_URL` | 微信监听器调用的后端 API 地址 |
| `WECHAT_POLL_INTERVAL` | 轮询微信消息间隔，单位秒 |
| `WECHAT_MAX_RESPONSE_LEN` | 微信回复最大长度，超过会截断 |
| `WECHAT_WATCH_TARGETS` | 监听目标列表 |

`WECHAT_WATCH_TARGETS` 格式：

```text
微信聊天名称:租户ID:用户ID,微信聊天名称2:租户ID2:用户ID2
```

示例：

```env
WECHAT_WATCH_TARGETS=张三:zh123:user_zhangsan,客户群:zgs111:group_001
```

含义：

```text
监听微信里的“张三”
收到消息后，用租户 zh123 的知识库和 prompt 回答
这个客户在系统里的 user_id 是 user_zhangsan
```

## 4. 启动服务前需要准备什么

### 4.1 后端 AI 服务启动前

必须准备：

```text
Python 3.11+
MySQL
Redis
Milvus
大模型 API Key
.env 配置
```

如果要使用知识库问答，还需要：

```text
租户数据
租户 prompt
上传知识库文档
知识库向量化成功
```

### 4.2 微信监听服务启动前

真实微信模式必须准备：

```text
Windows 系统
微信桌面版已安装
微信账号已登录
wxauto 已安装
后端 API 可以访问
WECHAT_WATCH_TARGETS 已配置，或使用 --interactive 交互式添加
```

安装 wxauto：

```bash
pip install wxauto
```

macOS 或 Linux 只能使用 mock 模式做开发测试：

```bash
python run_wechat_listener.py --mock
```

## 5. 本地开发启动流程

### 5.1 启动基础服务

如果使用项目自带 Docker Compose：

```bash
docker compose up -d mysql redis milvus
```

### 5.2 配置 `.env`

本地开发常见配置：

```env
APP_PORT=8001

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root123456
MYSQL_DB=jewelry_ai

REDIS_HOST=127.0.0.1
REDIS_PORT=6379

MILVUS_URI=http://127.0.0.1:19530

LLM_MODEL=qwen3.7-plus
LLM_API_KEY=your-dashscope-api-key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v3

WECHAT_API_URL=http://127.0.0.1:8001
```

### 5.3 启动后端

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8001
```

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8001
```

健康检查：

```bash
curl http://127.0.0.1:8001/health
```

预期返回：

```json
{"status":"ok","channel":"wechat"}
```

依赖检查：

```bash
curl http://127.0.0.1:8001/readiness
```

### 5.4 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问：

```text
http://localhost:3000
```

### 5.5 Mock 微信测试

在 macOS/Linux 或不方便连接真实微信时：

```bash
python run_wechat_listener.py --mock --api-url http://127.0.0.1:8001
```

支持命令：

```text
直接输入文字：模拟客户发消息
/switch <聊天名称>：切换聊天对象
/status：查看当前状态
/quit：退出
```

## 6. 部署模式说明

项目支持两种常见演示或交付模式。

### 6.1 模式一：一体化本地演示

所有组件都部署在同一台 Windows 电脑上：

```text
Windows 电脑
  ├─ 微信桌面端
  ├─ wxauto
  ├─ run_wechat_listener.py
  ├─ FastAPI 后端
  ├─ MySQL
  ├─ Redis
  └─ Milvus
```

适用场景：

```text
客户现场临时演示
没有可用云服务器
希望所有服务离线或局域网内运行
```

优点是环境集中，缺点是客户电脑负载较重，并且基础服务也需要在客户电脑维护。

### 6.2 模式二：云端基础服务 + 客户 Windows 微信监听器

推荐正式演示和交付使用该模式。

云服务器部署：

```text
FastAPI 后端
前端管理后台
MySQL
Redis
Milvus
```

客户 Windows 电脑部署：

```text
微信桌面端
wxauto
run_wechat_listener.py
监听器运行所需 Python 依赖
```

整体交互链路：

```text
客户微信用户
  ↓
客户 Windows 电脑上的微信桌面端
  ↓ wxauto 读取消息
客户 Windows 电脑上的 run_wechat_listener.py
  ↓ HTTP 请求公网后端
云服务器 FastAPI: /api/v1/jewelry/chat
  ↓
云服务器 MySQL / Redis / Milvus / 大模型
  ↓
云服务器返回 AI 答案
  ↓ HTTP 响应
客户 Windows 电脑上的 run_wechat_listener.py
  ↓ wxauto SendMsg
客户 Windows 电脑上的微信桌面端回复用户
```

核心原则：

```text
后端在哪里都可以，只要微信监听器能访问它。
wxauto 必须和微信桌面端部署在同一台 Windows 机器上。
```

原因是 `wxauto` 操作的是本机 Windows 桌面微信窗口，不能直接远程操作另一台电脑上的微信客户端。

## 7. 云端部署 + 客户 Windows 监听器方案

### 7.1 云服务器部署内容

云服务器负责 AI 能力和数据存储：

```text
FastAPI 后端
Vue 管理后台
MySQL
Redis
Milvus
大模型 API 调用
知识库向量化
聊天日志存储
租户和 prompt 管理
```

云端建议绑定域名并配置 HTTPS，例如：

```text
https://ai.yourdomain.com
```

对微信监听器开放的核心接口：

```text
POST https://ai.yourdomain.com/api/v1/jewelry/chat
```

也可以临时使用公网 IP 演示：

```text
http://服务器公网IP:8000
```

正式环境建议使用 HTTPS 域名，避免客户网络、安全策略或浏览器混合内容限制带来的问题。

### 7.2 云服务器 `.env` 示例

云服务器 `.env` 重点配置后端、基础服务和模型：

```env
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000

MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-secure-password
MYSQL_DB=jewelry_ai

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

MILVUS_URI=http://milvus:19530
MILVUS_COLLECTION_KNOW=jewelry_knowledge
MILVUS_COLLECTION_MEMORY=user_chat_memory
EMBEDDING_DIM=1024

LLM_MODEL=qwen3.7-plus
LLM_API_KEY=your-dashscope-api-key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v3

MAX_CONTEXT_ROUNDS=10
MANUAL_LOCK_MINUTES=30
KNOWLEDGE_TOP_K=3
KNOWLEDGE_STRONG_THRESHOLD=0.72
KNOWLEDGE_WEAK_THRESHOLD=0.50
```

如果微信监听器不在云服务器上运行，云端 `.env` 里的 `WECHAT_*` 配置不是关键项；关键是云端后端接口必须能被客户 Windows 电脑访问。

### 7.3 云服务器启动步骤

拉取项目：

```bash
git clone git@github.com:zhaoguangshuai/customerServiceSystem.git
cd customerServiceSystem
```

复制并修改配置：

```bash
cp .env.example .env
```

启动基础服务和应用：

```bash
docker compose build
docker compose up -d
```

检查服务状态：

```bash
docker compose ps
```

检查后端：

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/readiness
```

如果使用 Nginx 或宝塔反向代理，建议将域名反代到：

```text
http://127.0.0.1:8000
```

### 7.4 云端演示数据准备

在管理后台完成：

```text
1. 创建或确认租户，例如 zh123
2. 配置租户系统 prompt
3. 上传知识库文档
4. 确认知识库向量化成功
5. 准备测试账号和测试问题
```

注意：业务问题依赖知识库命中。如果知识库为空或相似度过低，价格、库存、活动、售后政策等业务问题会转人工。

### 7.5 客户 Windows 部署内容

客户 Windows 电脑只负责微信收发，不需要部署 MySQL、Redis、Milvus 和完整后端。

客户电脑需要：

```text
Windows
微信桌面版，已登录演示微信号
Python 3.11
wxauto
微信监听器代码
能够访问云端后端 URL
```

可以部署完整项目代码，也可以只保留运行监听器所需文件：

```text
run_wechat_listener.py
src/wechat/
requirements.txt
.env
```

为了减少缺文件风险，演示阶段建议直接拉取完整项目。

### 7.6 客户 Windows `.env` 示例

客户 Windows 电脑的 `.env` 重点是微信监听配置。

如果云端使用域名：

```env
WECHAT_API_URL=https://ai.yourdomain.com
WECHAT_POLL_INTERVAL=2
WECHAT_MAX_RESPONSE_LEN=500
WECHAT_WATCH_TARGETS=客户微信昵称:zh123:user_demo
```

如果云端临时使用公网 IP：

```env
WECHAT_API_URL=http://服务器公网IP:8000
WECHAT_POLL_INTERVAL=2
WECHAT_MAX_RESPONSE_LEN=500
WECHAT_WATCH_TARGETS=客户微信昵称:zh123:user_demo
```

`WECHAT_WATCH_TARGETS` 含义：

```text
客户微信昵称：微信桌面端左侧聊天列表中的显示名称
zh123：云端系统中的租户 ID
user_demo：该客户在系统里的用户 ID
```

例如：

```env
WECHAT_WATCH_TARGETS=张三:zh123:user_zhangsan
```

表示监听微信里的“张三”，收到消息后调用云端后端，并使用租户 `zh123` 的知识库和 prompt 生成回答。

### 7.7 客户 Windows 启动监听器

安装依赖：

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install wxauto
```

确认微信桌面版已登录，并且聊天列表里能看到要监听的客户或群。

使用 `.env` 配置启动：

```powershell
python run_wechat_listener.py
```

或交互式添加监听对象：

```powershell
python run_wechat_listener.py --interactive --api-url https://ai.yourdomain.com
```

交互式输入示例：

```text
WeChat contact/group name: 张三
Tenant ID for '张三': zh123
User ID for '张三': user_zhangsan
```

### 7.8 云端交互示例

客户 Windows `.env`：

```env
WECHAT_API_URL=https://ai.yourdomain.com
WECHAT_WATCH_TARGETS=张三:zh123:user_zhangsan
```

当“张三”发微信消息：

```text
这个黄金手镯多少钱？
```

监听器请求云端：

```http
POST https://ai.yourdomain.com/api/v1/jewelry/chat
```

请求内容：

```json
{
  "tenant_id": "zh123",
  "user_id": "user_zhangsan",
  "session_id": "zh123_user_zhangsan_xxx",
  "query": "这个黄金手镯多少钱？",
  "channel": "wechat"
}
```

云端后端处理：

```text
根据 tenant_id=zh123 读取租户 prompt
搜索 zh123 的知识库
结合 Redis 上下文和 Milvus 用户记忆
调用大模型
返回回答
```

客户 Windows 监听器收到回答后，通过 `wxauto.SendMsg` 发回微信。

## 8. 一体化客户环境演示流程

如果没有云服务器，也可以把所有服务部署在客户 Windows 电脑上。

### 8.1 客户机器准备

必须安装：

```text
Windows
Docker Desktop
Python 3.11
微信桌面版
Git
```

Python 依赖：

```bash
pip install -r requirements.txt
pip install wxauto
```

### 8.2 拉取项目

```bash
git clone git@github.com:zhaoguangshuai/customerServiceSystem.git
cd customerServiceSystem
```

如果客户环境不能使用 SSH，可以改用 HTTPS 地址。

### 8.3 启动基础服务

```bash
docker compose up -d mysql redis milvus
```

确认服务：

```bash
docker compose ps
```

### 8.4 配置 `.env`

复制示例配置：

```bash
cp .env.example .env
```

一体化演示推荐配置：

```env
APP_PORT=8001

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root123456
MYSQL_DB=jewelry_ai

REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

MILVUS_URI=http://127.0.0.1:19530
MILVUS_USER=
MILVUS_PASSWORD=

LLM_MODEL=qwen3.7-plus
LLM_API_KEY=your-dashscope-api-key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v3

MAX_CONTEXT_ROUNDS=10
MANUAL_LOCK_MINUTES=30
KNOWLEDGE_TOP_K=3
KNOWLEDGE_STRONG_THRESHOLD=0.72
KNOWLEDGE_WEAK_THRESHOLD=0.50

WECHAT_API_URL=http://127.0.0.1:8001
WECHAT_POLL_INTERVAL=2
WECHAT_MAX_RESPONSE_LEN=500
WECHAT_WATCH_TARGETS=客户微信昵称:zh123:user_demo
```

### 8.5 启动后端

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8001
```

检查：

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8001/readiness
```

### 8.6 初始化演示数据

打开管理后台，创建或确认：

```text
租户，例如 zh123
租户 prompt
知识库文档
FAQ
```

上传知识库后，需要确认向量化成功。否则知识库检索没有数据，业务问题可能会转人工。

### 8.7 启动微信监听器

确认微信桌面端已登录，然后启动：

```bash
python run_wechat_listener.py
```

或使用交互式方式：

```bash
python run_wechat_listener.py --interactive
```

### 8.8 开始演示

用另一个微信给演示微信号发送消息。

监听器会：

```text
读取微信消息
调用本机后端 AI 接口
收到 AI 回复
把回复发送回微信
```

## 9. 运维和交付注意事项

### 9.1 微信聊天名称必须匹配

`WECHAT_WATCH_TARGETS` 中的 `chat_name` 必须和微信聊天列表显示名一致。

如果微信里叫：

```text
张三
```

配置就应该是：

```env
WECHAT_WATCH_TARGETS=张三:zh123:user_zhangsan
```

### 9.2 真实微信监听只能部署在 Windows

`wxauto` 依赖 Windows 桌面微信。

macOS/Linux 开发时使用 mock 模式：

```bash
python run_wechat_listener.py --mock
```

### 9.3 wxauto 必须和微信桌面端在同一台机器

`wxauto` 是桌面自动化工具，只能操作当前 Windows 登录会话里的微信窗口。

如果基础服务部署在云服务器，而微信登录在客户电脑，那么：

```text
wxauto 和 run_wechat_listener.py 必须部署在客户 Windows 电脑。
云服务器只提供后端 API。
```

### 9.4 不要随意切换不支持 embedding 的模型供应商

当前聊天模型和 embedding 共用：

```text
LLM_API_KEY
LLM_BASE_URL
```

如果 `LLM_BASE_URL` 换成不支持 `text-embedding-v3` 的供应商，知识库检索会失败。

### 9.5 业务问题未命中会转人工

当前策略下，价格、库存、活动、退换货、拿货、交期等业务问题，如果知识库相似度低于阈值，会转人工。

这是为了避免 AI 编造价格、库存和政策。

### 9.6 微信窗口和客户端版本可能影响自动化

真实微信接入本质是桌面自动化，不是官方 API，因此对以下因素敏感：

```text
微信是否已登录
微信客户端版本
聊天窗口名称
窗口是否可被 wxauto 操作
系统权限
```

### 9.7 网络连通性要求

云端部署时，需要确认：

```text
云服务器 -> DashScope API
云服务器 -> MySQL / Redis / Milvus
客户 Windows -> 云端 FastAPI 地址
客户 Windows -> 微信桌面端正常联网
```

一体化部署时，需要确认：

```text
客户 Windows -> DashScope API
客户 Windows -> 本机 Docker 基础服务
客户 Windows -> 本机后端端口
```

## 10. 演示前检查清单

### 10.1 云端基础服务检查

```text
1. 云服务器 Docker 服务已启动
2. MySQL / Redis / Milvus 已启动
3. FastAPI 后端已启动
4. 域名或公网 IP 可访问
5. /health 正常
6. /readiness 正常
7. LLM_API_KEY 有效
8. 管理后台能登录
9. 租户已创建
10. 租户 prompt 已配置
11. 知识库已上传并向量化
```

### 10.2 客户 Windows 监听器检查

```text
1. Windows 微信桌面端已安装并登录
2. Python 3.11 已安装
3. wxauto 已安装
4. run_wechat_listener.py 可运行
5. WECHAT_API_URL 指向云端后端
6. 客户 Windows 可以访问 WECHAT_API_URL
7. WECHAT_WATCH_TARGETS 的聊天名称和微信一致
8. run_wechat_listener.py 已启动
9. 另一个微信号可以发送测试消息
```

### 10.3 一体化演示检查

```text
1. Docker Desktop 已启动
2. MySQL / Redis / Milvus 已启动
3. .env 配置正确
4. LLM_API_KEY 有效
5. 后端 /health 正常
6. 后端 /readiness 正常
7. 管理后台能登录
8. 租户已创建
9. 租户 prompt 已配置
10. 知识库已上传并向量化
11. 微信桌面端已登录
12. WECHAT_WATCH_TARGETS 的聊天名称和微信一致
13. run_wechat_listener.py 已启动
14. 另一个微信号可以发消息测试
```

## 11. 总结

```text
后端负责“怎么回答”，微信监听器负责“从微信拿消息、把回答发回微信”。

云服务器负责大脑：
  FastAPI、管理后台、MySQL、Redis、Milvus、大模型调用、知识库。

客户 Windows 电脑负责手脚：
  微信桌面端、wxauto、run_wechat_listener.py。

.env 里的后端配置决定 AI 系统连接哪些数据库和模型；
.env 里的微信配置决定监听哪个微信聊天、把消息发给哪个后端。
```
