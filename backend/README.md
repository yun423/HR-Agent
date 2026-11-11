# HR Agent 后端 API

HR Agent 是一个基于人工智能的人力资源助手，提供智能问答、文档管理、知识库检索、面试计划和简历评估等功能。

## 技术栈

- **语言**: Python 3.10+
- **框架**: FastAPI, Dify工作流,  LangChain后端,  Vue3前端
- **数据库**: PostgreSQL + pgvector (向量搜索)
- **ORM**: SQLAlchemy (异步)
- **认证**: JWT + OAuth2
- **AI 模型**:
  - 通义千问 (Qwen)
- **容器化**: Docker
- **部署**: Docker Compose

## 功能特性

- 🔐 **用户认证与权限管理**
  - JWT Token 认证
  - OAuth2 密码流
  - 角色基础访问控制 (RBAC)
  - 用户注册、登录、个人信息管理
- 💬 **智能对话系统**
  - 基于大语言模型的对话
  - 对话历史管理
  - 流式响应支持
  - 上下文感知对话
- 📚 **知识库管理**
  - 文档上传与管理
  - 文本分割与向量化
  - 相似度搜索
  - RAG (检索增强生成) 技术
- 🧠 **知识助手**
  - 基于知识库的智能问答
  - 多路召回融合排序
  - 查询增强与重排
- 📝 **面试管理**
  - 面试计划制定
  - 候选人管理
  - 面试评估标准
- 📄 **简历评估**
  - 简历解析
  - 岗位匹配度分析
  - 自动化评分
- 📊 **考试管理**
  - 考试创建与管理
  - 题库管理
  - 在线考试
  - 自动评分
- 🔄 **Rerank功能**
  - 使用通义千问模型进行rerank操作
  - 提高搜索结果的相关性排序

## 项目结构

```
backend/
├── app/                     # 主应用目录
│   ├── api/                 # API 路由
│   │   └── v1/              # API v1 版本
│   │       ├── endpoints/   # API 端点
│   │       └── api.py       # API 路由聚合
│   ├── core/                # 核心配置
│   ├── models/              # 数据库模型
│   ├── schemas/             # 数据验证模型
│   ├── services/            # 业务逻辑
│   └── utils/               # 工具函数
├── scripts/                 # 脚本目录
├── tests/                   # 测试文件
├── uploads/                 # 上传文件目录
├── requirements.txt         # Python 依赖
├── Dockerfile               # Docker 配置
├── docker-compose.yml       # Docker Compose 配置
└── main.py                  # 应用入口
```

## 快速开始

### 环境要求

- Python 3.10+
- PostgreSQL 13+ (启用 pgvector 扩展)
- Docker & Docker Compose (可选)

### 安装PostgreSQL + pgvector

在 `docker-compose.yml` 所在目录下运行：

```bash
cd backend

docker compose up -d
```

查看容器状态：

> docker ps

输出应包含一个名为`hr_agent_postgres`的容器，状态为 Up。

验证 pgvector 安装成功：

> docker exec -it hr_agent_postgres psql -U hr_agent_user -d hr_agent

### 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 配置环境变量

创建 `.env` 文件:

```bash
cp .env.example .env
```
编辑 `.env` 文件配置变量

### 初始化数据库
```bash
python backend/scripts/seed_roles.py
```
会创建一个超级管理员账号testuser/test123

### 运行应用

```bash
# 开发模式
python main.py

# 或使用uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

访问 `http://localhost:8000/api/v1/docs` 查看 API 文档。

## API 文档

API 使用 OpenAPI/Swagger 文档自动生成。启动服务后访问:

- Swagger UI: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`

主要 API 端点:

### 认证相关
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/register` - 用户注册
- `GET /api/v1/auth/me` - 获取当前用户信息

### 用户管理
- `GET /api/v1/users/` - 获取用户列表
- `GET /api/v1/users/{user_id}` - 获取用户详情
- `PUT /api/v1/users/{user_id}` - 更新用户信息
- `DELETE /api/v1/users/{user_id}` - 删除用户

### 对话管理
- `GET /api/v1/conversations/` - 获取对话列表
- `POST /api/v1/conversations/` - 创建新对话
- `GET /api/v1/conversations/{conversation_id}` - 获取对话详情
- `DELETE /api/v1/conversations/{conversation_id}` - 删除对话

