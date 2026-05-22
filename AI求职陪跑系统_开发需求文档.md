# JC — AI求职陪跑系统 开发文档

> 本文档反映 2026-05-18 当前开发进度。技术栈、目录结构、环境变量均与代码仓库一致。

---

## 一、产品概述

**JC (Job Copilot)** — 面向求职者的 AI 陪跑平台，覆盖从简历匹配到模拟面试的完整链路。

| 痛点 | 对应功能 |
|------|---------|
| 不知道差距在哪 | 简历 × JD 智能匹配分析 |
| 不知道如何准备 | 面经库 RAG 检索 + 公司调研 |
| 面试表达不出来 | AI 模拟面试官 + 实时点评 |

---

## 二、当前功能状态

### 已完成 (Phase 1 + Phase 2)

| 模块 | 状态 | 说明 |
|------|------|------|
| 用户注册/登录 | ✅ | 邮箱+密码，JWT 鉴权，自定义实现（非 NextAuth） |
| 简历解析 | ✅ | .docx + .pdf，自动格式识别，含 WPS/中文 Word 兼容 |
| 简历 × JD 匹配分析 | ✅ | LangGraph 节点，SSE 流式输出，0-100 评分 + 缺失技能 + 建议 |
| LangGraph 条件路由 | ✅ | 分数 ≥60 → 面试准备；<60 → 简历优化（待 Phase 3 完善） |
| 面经 RAG 检索 | ✅ | 上传面经文件 → 分片 → 嵌入 → Qdrant；支持搜索 + 重排 |
| 公司调研 | ✅ | Tavily 联网搜索 + LLM 结构化报告 |
| 模拟面试 | ✅ | 多轮对话 + 实时评分 + 分层 Memory（短期/长期/结构化） |
| 用户自配 API Key | ✅ | 前端 Settings 页配置，加密存 PostgreSQL，支持任意 OpenAI 兼容接口 |
| 面经预处理 | ✅ | LLM 提取 Q&A 对 + 元数据（公司/岗位/轮次/日期），兜底滑动窗口分片 |
| 评测集 | ✅ | 20 条标注 query + Hit@3 评测脚本 |

### 待完成 (Phase 3)

| 模块 | 状态 |
|------|------|
| 简历优化 Agent（多版本生成+对比） | 待开发 |
| 备考计划生成 | 待开发 |
| 面试报告导出 PDF | 待开发 |
| 用户数据看板 | 待开发 |
| 每日调用次数限制（Redis） | 待开发 |
| 后台管理页面 | 待开发 |

---

## 三、技术架构

```
前端 (Next.js 16 + Tailwind CSS v4)
    ↕ SSE 流式
后端 (FastAPI + LangGraph)
    ├── 文档解析 (python-docx + PyMuPDF)
    ├── 匹配分析节点 (LLM)
    ├── 条件路由 (分数阈值)
    ├── 面试准备节点 (RAG 面经检索 → LLM 生成备考建议)
    ├── 公司调研节点 (Tavily + query 改写 + 重试)
    └── 模拟面试节点 (分层 Memory)
    ↓
基础设施
    ├── PostgreSQL (用户、面试会话、加密 API Key)
    ├── Qdrant (面经向量库)
    └── Redis (预留)
```

## 四、技术栈清单（与代码一致）

| 层级 | 技术 | 备注 |
|------|------|------|
| 后端框架 | FastAPI | 异步，SSE 流式 |
| Agent 编排 | LangGraph | 有向图 + 条件路由 |
| LLM 调用 | langchain-openai (ChatOpenAI) | 用户自配 Key，支持 DeepSeek/OpenAI/Groq/Ollama 等 |
| Embedding | BAAI/bge-small-zh-v1.5 | 本地免费，512 维，中英双语，通过 sentence-transformers 加载 |
| 向量数据库 | Qdrant (Docker) | payload 过滤 + 相似度检索 |
| 重排序 | cross-encoder/ms-marco-MiniLM-L-6-v2 | 应用启动时预热加载 |
| 关系数据库 | PostgreSQL (Docker, pgvector) | 用户、面试会话、加密 API Key |
| 文档解析 | python-docx + PyMuPDF | .docx（含 WPS 兼容）+ .pdf 自动分流 |
| 联网搜索 | Tavily API | 用户自配 Key，指数退避重试 |
| 前端框架 | Next.js 16 + Tailwind CSS v4 | SSE 消费、RawBlock 设计系统 |
| 认证 | 自定义 JWT (python-jose + bcrypt) | 用户自配 LLM Key，加密存 DB |
| 容器化 | Docker Compose | postgres + qdrant + redis |

