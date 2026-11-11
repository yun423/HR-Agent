# HR Agent - 智能人力资源管理系统

## 一、项目概述

HR Agent 是一个以**自然语言对话为核心交互方式**的智能 HR 管理系统。用户不需要在多个页面和菜单之间跳转，而是可以通过一个统一的 Agent 对话界面，用自然语言下达指令（如"帮我生成一个前端工程师的 JD"），系统自动理解意图、调度对应工具、执行任务并返回结果。

### 核心理念

- **对话即操作**：用户通过自然语言描述需求，AI Agent 自动路由到对应功能模块
- **工具编排**：Agent 作为"调度中心"，根据意图选择合适的工具（JD 生成、简历筛选、面试计划等）
- **确认即执行**：关键操作需要用户确认后才执行（如发送邮件），体现人机协作

---

## 二、技术架构

```
┌─────────────────────────────────────────────────────┐
│                     前端 (Vue 3)                      │
│   Element Plus  │  Pinia  │  Vue Router  │  ECharts  │
├─────────────────────────────────────────────────────┤
│                  REST API / SSE 流式                  │
├─────────────────────────────────────────────────────┤
│                 后端 (FastAPI + Python)               │
│                                                       │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐ │
│  │ Agent    │  │ Intent   │  │ RAG 检索增强       │ │
│  │ Service  │  │ Service  │  │ 向量搜索 + Rerank  │ │
│  └──────────┘  └──────────┘  └───────────────────┘ │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐ │
│  │ Skill    │  │ Dify     │  │ LLM Service        │ │
│  │ System   │  │ 工作流    │  │ (Qwen/通义千问)    │ │
│  └──────────┘  └──────────┘  └───────────────────┘ │
├─────────────────────────────────────────────────────┤
│          PostgreSQL + pgvector (向量存储)            │
└─────────────────────────────────────────────────────┘
```

### 技术栈

| 层级     | 技术                                          |
| -------- | --------------------------------------------- |
| 前端     | Vue 3, Vite, Element Plus, Pinia, ECharts     |
| 后端     | Python 3.10+, FastAPI, SQLAlchemy (异步)      |
| 数据库   | PostgreSQL + pgvector (向量搜索)              |
| AI 模型  | 通义千问 (Qwen-Max), text-embedding-v1        |
| 工作流   | Dify 工作流引擎                               |
| 向量检索 | LangChain + pgvector + Rerank (gte-rerank-v2) |
| 部署     | Docker + Docker Compose                       |

---

## 三、项目结构

