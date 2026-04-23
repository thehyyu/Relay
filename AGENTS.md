# Relay

**願景：** 一個 multi-agent research 系統，用來學習「同一套業務邏輯在三種部署架構下如何演化」。  
題目刻意保持簡單，讓複雜度預算全部花在架構上，不花在業務邏輯上。

---

## 核心概念

Agent 的最小定義：

```
system prompt + tools (function calling) + loop
```

Loop 的終止條件：

```
成功：LLM 回傳最終答案（無 tool call）
失敗：達到最大迭代次數，或工具回傳錯誤且無法繼續
```

Orchestrator 的最小定義：

```
一個 agent，它的 tools 是「呼叫其他 agent」
```

系統包含兩種元件：

```
無狀態：Orchestrator、Search Agent、Summarize Agent、Write Agent
有狀態：ChromaDB（語意搜尋語料庫）
```

不使用 AutoGen / LangGraph / CrewAI。從 raw API 自己組，才是架構學習的意義。

---

## Agent 組成

| Agent | 職責 |
|---|---|
| **Orchestrator** | 接收使用者問題，決定呼叫順序，整合最終輸出 |
| **Search Agent** | 將問題轉為 embedding，向 ChromaDB 做語意搜尋，回傳相關文件段落 |
| **Summarize Agent** | 將來源資料壓縮成結構化摘要 |
| **Write Agent** | 將摘要整理成可讀的最終回答 |

---

## 三個部署版本（學習主軸）

| 版本 | 部署方式 | LLM | 學到什麼 |
|---|---|---|---|
| **v1 monolith** | 單一 Python script | Ollama（Mac mini，免費） | tool use、agent loop、prompt 設計、ReAct pattern、ChromaDB 本地檔案存取 |
| **v2a microservices** | 每個 agent 是一個 FastAPI 服務，Docker Compose | Ollama（Mac mini，免費） | 服務拆分、API 契約、容器化、服務間通訊、ChromaDB 獨立容器 + volume mounting |
| **v2b K8s** | 同 v2a 遷移至 minikube | Ollama（Mac mini，免費） | Deployment / Service / Ingress、rolling update、**StatefulSet + PersistentVolumeClaim（ChromaDB）** |
| **v3 hybrid** | Orchestrator 容器化，短任務 agent 用 serverless | Claude API（付費，v3 才開始） | 事件驅動、message queue、冷啟動取捨、混合架構選型、有狀態與無狀態服務混合部署 |

每個版本完成後：一張架構圖 + 一份選型說明 + 一篇 README 文章，最後會把三個部署版本寫在同一份 README。

---

## LLM 策略

```
v1 + v2a + v2b  →  Ollama（Mac mini 已有，完全免費）
v3              →  Claude API（展示雲端 vs 本地 LLM 選型差異）
```

---

## Tech Stack

- **語言：** Python
- **套件管理：** `uv`
- **v1：** 純 Python script
- **v2a：** FastAPI + Docker Compose
- **v2b：** minikube（本地 K8s）
- **v3：** FastAPI 容器 + message queue（RabbitMQ / Redis）+ serverless（AWS Lambda 或 Azure Functions）
- **LLM v1-v2：** Ollama（Mac mini）
- **LLM v3：** Claude API
- **Vector DB：** ChromaDB（靜態語料庫，預先 index，embedding 由 Ollama 產生）

---

## 測試策略

**TDD 範圍：只測確定性邏輯，不測 LLM 輸出。**

| 可以 TDD | 不做 |
|---|---|
| Agent loop 終止條件 | LLM 回答品質 |
| Orchestrator routing 邏輯 | Agent 摘要準確度 |
| Tool call JSON parsing | Search 結果相關性 |
| v2a FastAPI endpoint contract | |

**CI（GitHub Actions）：** push 觸發 `ruff`（lint）+ `mypy`（型別）+ unit tests。全版本共用同一條 pipeline。

**CD：不做。** 每個版本的部署方式完全不同，部署步驟本身就是學習內容，自動化掉它反而失去意義。

---

## Branch DAG

```
Branch 0    環境就緒
    ↓
Branch 0.5  曳光彈（v1 最短路徑：問題進去，答案出來）
    ↓
Branch 1    v1 Monolith 完整版
    ↓
Branch 2a   v2 Microservices — Docker Compose
    ↓
Branch 2b   v2 K8s — 遷移至 minikube
    ↓
Branch 3    v3 Hybrid — 事件驅動 + Serverless + Claude API
    ↓
Branch 4    收尾：架構圖、README、blog 素材整理
```

---

## AI 協作守則

1. **最小修改原則：** 每次只做達成當前節點的最小修改，不動無關模組
2. **質疑新增：** 引入新 library 或建立新檔案前，必須先說明為何現有結構無法解決
3. **先求跑通，再求完美：** 重構是獨立任務，不在同一個 commit 內混做
4. **拒絕發散：** 一次 commit 只解一件事
5. **DoD 嚴格：** 所有 success criteria（含 REFACTOR）完成才算 done，不得跳過
6. **做中學：** 每引入新概念，先一句話說明它是什麼、為什麼用

---

## 當前狀態

**最後更新：** 2026-04-23  
**目前進度：** 規格確立，尚未開始開發

### 下一步
- [ ] Branch 0：環境就緒確認

**Branch 0 DoD：**
- [ ] Mac mini 上 Ollama 綁定 Tailscale 介面（`OLLAMA_HOST` 設為 Mac mini 的 Tailscale IP），`curl $OLLAMA_BASE_URL/api/tags` 從 MacBook 回傳正常
- [ ] `.env` 建立（不進 git），填入 `OLLAMA_BASE_URL`；`.env.example` 作為範本進 git
- [ ] `uv` 安裝完成，可建立 venv 並安裝 `httpx`
- [ ] 一支測試腳本讀取 `OLLAMA_BASE_URL`，對 Ollama 送出 chat request 並拿到回應

**連線架構（開發期）：**
```
MacBook → Tailscale → Mac mini ($OLLAMA_BASE_URL) → Ollama
```

**學習完之後的切換路徑：**
- Mac mini 上移除 `OLLAMA_HOST` 設定，Ollama 回到 `localhost` only
- Script 搬到 Mac mini 上直接執行（同 Echoforge poll.py 模式）