---

## 五、设计系统：RawBlock

粗野主义 / 反设计风格，纯黑白配色，零圆角，无阴影，粗边框。

| 维度 | 值 |
|------|-----|
| 主色 | #000（黑）/ #FFF（白） |
| 强调色 | #0000FF（仅链接） |
| 标题字体 | Archivo Black |
| 正文字体 | Work Sans → 中文 Noto Sans SC |
| 等宽字体 | Space Mono |
| 圆角 | 0px（全部直角，radio 除外） |
| 边框 | 1px / 3px / 5px 粗边框替代阴影 |
| hover 反馈 | 完整颜色反转 |

---

## 六、前端页面

| 路由 | 页面 | 状态 |
|------|------|------|
| `/` | Landing | ✅ |
| `/auth/login` | 登录 | ✅ |
| `/auth/register` | 注册 | ✅ |
| `/analysis` | 简历 × JD 匹配分析 | ✅ |
| `/interview` | 模拟面试（需完成分析后进入） | ✅ |
| `/research` | 公司调研 | ✅ |
| `/experiences` | 面经库管理（上传/删除/搜索） | ✅ |
| `/settings` | 用户 API Key 配置 | ✅ |

### 共享组件

| 组件 | 用途 |
|------|------|
| `top-bar.tsx` | 顶部固定栏（logo + 导航 + 登录态） |
| `footer.tsx` | 底部固定栏 |
| `file-input.tsx` | 文件选择（隐藏原生控件） |
| `loading-indicator.tsx` | 加载指示器 |
| `form-field.tsx` | 表单字段封装 |
| `password-input.tsx` | 密码输入框（Show/Hide 切换） |
| `feature-card.tsx` | 首页功能卡片 |

### SSE 工具

| 文件 | 用途 |
|------|------|
| `lib/sse.ts` | `readSSE`（流读取）+ `fetchSSE`（JSON 请求+流读取） |

---

## 七、后端 API（当前全部路由 16 条）

```
POST   /api/auth/register
POST   /api/auth/login
GET    /api/auth/me
POST   /api/analysis/match           # SSE 流式匹配分析
POST   /api/interview/start          # 创建面试会话
POST   /api/interview/chat/{id}      # 面试对话
POST   /api/research/search          # 公司调研
POST   /api/experiences/upload       # 上传面经文件
POST   /api/experiences/search       # 搜索面经
GET    /api/experiences/list         # 列出所有面经chunk
DELETE /api/experiences/chunks/{id}  # 删除面经chunk
GET    /api/user/config              # 获取用户 API 配置
POST   /api/user/config              # 保存用户 API 配置
GET    /api/health
```

---

## 八、LangGraph 节点流程

```
START → parse_resume → match_analysis → route_decision
                                            ├── score ≥ 60 → interview_prep (RAG 面经 → LLM 备考建议)
                                            └── score < 60  → optimize_resume (待完善)
                                            ↓
                                           END
```

| 节点 | 功能 |
|------|------|
| parse_resume | docx/pdf 文本提取 |
| match_analysis | LLM 评分 + 缺失技能 + 优势 + 建议 |
| route_decision | 分数阈值条件分支 |
| interview_prep | RAG 面经检索 → LLM 生成备考指南 |
| optimize_resume | 简历优化建议（Phase 3 完善） |

---

## 九、面经 RAG 流水线

```
上传文件 (.docx/.pdf/.txt)
  → 提取纯文本
  → 分片策略:
      A) LLM 预处理: 提取 Q&A 对 + 元数据（公司/岗位/轮次/日期），一对 = 一个 chunk
      B) 滑动窗口兜底: 300-500 字符，80 字符重叠
  → BGE-small-zh-v1.5 嵌入 (512 维，本地免费)
  → 存入 Qdrant
  → 检索时: 向量搜索 (top-20) → cross-encoder 重排 (top-5)
```

---

## 十、分层 Memory（模拟面试）