```
hr-agent-study/
├── backend/                        # 后端 (FastAPI)
│   ├── main.py                     # 应用入口，FastAPI 生命周期
│   ├── requirements.txt            # Python 依赖
│   ├── Dockerfile / docker-compose.yml
│   ├── alembic.ini                 # 数据库迁移
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── api.py              # 路由聚合（16 个模块）
│   │   │   └── endpoints/          # 各模块 API 端点
│   │   │       ├── agent.py        # HR Agent 对话/流式接口
│   │   │       ├── auth.py         # 认证（JWT）
│   │   │       ├── users.py        # 用户管理
│   │   │       ├── chat.py         # 对话管理
│   │   │       ├── conversations.py
│   │   │       ├── documents.py    # 文档上传/管理
│   │   │       ├── knowledge_base.py
│   │   │       ├── knowledge_assistant.py
│   │   │       ├── job_description.py
│   │   │       ├── resume_evaluation.py
│   │   │       ├── interview_plan.py
│   │   │       ├── scoring_criteria.py
│   │   │       ├── exam_management.py
│   │   │       ├── email_configs.py
│   │   │       ├── hr_workflows.py  # HR 工作流
│   │   │       ├── intent_router.py # 意图路由
│   │   │       └── stats.py         # 统计
│   │   ├── core/                   # 核心配置
│   │   │   ├── config.py           # 全局配置 (Pydantic Settings)
│   │   │   ├── database.py         # PostgreSQL + pgvector 连接
│   │   │   ├── security.py         # JWT + OAuth2
│   │   │   └── middleware.py       # 自定义中间件
│   │   ├── models/                 # 数据库模型 (SQLAlchemy)
│   │   │   ├── user.py             # 用户 + 角色 (RBAC)
│   │   │   ├── conversation.py     # 对话 + 消息
│   │   │   ├── document.py         # 文档
│   │   │   ├── knowledge_base.py   # 知识库
│   │   │   ├── exam.py             # 试卷 + 试题
│   │   │   ├── exam_result.py      # 考试结果
│   │   │   ├── resume_evaluation.py # 简历评分
│   │   │   ├── email_config.py     # 邮箱配置
│   │   │   └── ...
│   │   ├── schemas/                # Pydantic 请求/响应模型
│   │   ├── services/               # 业务逻辑层
│   │   │   ├── agent_service.py    # HR Agent 核心编排
│   │   │   ├── agent_skills.py     # Skill 插件系统
│   │   │   ├── intent_service.py   # 意图分类
│   │   │   ├── llm_service.py      # LLM 调用封装
│   │   │   ├── rag_service.py      # RAG 检索增强
│   │   │   ├── embedding_service.py # 向量嵌入
│   │   │   ├── rerank_service.py   # 重排序
│   │   │   ├── dify_service.py     # Dify 工作流
│   │   │   ├── email_service.py    # 邮件发送
│   │   │   ├── exam_service.py     # 考试管理
│   │   │   └── ...
│   │   └── utils/                  # 工具函数
│   ├── skills/                       # Skill 插件目录
│   │   └── hr-agent-email/           # 邮件发送 Skill
│   │       ├── SKILL.md              # Skill 说明文档
│   │       ├── skill.json            # Skill 清单
│   │       ├── config.txt            # 邮箱配置
│   │       ├── scripts/              # Skill 执行脚本
│   │       └── references/           # 参考文档
│   ├── scripts/                    # 数据库管理、种子数据
│   └── uploads/                    # 文件上传目录
├── frontend/                       # 前端 (Vue 3 + Vite)
│   ├── src/
│   │   ├── api/                    # 接口请求封装 (Axios)
│   │   ├── views/
│   │   │   ├── agent/HRAgent.vue   # HR Agent 对话界面
│   │   │   ├── dashboard/          # 工作台
│   │   │   ├── recruitment/        # 智能招聘
│   │   │   │   ├── JDGenerator.vue       # JD 生成
│   │   │   │   ├── ResumeScreening.vue   # 简历筛选
│   │   │   │   └── SmartInterview.vue    # 智能面试
│   │   │   ├── training/           # 智能培训
│   │   │   │   ├── ExamGenerator.vue     # 试卷生成
│   │   │   │   ├── ExamManagement.vue    # 考试管理
│   │   │   │   └── AutoGrading.vue       # 自动阅卷
│   │   │   ├── assistant/          # 知识助理
│   │   │   │   ├── KnowledgeAssistant.vue # 知识问答
│   │   │   │   └── KnowledgeBase.vue     # 知识库管理
│   │   │   └── system/             # 系统管理
│   │   │       ├── UsersManagement.vue
│   │   │       ├── RolesManagement.vue
│   │   │       └── EmailManagement.vue
│   │   ├── router/index.js         # 路由配置
│   │   ├── stores/                 # Pinia 状态管理
│   │   └── layouts/                # 页面布局
│   └── package.json
```

---

## 四、核心模块

### 4.1 HR Agent（Agent 对话助手）

**入口文件**: `backend/app/services/agent_service.py`, `frontend/src/views/agent/HRAgent.vue`

HR Agent 是整个系统的"大脑"，采用 **ReAct（推理-行动）** 模式进行决策：

```
用户输入 → 意图分类 → ReAct 决策 → 工具调度 → 结果返回
                ↓
    ┌─────────────────────────────┐
    │  chat    → 普通对话回复      │
    │  use_tool → 调用业务工具     │
    │  ask_user → 追问缺失信息     │
    └─────────────────────────────┘
```

