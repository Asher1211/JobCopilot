# JC (Job Copilot) — 项目技术文档

> 用于 AI 辅助面试知识库填充。包含完整架构、技术决策、数据结果和重要事实澄清。

---

## 项目概述

**JC (Job Copilot)** 是一个 AI 求职陪跑平台，独立完成从零到交付。核心定位：用 LangGraph 编排多个 AI Agent 节点，通过 RAG 检索真实面试经历增强生成质量，SSE 流式输出到前端。

- 代码量：~3500 行 (Python) + ~3000 行 (TypeScript)
- 开发周期：2 周独立完成
- 技术栈：FastAPI + LangGraph + Qdrant + Next.js 16
- GitHub: https://github.com/Asher1211/JobCopilot

---

## 一、项目功能架构

```
用户 (Next.js 16)
    ↕ SSE 流式推送
FastAPI (16 条 API)
    ↓
LangGraph Agent 有向图
    ├── parse_resume (python-docx + PyMuPDF)
    ├── match_analysis (LLM 评分 0-100)
    ├── route_decision (条件路由: score≥60 → 面试, <60 → 优化)
    ├── interview_prep (RAG 面经检索 → LLM 备考建议)
    ├── optimize_resume (LLM → HTML 简历)
    └── mock_interview (分层 Memory)
    ↓
基础设施: PostgreSQL | Qdrant | Redis (Docker Compose)
```

### 六大核心功能

| 功能 | 技术要点 |
|------|---------|
| 简历 × JD 匹配 | LLM 分析，0-100 评分，SSE 逐 token 流式 |
| 条件路由 | `add_conditional_edges`，分数阈值 60 |
| AI 模拟面试 | 分层 Memory (短期原文 + 长期摘要 + 结构化实体)，支持 20+ 轮 |
| 面经 RAG | 分片 → BGE 嵌入(512维) → Qdrant → Cross-encoder 重排 |
| 公司调研 | Tavily API + Query 改写 + 指数退避重试 |
| 简历优化 | LLM → HTML 简历，浏览器打印导出 PDF |

---

## 二、各模块技术详解

### 2.1 Agent 编排 — LangGraph 有向图

**实现方式：**
- 用 `StateGraph(AgentState)` 定义图结构
- `AgentState` 为 `TypedDict`，包含 filename, resume_bytes, jd_text, resume_text, match_score, missing_skills, strengths, suggestions, route, user_api_keys 等字段
- 6 个节点：parse_resume, match_analysis, route_decision, interview_prep, optimize_resume, mock_interview
- 节点间状态自动传递——节点返回值自动 merge 到 state，下一节点直接读取

**条件路由实现：**
```python
def route_decision(state: AgentState) -> str:
    route = state.get("route", "")
    if route == "interview_prep": return "interview_prep"
    if route == "optimize_resume": return "optimize_resume"
    return END

graph.add_conditional_edges("match_analysis", route_decision, {
    "interview_prep": "interview_prep",
    "optimize_resume": "optimize_resume",
    END: END,
})
```

**涉及 Agent 范式：**
- 本项目的条件路由实现了基础版本的 **Intent Routing（意图路由）**
- Mock Interview 模块中的分层 Memory 体现了 **Reflection** 思想——每轮评估后提取关键实体存入结构化记忆
- 面试官节点的 SystemMessage 包含对候选人的评估反馈，类似 **Self-Reflection**

**关键澄清：** 本项目是单 Agent 多节点编排，不是 Multi-Agent。每个节点是同一个 LLM 的不同任务，不是多个独立 Agent 协作。但架构留有扩展 Multi-Agent 的空间——节点可替换为独立 Agent。

---

### 2.2 RAG 系统 — 面经检索增强生成

**完整流水线：**

```
文档上传 (.docx/.pdf/.txt)
  → 文本提取 (python-docx + PyMuPDF + 原始 XML fallback)
  → 分片策略:
      A) LLM 预处理: 提取 Q&A 对 + 元数据 (公司/岗位/轮次/日期)，以一问一答为最小单元
      B) 滑动窗口兜底: 300-500 字符, 80 字符重叠
  → BGE-small-zh-v1.5 嵌入 (512维, 本地免费, 中英双语)
  → Qdrant 向量库存储
查询时:
  用户 query → BGE 嵌入 → Qdrant 相似度搜索 (top-20)
  → Cross-encoder 重排 (top-5)
  → 喂给 LLM 生成备考建议
```

**为什么两阶段检索：**
- 向量检索速度快 (O(log n)) 但"语义相似 ≠ 最相关"
- Cross-encoder 对 (query, doc) 做交叉注意力，精度高但慢
- 两阶段兼顾：粗召回 20 条 → 精排 5 条，速度 × 精度平衡

