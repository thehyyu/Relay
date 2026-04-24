# Relay：用三種部署架構學習 Multi-Agent 系統

> 同一套業務邏輯，在 Python Monolith、Docker Compose 微服務、Kubernetes 三種環境下，架構會有什麼不同？

這是我給自己出的一道題。

---

## 為什麼做這個專案

我想學的不是「怎麼呼叫 LLM API」，而是**同一個系統在不同部署架構下，程式碼和基礎設施如何一起演化**。

所以我刻意把業務邏輯設計得極簡：一個能回答問題的 research agent，從語料庫搜尋文件、摘要、寫出答案。複雜度預算全部花在架構上。

另一個原則：**不使用任何 agent 框架**（AutoGen、LangGraph、CrewAI 都不用）。框架把 agent loop、tool dispatch、orchestration 都藏起來了，用框架等於跳過了最核心的學習目標。

---

## 系統是什麼

一個 multi-agent research pipeline，由四個 agent 組成：

| Agent | 職責 |
|---|---|
| **Orchestrator** | 接收問題，決定呼叫順序，整合最終輸出 |
| **Search Agent** | 語意搜尋 ChromaDB，回傳相關文件段落 |
| **Summarize Agent** | 將文件壓縮成結構化摘要 |
| **Write Agent** | 將摘要整理成可讀的最終回答 |

Orchestrator 用 **ReAct pattern**（Reasoning + Acting）驅動：LLM 透過 tool use 自行決定呼叫哪個 agent、用什麼參數，看到結果後再決定下一步。

```
問題進來
    ↓
[ITER 1] LLM → TOOL: search({"query": "k8s"})
[ITER 1] TOOL → LLM: ["Kubernetes 是開源的容器編排平台...", ...]

[ITER 2] LLM → TOOL: summarize({"documents": [...], "question": "..."})
[ITER 2] TOOL → LLM: "Kubernetes 是一個開源容器編排平台，用於..."

[ITER 3] LLM → TOOL: write_answer({"question": "...", "summary": "..."})
[ITER 3] TOOL → LLM: "Kubernetes（K8s）是..."

[ITER 4] LLM → FINAL: 最終答案
```

這個 log 是真實執行輸出，不是示意。LLM 自己決定走了 4 輪（比預期多一輪），在 ITER 4 確認一次才結束——這是 ReAct loop 的正常行為，也是為什麼需要 `MAX_ITER = 6` 安全閥。

---

## LLM 策略

- **v1 / v2**：Ollama 本地部署（Mac mini，qwen2.5:32b），完全免費，資料不出境
- **v3**（下一步）：Claude API，對比雲端 vs 本地 LLM 的選型差異

---

## v1：Monolith — 在一個 process 裡理解 agent loop

第一個版本是單一 Python script。四個 agent 都是函式，`dispatch()` 直接呼叫。

```python
def run_react_loop(question, dispatch, chat_fn):
    messages = [system_prompt, user_question]
    for i in range(MAX_ITER):
        msg = chat_fn(messages)          # 問 LLM
        if not msg.get("tool_calls"):
            return msg["content"]        # 有答案，結束

        for tc in msg["tool_calls"]:
            result = dispatch(tc["function"]["name"], tc["function"]["arguments"])
            messages.append({"role": "tool", "content": result})
    return "（超過最大迭代次數）"
```

**這一版最重要的體會**：LLM 不「執行」任何事，它只輸出一個 JSON 說「我想呼叫 search，參數是 `{"query": "k8s"}`」。真正執行的是外部的 `dispatch()`。這個分工讓 LLM 保持無狀態，副作用完全由外部控制。

Search Agent 用 ChromaDB + ONNX embedding 做語意搜尋，搜尋的是預先 index 好的靜態語料庫（軟體架構文件）。刻意選靜態語料庫，是因為學習重點在部署架構，不在 Search Agent 的能力。

---

## v2a：Docker Compose — 把函式切成獨立服務

第二版把四個函式各自包成 FastAPI 服務，用 Docker Compose 一鍵啟動。

**最核心的變化**：orchestrator 從直接呼叫 Python 函式，改成對其他容器發 HTTP POST。

```
v1：dispatch("search", args)           → 直接呼叫 Python 函式
v2a：POST http://search:8001/search    → 跨容器 HTTP 呼叫
```

服務間透過 Docker Compose 內部網路用 service name 互連，ChromaDB 資料用 volume mount 共享。

**踩到的坑**：ONNX embedding model（79MB）在容器啟動時才下載，orchestrator 呼叫 search 時 timeout。解法是用 FastAPI `lifespan` 在啟動時預熱，暖機完成再開始接流量。這個模式後來在 K8s 的 readiness probe 設計裡完全對應。