### 文档管理
- `POST /api/v1/documents/upload` - 上传文档
- `GET /api/v1/documents/` - 获取文档列表
- `GET /api/v1/documents/{document_id}` - 获取文档详情
- `DELETE /api/v1/documents/{document_id}` - 删除文档

### 知识库
- `POST /api/v1/knowledge-base/collections` - 创建知识库集合
- `GET /api/v1/knowledge-base/collections` - 获取知识库集合列表
- `POST /api/v1/knowledge-base/query` - 查询知识库

### 智能对话
- `POST /api/v1/chat/message` - 发送消息
- `POST /api/v1/chat/stream` - 流式发送消息

### 知识助手
- `POST /api/v1/knowledge-assistant/query` - 知识库问答

## 开发指南

### 代码结构

- `app/main.py` - 应用入口点
- `app/core/` - 核心配置和中间件
- `app/models/` - 数据库模型定义
- `app/schemas/` - Pydantic 数据验证模型
- `app/api/v1/endpoints/` - API 端点实现
- `app/services/` - 业务逻辑服务
- `app/utils/` - 工具函数

### 数据库迁移

使用 Alembic 进行数据库迁移:

```bash
# 生成迁移文件
alembic revision --autogenerate -m "migration message"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```


## 配置说明

应用配置在 `app/core/config.py` 中定义，可通过环境变量覆盖:

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `PROJECT_NAME` | "HR Agent" | 项目名称 |
| `DEBUG` | False | 调试模式 |
| `SECRET_KEY` | "your-secret-key-change-in-production" | JWT 密钥 |
| `DATABASE_URL` | "postgresql://username:password@localhost:5432/hr_agent" | 数据库连接URL |
| `LLM_API_KEY` | None | API 密钥 |
| `LLM_MODEL` | "qwen-max" | LLM 模型名称 |
| `EMBEDDING_MODEL` | "text-embedding-v1" | 嵌入模型名称 |

## Rerank功能

系统支持使用通义千问模型进行rerank操作，以提高搜索结果的相关性排序。

### 配置说明

本项目现在仅支持使用通义千问模型进行rerank操作。相关配置项如下：

1. `QWEN_API_KEY`: 通义千问API密钥，用于调用通义千问的API
2. `QWEN_MODEL`: 使用的通义千问rerank模型名称，默认为`gte-rerank-v2`
3. `RERANK_USE_QWEN`: 是否使用通义千问进行rerank，默认为`true`
4. `CONTEXT_LIMIT`: 上下文文档数量限制，默认为`5`

### 启用通义千问Rerank功能

要启用通义千问的rerank功能，请按以下步骤操作：

1. 确保您已经在.env文件中设置了`QWEN_API_KEY`：
   ```
   QWEN_API_KEY=your-qwen-api-key-here
   ```

2. 确保`RERANK_USE_QWEN`设置为`true`（默认已设置）：
   ```
   RERANK_USE_QWEN=true
   ```

3. 可选地，您可以指定要使用的通义千问rerank模型：
   ```
   QWEN_MODEL=gte-rerank-v2  # 或其他您想使用的rerank模型
   ```

### 配置上下文限制

您可以调整上下文文档的数量限制：

1. 在.env文件中修改`CONTEXT_LIMIT`的值：
   ```
   CONTEXT_LIMIT=15  # 将上下文限制设置为15个文档
   ```

2. 前端会自动从后端获取此配置值，无需手动同步。

   较大的值可以提高召回率，但可能会增加处理时间和成本。
   较小的值可以提高响应速度，但可能会遗漏一些相关文档。

### 使用的模型

通义千问提供了多种适用于不同场景的rerank模型，您可以根据需要选择合适的模型：

- `gte-rerank-v2`: 通用文本排序模型，适合大多数rerank任务（默认）
- `qwen3-rerank`: 基于通义千问3的文本排序模型，具有更强的语义理解能力

### 测试功能

您可以运行以下命令来测试通义千问的rerank功能：

```bash
cd backend
python scripts/test_qwen_rerank.py
```

注意：运行测试前请确保已正确设置环境变量。