| 层 | 策略 | 说明 |
|------|------|------|
| 短期 | 最近 3 轮原文 | 保证上下文连贯 |
| 长期 | 旧对话 LLM 摘要 | 不超过 token 窗口 |
| 结构化 | 提取关键实体 | 项目名、技术栈、经验 |

存储在 PostgreSQL `interview_sessions` 表中，支持会话恢复。

---

## 十一、项目目录结构（当前实际）

```
job-copilot/
├── frontend/
│   ├── app/
│   │   ├── analysis/page.tsx
│   │   ├── interview/page.tsx
│   │   ├── research/page.tsx
│   │   ├── experiences/page.tsx
│   │   ├── settings/page.tsx
│   │   ├── auth/login/page.tsx
│   │   ├── auth/register/page.tsx
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── top-bar.tsx
│   │   ├── footer.tsx
│   │   ├── file-input.tsx
│   │   ├── loading-indicator.tsx
│   │   ├── form-field.tsx
│   │   ├── password-input.tsx
│   │   └── feature-card.tsx
│   ├── lib/
│   │   ├── auth.tsx
│   │   ├── api.ts
│   │   ├── sse.ts
│   │   └── constants.ts
│   └── public/logo.png
├── backend/
│   ├── main.py
│   ├── agents/
│   │   ├── graph.py
│   │   ├── state.py
│   │   ├── llm.py
│   │   ├── nodes/
│   │   │   ├── parse_resume.py
│   │   │   ├── match_analysis.py
│   │   │   ├── interview_prep.py
│   │   │   ├── optimize_resume.py
│   │   │   ├── mock_interview.py
│   │   │   └── company_research.py
│   │   └── tools/tavily_search.py
│   ├── api/routes/
│   │   ├── auth.py
│   │   ├── analysis.py
│   │   ├── interview.py
│   │   ├── research.py
│   │   ├── experiences.py
│   │   └── user.py
│   ├── api/middleware/auth.py
│   ├── rag/
│   │   ├── chunker.py
│   │   ├── indexer.py
│   │   ├── retriever.py
│   │   ├── embedder.py
│   │   ├── preprocessor.py
│   │   ├── metadata_extractor.py
│   │   └── schema.py
│   ├── memory/manager.py
│   ├── models/
│   │   ├── base.py
│   │   ├── database.py
│   │   ├── user.py
│   │   └── interview.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── crypto.py
│   │   └── logging.py
│   ├── parsers/parser.py
│   └── requirements.txt
├── data/
│   └── evals/queries.json
├── docker-compose.yml
├── .env.example
└── logo.png
```

---

## 十二、环境变量 (.env.example)

```bash
# 关系数据库
DATABASE_URL=postgresql+asyncpg://jobcopilot:jobcopilot@localhost:5432/jobcopilot

# 向量数据库
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=interview_questions

# 监控 (可选)
LANGSMITH_API_KEY=
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=job-copilot

# 认证
JWT_SECRET=change-me

# CORS
CORS_ORIGINS=http://localhost:3000

# 限流 (预留)
DAILY_CALL_LIMIT=20
REDIS_URL=redis://localhost:6379
```

> **注意：服务端不存储任何 LLM API Key。** 用户通过前端 Settings 页自行配置（支持 DeepSeek/OpenAI/Groq/Ollama 等任意 OpenAI 兼容接口），加密后存储在 PostgreSQL `users.encrypted_api_keys` 字段。

---

## 十三、关键设计决策

1. **Embedding 选型** — `BAAI/bge-small-zh-v1.5`：中英双语，本地免费，512 维，无需外部 API
2. **LLM 由用户自配** — 服务端零 API Key，降低运营成本和安全风险
3. **面经库替代题库** — 题库模板价值低，改成真实面经入库，RAG 才有实际意义
4. **SSE 统一工具** — 4 个页面共享 `readSSE/fetchSSE`，避免手写解析重复出错
5. **预处理 + 滑窗双层分片** — LLM 提取 Q&A 对优先，滑窗兜底，保证任何格式面经都能入库
6. **分层 Memory** — 短期原文 + 长期摘要 + 结构化实体，支持 20+ 轮面试不丢失关键上下文

---

*文档版本：v2.0 | 更新时间：2026-05-18 | 与代码仓库当前状态一致*