### Clean Architecture 重構（Branch 2a+）

進入 K8s 前，先把 orchestrator 拆層，展示 Dependency Rule：

```
orchestrator/
├── main.py      # FastAPI app + 路由
├── react.py     # ReAct loop，不 import httpx，不 import fastapi
└── clients.py   # 所有 HTTP 呼叫集中在這
```

`react.py` 的 `run_react_loop(question, dispatch, chat_fn)` 只接受 callable，完全不知道下游是 HTTP 還是直接函式。測試時直接傳 mock，不需要 `patch("httpx.post")`。

```python
# 測試：完全不啟動任何服務
def mock_dispatch(tool_name, args):
    return '["假的搜尋結果"]'

result = run_react_loop("測試問題", mock_dispatch, mock_chat_fn)
```

這個設計讓 K8s 的 retry、correlation ID 全部加在 `clients.py`，`react.py` 完全不動。

---

## v2b：Kubernetes — 遷移 minikube，遇到真實分散式系統的問題

把 v2a 遷移到 minikube 是最有收穫的一段。Docker Compose 掩蓋了很多假設，K8s 把它們全部暴露出來。

### Docker Compose → K8s 的概念對照

| Docker Compose | K8s | 差異 |
|---|---|---|
| 服務名稱（`search`） | Service（ClusterIP） | 概念相同，K8s 多了負載均衡 |
| `ports: "8000:8000"` | Ingress | K8s 可以根據路徑分流，不只是開 port |
| `environment:` | ConfigMap | 設定值獨立成資源，多個 Pod 共用 |
| `volumes:` | PVC | K8s 需要明確申請（Claim）儲存資源 |
| `depends_on:` | readinessProbe | Compose 只等容器啟動；K8s 等服務真正 ready |

**最重要的選型決策**：ChromaDB 用 StatefulSet，其餘三個服務用 Deployment。

```
Deployment：orchestrator-7f9b2-xkp3q 死掉 → orchestrator-7f9b2-mn4rs（新名字，無狀態）
StatefulSet：search-0 死掉               → search-0（同名字，PVC 自動重新掛上，資料不消失）
```

### 新增的三個分散式系統能力

**1. Liveness / Readiness Probe 分離**

兩個探針解決兩個不同問題：

```
livenessProbe  → /health/live  → 永遠 200，K8s 用來判斷「process 還活著嗎？」
readinessProbe → /health/ready → 暖機完成才 200，K8s 用來判斷「可以接流量嗎？」
```

search pod 啟動時，ChromaDB warmup 需要時間。這段時間 process 是活的（不該重啟），但還沒 ready（不該接流量）。兩個探針分開才能正確處理這個狀態。

**2. Retry with Exponential Backoff**

```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
async def call_search(query):
    ...
```

演練：`kubectl delete pod search-0` 刪掉 search pod，orchestrator 在 search 重啟期間（12 秒）自動重試，最終回傳正確答案，使用者端無感。

**3. Correlation ID 跨服務追蹤**

每個 request 分配一個 UUID，透過 `X-Request-ID` header 傳給所有下游，每個服務的 log 都帶這個 ID：

```
[432f82fa] START: 什麼是k8s?
[432f82fa] search: k8s          ← search pod log
[432f82fa] ITER 2 LLM → TOOL: summarize(...)
[432f82fa] DONE: Kubernetes (k8s) 是...
```

四個服務的 log 可以用同一個 ID grep 出完整的請求路徑，不需要任何額外工具。這是 Jaeger / Zipkin 等分散式追蹤系統的最簡版本，原理完全相同。

---

## 最深的一堂課：event loop 阻塞診斷

部署到 K8s 後，所有請求在第三輪 LLM 推論前後都回傳 `Empty reply from server`，pod 以 exit code 137 重啟。

關鍵診斷訊號藏在 `kubectl logs` 裡：

```
INFO: GET /health/ready 200 OK   ← request 前有 probe log
INFO: GET /health/ready 200 OK
[START: 什麼是k8s?]
[ITER 1] LLM → TOOL: search(...)
[ITER 2] LLM → TOOL: summarize(...)
[ITER 2] TOOL → LLM: (摘要結果)
← 此後完全沒有任何 probe log，直到 pod 被 kill
```

readiness probe 每 5 秒、liveness probe 每 10 秒都應該在 log 留下 access 記錄。它們全部消失，代表 **asyncio event loop 被阻塞**，uvicorn 無法處理任何新請求，包括 health check。K8s 誤判 pod 不健康，送 SIGKILL（exit 137）重啟。

原來的做法：

```python
# 理論上把阻塞工作丟到 thread pool，event loop 應該自由
loop = asyncio.get_event_loop()
answer = await loop.run_in_executor(None, react.run_react_loop, ...)
```