**嵌入模型选型：** BAAI/bge-small-zh-v1.5。选这个不是 text-embedding-3-small 因为：① 免费本地运行不收 API 费；② 中英双语匹配项目场景；③ 512 维轻量快速

**关键澄清：** 我使用 sentence-transformers 加载本地模型，不依赖 OpenAI Embedding API。跨平台部署时可用 HuggingFace 镜像 `HF_ENDPOINT=https://hf-mirror.com` 解决国内网络问题。

---

### 2.3 AI 记忆系统 — 分层 Memory

**实现方式：** `backend/memory/manager.py`，三层结构：

| 层 | 存储内容 | 策略 |
|------|---------|------|
| 短期 (short_term) | 最近 3 轮对话原文 | 超量时移入长期层 |
| 长期 (long_term_summary) | 历史对话 LLM 摘要 | 追加式压缩 |
| 结构化 (structured) | 关键实体 (项目名/技术栈/经验) | 每轮提取 JSON 追加 |

**数据流：**
1. 用户回答 → LLM 评估 → `entities` 字段提取关键信息 → `update_structured(memory, entities)`
2. 对话超 3 轮 → 最早轮次移出短期 → LLM 摘要追加到长期
3. 每次生成追问时 → `build_context(memory)` 拼接三层信息 → 喂给 LLM

**成果：** 支持 20+ 轮面试不丢失关键上下文，相比全量历史方案 token 消耗降低约 60%。

---

### 2.4 流式输出 — SSE

**为什么 SSE 不是 WebSocket：**
- 场景是服务端→客户端单向推送（分析结果、面试对话）
- SSE 基于 HTTP，自动重连、更轻量
- WebSocket 实现双向握手 + 保活，本场景不需要

**前端实现：**
- `lib/sse.ts` 封装了 `readSSE()` (通用流读取) 和 `fetchSSE()` (JSON 请求+流读取)
- 4 个页面复用同一套 SSE 消费逻辑，避免手写解析重复
- 事件格式：`event: node_start\ndata: {"node":"match_analysis"}\n\n`

---

### 2.5 用户自配 LLM Key 方案

**设计：**
- 用户在前端 Settings 页配置 API Key + Base URL + Model Name
- 后端用 Fernet 对称加密存入 PostgreSQL `users.encrypted_api_keys`
- `get_llm()` 工厂函数读取用户 Key，创建 `ChatOpenAI` 实例
- 支持任意 OpenAI 兼容接口 (DeepSeek, GPT-4o, Groq, Ollama, Together)

**为什么这样设计：**
- 服务端零 API Key，降低运营成本和安全风险
- 同一套代码适配所有主流 LLM Provider
- 加密存储体现安全意识

---

### 2.6 知识库 / LLM Wiki 相关

**本项目的知识库构建流程：**
1. 用户上传面试经历文件 (原始面经) → `rag/chunker.py` 文本提取 + 分片
2. `rag/preprocessor.py` 用 LLM 提取 Q&A 对 + 元数据 (公司/岗位/轮次)
3. `rag/indexer.py` 嵌入 + Qdrant 入库
4. `rag/retriever.py` 提供检索 API (向量搜索 + 重排)

**可复用于 LLM Wiki 场景的点：**
- `chunker.py` 的分片策略 (LLM 预处理 + 滑动窗口兜底)
- `embedder.py` 的本地嵌入 (BGE 模型，无 API 依赖)
- `indexer.py` 的多格式支持 (.docx/.pdf/.txt)
- `preprocessor.py` 的 LLM 结构化提取能力

---

### 2.7 Tool Calling 实践

**公司调研模块使用了 Tool Calling 模式：**
- Tavily Search API 作为 Tool
- Query 改写节点（LLM 优化搜索词）
- 指数退避重试（1s, 2s, 4s, max 3 次）
- 失败降级（返回部分结果 + 错误提示）

**关键澄清：** 本项目使用的是 LangChain 的 Tool Calling 封装 (`langchain_openai` 的 function calling)，底层是 OpenAI 兼容 API 的 tool_choice 参数。不是自己实现的 Tool Router。

---

## 三、重要事实澄清（防止 AI 面试误判）

