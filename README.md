# JC — AI 求职陪跑平台

> AI 驱动的求职陪跑平台：简历匹配、模拟面试、公司调研、面经检索。

## 项目介绍

JC (Job Copilot) 面向应届生/实习生求职群体，核心价值是降低求职过程中的信息不对称。用户上传简历和职位描述后，AI 自动分析匹配度、识别技能缺口、生成备考建议，并进行个性化模拟面试。

系统采用 **LangGraph 有向图**编排多个 AI Agent 节点，通过 **RAG（检索增强生成）** 从面经库检索真实面试经历提升回答质量，**SSE 流式输出** 实现逐 token 实时推送到前端。

### 解决的问题

| 痛点 | 解决方案 |
|------|---------|
| 不知道差距在哪 | 简历 × JD 智能匹配分析，0-100 评分 + 缺失技能 + 改进建议 |
| 不知道怎么准备 | RAG 面经库检索 + 公司调研 + 基于真实面经生成备考指南 |
| 面试表达不出来 | AI 模拟面试官，多轮对话实时评分，分层记忆支持 20+ 轮上下文 |

## 功能模块

| 功能 | 说明 |
|------|------|
| 简历 × JD 匹配 | 上传 .docx/.pdf + 粘贴 JD → LLM 评分(0-100)、缺失技能、优势、建议 |
| 条件路由 | 分数 ≥60 → 面试准备 + RAG 面经检索；分数 <60 → 简历优化 |
| AI 模拟面试 | 基于简历 + JD + 分析结果生成个性化面试，实时评分 + 追问，分层记忆 |
| 面经库 RAG | 上传面试经历 → 分片 → 嵌入 → Qdrant。LLM 预处理提取 Q&A 对 + 元数据 |
| 公司调研 | Tavily 联网搜索目标公司技术栈、面试风格、薪资范围 |
| 简历优化 | LLM 根据 JD 改写简历，导出排版美观的 HTML（可直接打印 PDF） |
| 用户自配 API Key | 支持 DeepSeek、OpenAI、Groq、Ollama 等任意 OpenAI 兼容接口，加密存储 |

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端框架 | FastAPI | 异步 Python，SSE 流式推送 |
| Agent 编排 | LangGraph | 有向图 + 条件路由 + 状态管理 |
| LLM 调用 | LangChain ChatOpenAI | 统一接口，兼容任意 OpenAI API |
| 嵌入模型 | BAAI/bge-small-zh-v1.5 | 本地免费，512 维，中英双语 |
| 向量数据库 | Qdrant | Payload 过滤 + 相似度检索 |
| 重排序 | cross-encoder/ms-marco | 召回 → 精排两阶段检索 |
| 关系数据库 | PostgreSQL | 用户、面试会话、加密 API Key |
| 文档解析 | python-docx + PyMuPDF | .docx（含 WPS 兼容）+ .pdf 自动分流 |
| 前端框架 | Next.js 16 + Tailwind CSS v4 | RawBlock 粗野主义设计系统 |
| 流式输出 | SSE | 比 WebSocket 更轻量的单向推送 |
| 用户认证 | JWT + bcrypt | 自实现，API Key Fernet 加密 |
| 容器化 | Docker Compose | PostgreSQL + Qdrant + Redis 一键启动 |

## 快速开始

### 环境要求
- Docker Desktop
- Python 3.11+
- Node.js 18+

### 启动步骤

```bash
# 1. 启动基础设施
docker compose up -d

# 2. 后端
cd backend
cp .env.example .env        # 填写 JWT_SECRET
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 3. 前端
cd frontend
npm install
npm run dev
```

打开 `http://localhost:3000`，在 Settings 页配置你的 LLM API Key，上传简历测试。

### 入库面经（可选）
```bash
cd backend
python -m rag.indexer /path/to/experiences.docx              # 滑动窗口分片
python -m rag.indexer /path/to/experiences.docx --preprocess  # LLM 提取 Q&A 对
```

## 系统架构

```
用户 (Next.js) ←→ SSE 流 ←→ FastAPI ←→ LangGraph Agent 图
                                           ├── parse_resume (文档解析)
                                           ├── match_analysis (LLM 评分)
                                           ├── route_decision (条件路由)
                                           ├── interview_prep (RAG → LLM 建议)
                                           ├── optimize_resume (LLM → HTML 简历)
                                           └── mock_interview (分层记忆)
                                    ↓
                    PostgreSQL (用户、会话、加密 Key)
                    Qdrant (面经向量库)
```

## 设计系统 — RawBlock

粗野主义风格，纯黑白，零圆角，粗边框替代阴影。

| 元素 | 值 |
|------|-----|
| 标题字体 | Archivo Black |
| 正文字体 | Work Sans → Noto Sans SC（中文） |
| 等宽字体 | Space Mono |
| 主色 | #000 / #FFF |
| 边框 | 3px / 5px |
| 圆角 | 0px |

## API（16 条路由）

```
POST /api/auth/register          POST /api/auth/login
GET  /api/auth/me                POST /api/analysis/match
POST /api/interview/start        POST /api/interview/chat/{id}
POST /api/research/search        POST /api/experiences/upload
POST /api/experiences/search     GET  /api/experiences/list
DELETE /api/experiences/chunks/{id}
GET  /api/user/config            POST /api/user/config
GET  /api/health
```

## 项目结构

```
job-copilot/
├── frontend/          # Next.js 16 前端 (7 个页面)
│   ├── app/           # analysis, interview, research, experiences, settings, auth
│   ├── components/    # top-bar, footer, file-input, form-field, password-input...
│   └── lib/           # auth, api, SSE 工具, 常量
├── backend/           # FastAPI + LangGraph 后端
│   ├── agents/        # 图定义 + 功能节点 (match, interview, optimize, research)
│   ├── api/routes/    # REST + SSE 端点
│   ├── rag/           # 分片、索引、检索、嵌入、预处理
│   ├── memory/        # 分层记忆管理 (短期/长期/结构化)
│   ├── models/        # SQLAlchemy 数据模型
│   ├── parsers/       # .docx + .pdf 文档提取
│   └── core/          # 配置、安全、加密
├── data/evals/        # 评测集
├── docker-compose.yml
└── 面试技术手册.md     # 技术面试准备文档
```

## 面试准备

如需技术面试准备，查看项目根目录的 [`面试技术手册.md`](./面试技术手册.md)，覆盖全部技术栈的含义、应用场景和选型理由。

## License

MIT