`run_in_executor` 的設計是讓 event loop 繼續跑，但在這個案例中 event loop 還是被阻塞了（推測是 sync httpx 在某些情況下 interact 回 asyncio event loop）。

**根本解法：全程 async**

```python
# clients.py：async def + httpx.AsyncClient
async def chat_fn(messages):
    async with httpx.AsyncClient() as client:
        response = await client.post(ollama_url, ...)
    return response.json()["message"]

# react.py：async def run_react_loop
async def run_react_loop(question, dispatch, chat_fn):
    msg = await chat_fn(messages)
    result = await dispatch(name, args)
    ...

# main.py：直接 await，移除 run_in_executor
answer = await react.run_react_loop(req.question, dispatch, chat_fn)
```

FastAPI 是 async 框架，HTTP 呼叫是 I/O 密集操作，本來就應該全程 async。`run_in_executor` 是讓舊有同步程式碼「勉強跑」的變通手段，不是正確設計。

**改完後**：LLM 推論期間（qwen2.5:32b 可能跑 2-3 分鐘）event loop 仍能正常回應 health probe，pod 不再被誤殺。

**帶走的心法**：診斷 event loop 是否阻塞，看 health probe 的 access log 在 request 期間是否消失。

---

## 架構演化總覽

```
v1 Monolith
  └── 單一 process，4 個函式，direct function call
  └── 學到：tool use、ReAct loop、ChromaDB 語意搜尋

v2a Docker Compose
  └── 4 個 FastAPI 容器，HTTP 呼叫，volume mount
  └── 學到：服務拆分、API 契約、容器化、冷啟動處理

v2b Kubernetes（現況）
  └── StatefulSet + PVC（有狀態）、Deployment（無狀態）
  └── 學到：probe 設計、retry、correlation ID、async 正確用法

v3 Hybrid（下一步）
  └── Serverless function + message queue + Claude API
  └── 學到：事件驅動、冷啟動取捨、雲端 LLM 選型
```

---

## 目錄結構

```
Relay/
├── v1/                    # Monolith 版本
│   ├── agents/            # orchestrator / search / summarize / write
│   ├── corpus/            # 靜態語料庫（.md 文件）
│   └── scripts/           # index_corpus.py（建立 ChromaDB index）
├── v2/                    # 微服務版本
│   ├── services/
│   │   ├── orchestrator/  # main.py + react.py + clients.py
│   │   ├── search/        # ChromaDB 查詢
│   │   ├── summarize/     # Ollama 摘要
│   │   └── write/         # Ollama 寫作
│   ├── k8s/               # K8s YAML（ConfigMap / Deployment / StatefulSet / Ingress）
│   └── docker-compose.yml
├── AGENTS.md              # 完整系統規格與 ADR
└── LEARNING.md            # 每個概念的學習筆記
```

---

## 關鍵設計決策（ADR 節錄）

| ADR | 決策 | 理由 |
|---|---|---|
| ADR-001 | 不用 LLM 框架 | 框架藏起 agent loop，跳過最核心的學習 |
| ADR-002 | 靜態語料庫 | 複雜度預算留給部署架構，不花在 Search 能力 |
| ADR-005 | FastAPI lifespan 預熱 ChromaDB | 把冷啟動成本移到啟動期，請求期零等待 |
| ADR-006 | ONNX model 打進 Docker image | 避免 K8s pod 每次重啟重新下載 79MB model |
| ADR-007 | 全程 async httpx | sync httpx 在 run_in_executor 阻塞 event loop，導致 liveness probe 失敗 |

---

## 本地執行

**v1 Monolith：**

```bash
cp .env.example .env   # 填入 OLLAMA_BASE_URL
uv venv && uv pip install -r v1/requirements.txt
python v1/scripts/index_corpus.py   # 建立 ChromaDB index（一次性）
python v1/main.py
```

**v2a Docker Compose：**

```bash
cd v2
docker compose up --build
curl -X POST localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "什麼是 event sourcing？"}'
```

**v2b Kubernetes（minikube）：**

```bash
minikube start --driver=docker
minikube addons enable ingress
eval $(minikube docker-env)

cd v2
docker build -t relay-search:v2b        services/search/
docker build -t relay-summarize:v2b     services/summarize/
docker build -t relay-write:v2b         services/write/
docker build -t relay-orchestrator:v2b  services/orchestrator/

kubectl apply -f k8s/
kubectl cp v1/chroma_db/. search-0:/data/chroma_db/   # 首次 seed 資料

# 在 cluster 內測試
kubectl run test-curl --image=curlimages/curl --rm -it --restart=Never -- \
  curl -X POST http://orchestrator:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "什麼是 Kubernetes？"}' \
  --max-time 300
```
