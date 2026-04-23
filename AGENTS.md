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

## 架構決策（ADR）

> 記錄每個非顯而易見的選型決策。格式：背景 → 選項 → 決策 → 影響。

### ADR-001：不使用 LLM 框架

**狀態：** accepted

**背景：** AutoGen、LangGraph、CrewAI 都能快速搭建 multi-agent 系統。

**選項：**
- A：使用現有框架（快速上手，但黑盒）
- B：從 raw API 自己組

**決策：** 選 B。框架把 agent loop、tool dispatch、orchestration 都藏起來了，用框架等於跳過了這個專案最核心的學習目標。

**影響：** 程式碼量增加，但每一行都知道為什麼在那裡。

---

### ADR-002：Search Agent 使用靜態語料庫

**狀態：** accepted

**背景：** Research system 的 Search Agent 可以搜網路（即時）或搜本地語料庫（靜態）。

**選項：**
- A：串接 Web Search API（Brave / Serper）
- B：預先 index 靜態文件集，用 ChromaDB 語意搜尋

**決策：** 選 B。學習重點是部署架構，不是 Search Agent 的能力。靜態語料庫完全離線、無外部依賴，複雜度預算留給架構演化。

**影響：** 系統只能回答語料庫內的問題，定位是「文件問答系統」而非「通用研究工具」。

---

### ADR-003：開發期透過 Tailscale 存取 Mac mini Ollama

**狀態：** accepted

**背景：** Ollama 在 Mac mini，開發在 MacBook（SSH 進 Mac mini）。需要決定如何讓 script 連到 Ollama。

**選項：**
- A：SSH port forwarding
- B：Tailscale（已有）
- C：開放 LAN IP

**決策：** 選 B。Tailscale 已安裝、一直在線、不需手動建 tunnel，且不暴露到公開網路。設 `OLLAMA_HOST=0.0.0.0` 讓 Ollama 同時聽 localhost 和 Tailscale 介面，避免破壞 Echoforge 的 poll.py。

**影響：** 學習完成後移除 `OLLAMA_HOST` 設定，script 搬到 Mac mini 直接執行（同 Echoforge 模式）。

---

### ADR-004：加入 ChromaDB 作為向量資料庫

**狀態：** accepted

**背景：** 原始設計是純 stateless agent pipeline，沒有 DB 角色。

**選項：**
- A：維持無 DB 設計
- B：加入 ChromaDB

**決策：** 選 B。加入 DB 讓架構演化更有意義：v2b 的 K8s 部署會碰到 StatefulSet + PersistentVolumeClaim，這是 Deployment vs StatefulSet 最核心的差異，也是面試常問的概念。

**影響：** 每個部署版本都需要處理 ChromaDB 的有狀態性，複雜度可控且學習價值高。

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
**目前進度：** Branch 1 進行中

### 已完成
- [x] Branch 0：環境就緒
- [x] Branch 0.5：曳光彈（pipeline 走通，Search Agent 使用假資料）

### Branch 0 DoD：
- [x] Mac mini 上 Ollama 綁定 Tailscale 介面（`OLLAMA_HOST` 設為 Mac mini 的 Tailscale IP），`curl $OLLAMA_BASE_URL/api/tags` 從 MacBook 回傳正常
- [x] `.env` 建立（不進 git），填入 `OLLAMA_BASE_URL`；`.env.example` 作為範本進 git
- [x] `uv` 安裝完成，可建立 venv 並安裝 `httpx`
- [x] 一支測試腳本讀取 `OLLAMA_BASE_URL`，對 Ollama 送出 chat request 並拿到回應

### 下一步
- [ ] Branch 1：v1 Monolith 完整版（ChromaDB 語意搜尋 + ReAct pattern）

**連線架構（開發期）：**
```
MacBook → Tailscale → Mac mini ($OLLAMA_BASE_URL) → Ollama
```

**學習完之後的切換路徑：**
- Mac mini 上移除 `OLLAMA_HOST` 設定，Ollama 回到 `localhost` only
- Script 搬到 Mac mini 上直接執行（同 Echoforge poll.py 模式）