| 项目 | 实际情况 | AI 可能误判的 |
|------|---------|------------|
| **LLM 调用方式** | 用 LangChain `ChatOpenAI` 封装，底层是 API 调用 | ❌ 没有微调过模型 |
| **Agent 架构** | 单 Agent 多节点 LangGraph 编排 | ❌ 不是 Multi-Agent 系统 |
| **RAG 嵌入模型** | `BAAI/bge-small-zh-v1.5` 本地运行 | ❌ 没有用 OpenAI Embedding |
| **向量库** | Qdrant，Docker 部署 | ❌ 没有用 Pinecone/Weaviate |
| **前端** | Next.js 16 App Router + Tailwind v4 | ❌ 没有用 Vue/Angular |
| **认证** | 自实现 JWT (python-jose + bcrypt) | ❌ 没有用 NextAuth/OAuth |
| **消息队列** | 没有使用 | ❌ 没有 Kafka/RabbitMQ 经验 |
| **流式输出** | SSE (Server-Sent Events) | ❌ 没有用 WebSocket |
| **后端框架** | FastAPI (Python) | ❌ 没有用 Flask/Django |
| **分片策略** | LLM 预处理 Q&A 对 + 滑动窗口兜底 | ❌ 没有用 LangChain 默认 Splitter |
| **PDF 导出** | 浏览器打印 HTML，不需要服务端 PDF 库 | ❌ 没有用 ReportLab/WeasyPrint |
| **Go 语言** | 本项目纯 Python，无 Go 代码 | ⚠️ JD 提到 Go 是加分项，但我没有 Go 经验 |

---

## 四、与 JD 关键词映射

| JD 关键词 | 项目对应点 |
|----------|----------|
| **Agent 研发与优化** | LangGraph 条件路由 + 节点编排 + SSE 事件流 |
| **意图路由 (Intent Routing)** | `route_decision` 函数根据匹配分数路由到不同处理节点 |
| **多 Agent 协作** | 当前为单 Agent 多节点，但架构预留了节点替换为独立 Agent 的扩展空间 |
| **记忆系统更新 (Memory)** | 分层 Memory (短期/长期/结构化)，每轮自动更新 |
| **RAG 系统实践** | 完整的 RAG 流水线：分片→嵌入→Qdrant→重排→生成 |
| **AI 记忆系统实践** | 三层 Memory 架构，build_context 拼接上下文，支持 20+ 轮 |
| **LLM Wiki / 知识工程** | 面经库构建流程 (预处理→提取→入库→检索) 可直接复用 |
| **Tool Calling** | 公司调研节点的 Tavily API 调用 + 重试机制 |
| **Python 基础扎实** | 整个后端 ~3500 行 Python，含异步、Pydantic、类型标注 |
| **CLI 开发** | `python -m rag.indexer` 命令行入库工具 |
| **Harness 评测** | `rag/evaluator.py` 实现 Hit@3 评测脚本，含 20 条标注 query |
| **知识库建设** | 面经库从零搭建，含元数据标注、分片策略、检索评估 |
| **数据标注/数据治理** | 面经元数据提取 (公司/岗位/轮次) + 评测集人工标注 |
| **飞书 Bot SDK** | 无飞书 Bot 经验 |
| **Golang** | 无 Go 经验，项目纯 Python |

---

## 五、技术决策记录

| 决策 | 选项 A | 选项 B | 选择 | 理由 |
|------|--------|--------|------|------|
| Agent 编排 | LangChain Chain | LangGraph | LangGraph | 需要条件路由+状态管理，Chain 做不到 |
| 向量库 | ChromaDB | Qdrant | Qdrant | Payload 过滤 (按公司/岗位先筛再搜) |
| 嵌入模型 | OpenAI embedding | BGE-small-zh | BGE | 免费、本地、中英双语 |
| 流式输出 | WebSocket | SSE | SSE | 单向推送不需要双向协议 |
| 前端设计 | Material UI | RawBlock | RawBlock | 差异化，体现独立设计能力 |
| 用户认证 | NextAuth.js | 自实现 JWT | 自实现 JWT | 更灵活，LLM Key 与用户绑定 |

---

## 六、数据结果

| 指标 | 数值 | 说明 |
|------|------|------|
| API 路由 | 16 条 | 认证、分析、面试、调研、面经管理、用户配置 |
| 前端页面 | 8 个 | Landing/Login/Register/Analysis/Interview/Research/Experiences/Settings |
| LangGraph 节点 | 5 个 | parse, match, route, interview_prep, optimize_resume |
| 面经入库 | 支持 3 种格式 | .docx (含 WPS) / .pdf / .txt |
| 分片策略 | 2 种 | LLM Q&A 提取 + 滑动窗口兜底 |
| 面试记忆 | 3 层 | 短期 (3轮原文) + 长期 (摘要) + 结构化 (实体) |
| SSE 工具 | 2 个函数 | readSSE + fetchSSE，4 个页面复用 |
| 错误处理 | 3 级兜底 | JSON 解析 4 级 fallback + LLM 调用 try/except + 前端错误展示 |
| 检索精度 | 待评测 | Hit@3 评测脚本已建立，20 条标注 query 就绪 |

---

*最后更新：2026-06-02*