**关键设计**:

- **三层意图识别**：关键词快速匹配 → 附件上下文推理 → LLM 兜底分类
- **ReAct 决策**：LLM 在受限动作空间（chat/use_tool/ask_user）中选择下一步
- **工具注册表**：声明每个工具的意图、前置条件、对应路由
- **流式响应**：通过 Server-Sent Events (SSE) 实时推送执行进度
- **对话记忆**：支持上下文理解，处理"继续""刚才那个"等指代

**可调度的工具**:

| 工具          | 意图                 | 触发条件                     |
| ------------- | -------------------- | ---------------------------- |
| JD 生成       | `jd`                 | 提供岗位名称、地点等基本信息 |
| 简历批量筛选  | `resume_screening`   | 上传简历文件 + 选择匹配 JD   |
| 面试计划生成  | `interview_plan`     | 已有评分简历                 |
| 试卷生成      | `exam_generate`      | 上传参考文档 + 配置考试参数  |
| 资源删除      | `resource_delete`    | 指定要删除的资源类型和名称   |
| 邮件生成/发送 | `email_notification` | 通过 Skill 插件系统调度      |

### 4.2 智能招聘

**路由前缀**: `/recruitment/`

#### JD 生成 (`JDGenerator.vue`)

- 基于自然语言描述生成完整职位描述
- 同时自动生成配套的简历评分标准
- 流式输出生成内容
- 支持 JD 历史管理与导出

#### 简历筛选 (`ResumeScreening.vue`)

- 批量上传 PDF/DOC/DOCX 简历
- 基于 JD 自动评分和匹配度分析
- 支持手动调整评分、查看评分理由
- 依赖 Dify 工作流进行简历解析

#### 智能面试 (`SmartInterview.vue`)

- 根据候选人简历和 JD 自动生成面试方案
- 包含面试题目、考察维度、评分标准
- 支持与考试系统联动出题

### 4.3 智能培训/考试

**路由前缀**: `/training/`

#### 试卷生成 (`ExamGenerator.vue`)

- 上传参考文档（PDF/Word/TXT）自动生成试卷
- 支持配置题型、难度、分值、题量
- 流式生成，实时预览

#### 考试管理 (`ExamManagement.vue`)

- 试卷列表管理、搜索过滤
- 生成考试分享链接（无需登录）
- 查看考试结果与答题统计

#### 自动阅卷 (`AutoGrading.vue`)

- 客观题自动评分
- 考试成绩汇总与分析

### 4.4 知识助理

**路由前缀**: `/assistant/`

- **知识问答**：基于上传的知识库文档进行 RAG 问答
- **知识库管理**：创建/管理知识库、上传文档、自动向量化
- **混合检索**：向量相似度 + 文本匹配的融合排序
- **Rerank 重排**：使用 gte-rerank-v2 模型提升检索精度
- **查询增强**：自动改写用户查询以提升召回率

### 4.5 系统管理

**路由前缀**: `/system/`

- **用户管理**：用户 CRUD，支持搜索和分页
- **角色管理**：RBAC 权限控制（admin/hr_manager/hr_specialist/employee）
- **邮箱管理**：配置 IMAP/SMTP 邮箱，自动抓取简历邮件，定时调度

---

## 五、Agent Skill 插件系统

**核心文件**: `backend/app/services/agent_skills.py`

Skill 系统允许通过声明式配置扩展 Agent 的能力，无需修改核心代码。

### 工作原理

```
用户消息 "给候选人发邮件"
       ↓
Agent 识别意图: email_notification
       ↓
Skill Dispatcher 找到 hr-agent-email bundle
       ↓
执行 draft phase → 用户确认 → 执行 send phase
```

### Skill 结构

每个 Skill 是一个独立目录，包含：

```
backend/skills/<skill-name>/
├── SKILL.md         # Skill 描述 (YAML frontmatter)
├── skill.json       # 清单文件（声明 intent, phases, 执行脚本）
├── config.txt       # Skill 独立配置
└── scripts/         # 各阶段执行脚本
```

