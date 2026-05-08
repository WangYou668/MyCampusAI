# 智联校园 AI 助手

基于 **RAG（检索增强生成）** 的校园场景智能问答：PDF 入库与向量检索、大模型生成回答、对话会话持久化，配套 **React + TypeScript** 管理台式工作台。

| 后端 | 前端 |
|------|------|
| FastAPI · SQLAlchemy · ChromaDB | React 18 · TypeScript · Vite · TanStack Query |

---

## 功能一览

| 模块 | 说明 |
|------|------|
| 知识库 | PDF 上传 / 从 `./data` **重新索引**（`POST /kb/reingest`）；**同名文件再上传会先删旧向量**避免脏数据；**PyMuPDF 优先、PyPDF 回退** 抽字（`PDF_TEXT_BACKEND`）；文档列表、预览与下载 |
| 问答 | **宽向量召回 + Chroma 全文 `$contains` 混合检索**（可 `RAG_HYBRID` 关闭）；重排后仅取少量片段进模型；**图书馆/食堂等开放时间类问题**可走 **原文摘录**（`RAG_VERBATIM_HOURS`），减少数字被 LLM 改写；返回答案、`sources`、检索上下文 |
| 会话 | `GET/PUT/DELETE /sessions`，默认 SQLite（可通过 `DATABASE_URL` 使用 PostgreSQL 等） |
| 搜索 | 顶栏按关键词检索**已保存对话**标题与正文（`GET /search`） |
| 工作台 | 双栏（文档索引 + 对话）、文档管理、对话历史、外观设置；侧栏可收起、分栏可拖动；**对话区自动滚到底、参考资料/引用来源可展开收起** |

可选：设置环境变量 **`SERVE_FRONTEND=1`** 后，由 FastAPI 托管 `frontend/dist`，适合单机演示。

---

## 技术栈

| 层级 | 选型 |
|------|------|
| 后端运行时 | Python、Uvicorn |
| Web 框架 | FastAPI |
| 向量与嵌入 | ChromaDB；兼容 OpenAI 的 Embedding API（见 `.env.example`） |
| 关系数据 | SQLAlchemy；默认 SQLite `./data/app.db` |
| 文档解析 | **PyMuPDF（优先）+ PyPDF**；分块 + overlap 后批量入库 |
| 检索 | 向量 Top-K 池合并；可选 **问句子串 + `where_document` $contains`** 提升词面命中率（`RAG_VECTOR_FETCH`、`RAG_HYBRID`、`RAG_HYBRID_TERMS_MAX`） |
| 大模型 | HTTP 聊天补全；**默认 `CHAT_TEMPERATURE=0`**；少量片段进上下文（`CHAT_RAG_LLM_K`）；详见 `.env.example` |
| 前端 | React 18、TypeScript、Vite、TanStack Query、Axios |
| 代码质量 | ESLint、Prettier（见 `frontend/`） |

前端目录按 **Feature / Widget / Page** 分层，说明见 [`frontend/README.md`](frontend/README.md)。

---

## 快速开始

### 1. 准备环境

- Python 3.10+（建议）
- Node.js 18+（用于前端）

复制 **`.env.example`** 为 **`.env`**，至少填写 **`API_KEY`**。前后端分离开发时，建议配置 **`CORS_ORIGINS`** 包含前端地址，例如：

`http://127.0.0.1:5174,http://localhost:5174`

### 2. 启动后端（项目根目录）

**Windows（PowerShell）：**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

**macOS / Linux：**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

- OpenAPI：**http://127.0.0.1:8001/docs**
- 健康检查：**http://127.0.0.1:8001/health**

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

默认访问 **http://127.0.0.1:5174**（端口以终端输出为准）。开发态请求前缀 **`/api`**，由 Vite 代理到后端（见 `frontend/vite.config.ts` 中 `VITE_API_PROXY_TARGET`，默认 `http://127.0.0.1:8001`）。

生产构建：`cd frontend && npm run build`，部署与 `VITE_API_BASE_URL` 说明见 `frontend/README.md`。

---

## 主要 API（摘要）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查与模型信息 |
| GET | `/kb/stats`、`/kb/documents` | 片段统计、已入库文档列表 |
| POST | `/upload` | 上传 PDF 并建立索引 |
| POST | `/kb/reingest` | 从磁盘已有 PDF 重建索引 |
| GET | `/kb/file` | PDF 预览或下载 |
| POST | `/chat` | RAG 问答（`application/x-www-form-urlencoded`，字段 `query`） |
| GET/PUT/DELETE | `/sessions`… | 会话列表、详情、快照保存、删除 |
| GET | `/search`、`/api/search` | 搜索历史对话（Query：`q`） |

完整契约以 **`/docs`** 为准。

---

## 数据与仓库说明

- **`./data`**：上传的 PDF、默认 SQLite 数据库路径等（勿提交敏感数据）。
- **`./vector_db`**：Chroma 持久化目录。
- 上述目录已在 **`.gitignore`** 中忽略；密钥仅放 **`.env`**，勿提交。

---

## 常见问题

| 现象 | 处理 |
|------|------|
| 前端请求 404 | 确认浏览器请求是否到达 FastAPI；开发态检查 Vite 代理与后端端口；生产态检查 `VITE_API_BASE_URL` / 反代路径。 |
| `POST /kb/reingest` 404 | 重启 Uvicorn 以加载当前代码；`/health` 中可核对版本相关字段。 |
| CORS 报错 | 后端 `.env` 中 `CORS_ORIGINS` 包含前端 origin。 |
| 侧栏「最近对话」一直加载 | 需同时启动后端 **8001**；开发态前端走 Vite `/api` 代理到该端口。 |
| 问答数字与 PDF 不一致 | **重新索引** 同名 PDF（入库前会删旧向量）；开放时间类可走 **原文摘录** `RAG_VERBATIM_HOURS`；可调 `RAG_*`、`CHAT_TEMPERATURE` 等，见 `.env.example`。 |

---

![1778227828266](C:\Users\1023hfy\AppData\Roaming\Typora\typora-user-images\1778227828266.png)