### skill.json 清单示例

```json
{
  "name": "hr-agent-email",
  "intent": "email_notification",
  "route": "/system/email-configs",
  "phases": ["draft", "send"],
  "default_phase": "draft",
  "confirmation_action": "send_email",
  "phase_scripts": {
    "draft": "scripts/email_draft.py:generate_email_draft",
    "send": "scripts/email_send.py:send_confirmed_email"
  }
}
```

### 已实现的 Skill

| Skill          | 意图                 | 阶段         |
| -------------- | -------------------- | ------------ |
| hr-agent-email | `email_notification` | draft → send |

---

## 六、AI 技术特性

### RAG 检索增强生成

- **文档向量化**：上传文档自动分块 → 通义千问 text-embedding-v1 向量化 → pgvector 存储
- **混合检索**：向量相似度 (70%) + 文本匹配 (30%)
- **Rerank 重排序**：gte-rerank-v2 模型对候选结果二次排序
- **查询增强**：自动扩展查询关键词，提升召回

### ReAct Agent 决策

- LLM 在受限动作空间中选择下一步
- 规则兜底（LLM 失败时使用关键词+附件规则）
- 每次决策输出 thought（推理摘要）供前端展示

### 意图分类

- 关键词快速匹配（毫秒级）
- 附件上下文推理
- LLM 兜底分类（备选）
- 支持 6 种预定义意图

### 对话记忆

- 基于 PostgreSQL 存储完整对话历史
- 传入 Agent 决策上下文，支持代词指代消解

---

## 七、数据模型 (ER 概要)

```
User (用户)
├── id, username, email, role, is_superuser
├── conversations → Conversation[]
│   └── messages → Message[]
├── documents → Document[]
└── roles → Role[] (多对多)

KnowledgeBase (知识库)
├── id, name, description, category
└── documents → Document[]

Document (文档)
├── id, filename, content, embedding (pgvector)
├── knowledge_base_id → KnowledgeBase
└── uploaded_by → User

Exam (试卷)
├── id, title, subject, difficulty, duration
└── questions → Question[]

EmailConfig (邮箱配置)
├── id, email, imap/smtp 配置
└── logs → EmailFetchLog[]

ResumeEvaluation (简历评分)
├── id, candidate_name, score
├── job_description_id → JobDescription
└── model_score_detail (JSON)
```

---

## 八、快速启动

### 环境要求

- Python 3.10+
- Node.js >= 16
- PostgreSQL 13+ (需启用 pgvector 扩展)
- Docker (可选)

### 1. 启动数据库

```bash
cd backend
docker compose up -d    # 启动 PostgreSQL + pgvector
```

### 2. 启动后端

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # 编辑 .env 填入 API Key
python scripts/seed_roles.py   # 初始化角色和默认用户
python main.py          # 启动 http://localhost:8000
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev             # 启动 http://localhost:3000
```

### 4. 访问

- 前端界面：`http://localhost:3000`
- API 文档：`http://localhost:8000/api/v1/docs`
- 默认账号：`testuser` / `test123`

---

## 九、关键配置项 (`.env`)

| 配置项                           | 说明                | 默认值              |
| -------------------------------- | ------------------- | ------------------- |
| `LLM_API_KEY`                    | 通义千问 API Key    | -                   |
| `LLM_MODEL`                      | 大语言模型          | `qwen-max`          |
| `EMBEDDING_MODEL`                | 嵌入模型            | `text-embedding-v1` |
| `QWEN_API_KEY`                   | Rerank 模型 API Key | -                   |
| `RERANK_ENABLED`                 | 是否启用 Rerank     | `true`              |
| `DIFY_BASE_URL` / `DIFY_API_KEY` | Dify 工作流配置     | -                   |
| `RAG_MIN_SIMILARITY_SCORE`       | RAG 最低相似度阈值  | `0.4`               |
| `CONTEXT_LIMIT`                  | 知识库检索文档数量  | `10`                |

