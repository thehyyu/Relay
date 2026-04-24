# Relay 學習筆記

> 這個專案的核心精神是**做中學**。每個工具或概念第一次出現時，這裡會記錄「它是什麼、為什麼用它、用完後的體會」。

---

## 學習目標

| 概念 | 學習狀態 | 對標企業場景 |
|---|---|---|
| Ollama 本地 LLM 呼叫 | ✅ 完成 | 私有部署、資料不出境的企業需求 |
| Tool use / function calling | ✅ 完成 | 所有 LLM agent 框架的底層機制 |
| Agent loop（ReAct pattern） | ✅ 完成 | AutoGen / LangGraph 的核心邏輯 |
| Orchestrator pattern | ✅ 完成 | 企業 AI workflow 編排 |
| 可觀察性（Observability）演進 | ✅ 完成 | 從 print 到雲端集中 logging 的路徑 |
| FastAPI 服務設計 | ✅ 完成 | 微服務 API 契約 |
| Docker Image 與容器化 | ✅ 完成 | 對標公司 Java WAR → Docker 遷移路徑 |
| Docker Compose 多服務編排 | ✅ 完成 | 本地模擬多容器環境 |
| Clean Architecture（Dependency Rule） | ✅ 完成 | Use Case 與 Infrastructure 解耦，提升可測試性 |
| K8s：Deployment / Service / Ingress | 🔄 進行中 | 企業容器編排標準 |
| K8s：rolling update / health check | 🔄 進行中 | 零停機部署 |
| K8s：Application-level HA（replicas + probe） | 🔄 進行中 | Pod 失效自動重建、流量切換 |
| DB 主從式架構（Primary-Replica） | 另立專案 | 客戶端備援設計最常被問的題目 |
| Message queue（RabbitMQ / Redis） | 未開始 | Azure Service Bus / AWS SQS / Kafka |
| Serverless function 觸發 | 未開始 | Azure Functions / Lambda |
| 冷啟動 vs 常駐容器取捨 | 未開始 | 架構選型面試必答題 |
| 雲端 LLM vs 本地 LLM 選型 | 未開始 | 隱私、成本、延遲三角取捨 |

---

## Ollama 本地 LLM 呼叫

**它是什麼：** 在本地跑開源 LLM 的工具，提供與 OpenAI 相容的 HTTP API。  
**為什麼用它：** v1/v2 完全免費，資料不離開本機，對標企業私有部署場景。  
**核心呼叫方式：**

```python
import httpx

response = httpx.post("http://mac-mini:11434/api/chat", json={
    "model": "qwen2.5:32b",
    "messages": [{"role": "user", "content": "..."}]
})
```

**學習後的體會：**  
Ollama 的 API 和 OpenAI 幾乎一樣，`/api/chat` 接收 messages array，回傳 message 物件。真正的差異在部署：OpenAI 是呼叫遠端 API，Ollama 是呼叫本機 HTTP server。`stream: false` 讓 response 一次回來，適合 agent 場景（需要完整回應才能決定下一步）。

---

## Tool use / function calling

**它是什麼：** LLM 宣告它想呼叫哪個工具、帶什麼參數，由外部程式執行後再把結果還給 LLM。  
**為什麼用它：** Agent 能力的核心 — 讓 LLM 從「輸出文字」變成「執行動作」。  
**學習後的體會：**  
LLM 不會「執行」任何事，它只是輸出一個 JSON 說「我想呼叫 `search`，參數是 `{"query": "docker 部署 vs k8s 部署 決定因素"}`」。真正執行的是外部的 `dispatch()` 函式。這個分工讓 LLM 保持無狀態，副作用由外部程式控制 — 這也是為什麼 tool use 可以呼叫資料庫、API、甚至其他 agent，而 LLM 本身完全不需要改動。

---

## Agent loop（ReAct pattern）

**它是什麼：** Reasoning + Acting 的迴圈：LLM 思考 → 決定呼叫工具 → 看結果 → 再思考，直到任務完成。  
**為什麼用它：** 這是所有 agent 框架（AutoGen、LangGraph）的底層邏輯，自己實作一次才真正理解框架在做什麼。  
**學習後的體會：**  
真正執行後才發現 LLM 走了 **4 輪**才完成一個問題（見下方真實 trace）。第 4 輪的 `LLM → FINAL` 內容和第 3 輪 TOOL 的輸出幾乎一樣，代表 LLM 有時會多繞一圈確認。`MAX_ITER = 6` 的安全閥設計也因此顯得必要：若 LLM 陷入迴圈，不會無限執行。AutoGen / LangGraph 底層在做的就是這個 while loop，只是加了更多錯誤處理和狀態管理。

---

## Orchestrator pattern

**它是什麼：** 一個 agent 負責把任務分派給其他 agent，收集結果後整合輸出。  
**為什麼用它：** 單一 agent 做所有事會讓 prompt 爆炸複雜，拆開職責讓每個 agent 的 prompt 保持簡單。  
**學習後的體會：**  
Orchestrator 自己不做任何「內容工作」，它只負責決定順序和傳遞資料。真實執行時，它依序呼叫了 search → summarize → write_answer，每個 agent 的輸出成為下一個 agent 的輸入。這個資料流的設計讓每個 agent 的 prompt 只需要專注一件事，不需要在一個 prompt 裡同時做搜尋、摘要和寫作，避免 prompt 過長導致 LLM 表現下降。

---

## 可觀察性（Observability）演進

**它是什麼：** 能看到系統內部「正在發生什麼」的能力。對 agent 系統來說，就是能追蹤 LLM 每一輪的決策和 tool 呼叫。

**為什麼重要：** Agent loop 是非同步的黑盒子；沒有 observability，debug 和優化都無從下手。

### 各部署版本的 logging 方式

| 版本 | 機制 | 指令 | 對標企業場景 |
|---|---|---|---|
| v1（直接執行） | `print()` 到 stdout | 直接看終端機輸出 | 最簡單，開發階段快速驗證 |
| v2a（Docker Compose） | container stdout | `docker compose logs -f orchestrator` | 本地多服務同時追蹤 |
| v2b（K8s） | pod stdout | `kubectl logs -f deployment/orchestrator` | 多副本時可指定 pod 或 follow deployment |
| v3（Serverless） | 雲端集中 logging | CloudWatch / Azure Monitor | 多 function 跨服務統一查詢、設 alert |

### Log 格式設計原則

格式在所有版本保持一致，只有**收集位置**不同：

```
[ITER N] LLM → TOOL: tool_name(args)
[ITER N] TOOL → LLM: result_preview
[ITER N] LLM → FINAL: answer_preview
```

`[ITER N]` 前綴讓你一眼看出 loop 走了幾輪，不需要 IDE debugger。

### 真實執行 Trace（Branch 1）

問題：「我該如何判斷我應該用 docker 部署或是 k8s 部署」

```
[ITER 1] LLM → TOOL: search({"query": "docker 部署 vs k8s 部署 決定因素"})
[ITER 1] TOOL → LLM: ["Kubernetes（K8s）是開源的容器編排平台...", "| 面向 | 單體架構 | 微服務架構 |..."]

[ITER 2] LLM → TOOL: summarize({"documents": [...], "question": "我該如何判斷..."})
[ITER 2] TOOL → LLM: "1. K8s 是容器編排平台，支援微服務各自獨立部署..."

[ITER 3] LLM → TOOL: write_answer({"question": "...", "summary": "..."})
[ITER 3] TOOL → LLM: "您應該根據應用程式需求決定：微服務 → K8s，單體 → Docker..."

[ITER 4] LLM → FINAL: "您應該根據您的應用程式需求和組態來決定..."
```

**觀察**：LLM 走了 4 輪（比預期的 3 輪多一輪）。第 4 輪 FINAL 的內容和第 3 輪 TOOL 輸出幾乎相同，代表 LLM 選擇再確認一次才結束。這是 ReAct loop 的正常行為，`MAX_ITER = 6` 的安全閥設計就是為了處理這類多繞一圈的情況。

### 演進的核心洞察

- v1 的 `print` 不是「偷懶」，而是最適合這個部署方式的工具
- 每個版本的 logging 機制都是**那個環境的自然慣例**，不需要在 v1 就引入 logging library
- 格式統一才是真正的跨版本複用，而不是程式碼複用

### 生產環境的完整 Observability 方案（本專案不實作，但重要）

生產環境的 observability 通常分三個層次：

| 層次 | 工具 | 解決什麼問題 |
|---|---|---|
| **Logs** | ELK Stack（Elasticsearch + Logstash + Kibana）/ CloudWatch / Azure Monitor | 集中收集所有服務的 stdout，支援搜尋、過濾、設 alert |
| **Metrics** | Prometheus + Grafana | 數值型指標（request rate、error rate、latency、CPU/memory），畫成時序圖，設閾值警報 |
| **Tracing** | Jaeger / Zipkin / AWS X-Ray | 追蹤一個請求跨多個服務的完整路徑，找出哪個服務是效能瓶頸 |

**為什麼三個都需要：**
- Logs 告訴你「發生了什麼」
- Metrics 告訴你「系統健康程度」
- Tracing 告訴你「這個請求花在哪裡」

**對應到 Relay 的架構：** 一個 `/query` 請求會跨越 orchestrator → search → summarize → write 四個服務。在生產環境，Tracing 能讓你看到整條路徑的每個段落花了多少時間，直接定位瓶頸（例如：search 的 embedding 太慢）。

**本專案的替代方案：** `[ITER N]` prefix 的 print + `docker compose logs` / `kubectl logs`，夠用於學習，但沒有集中查詢和 alert 能力。

**學習後的體會：**  
v2a 最具體的體會是：`docker compose logs` 同時混合四個服務的輸出，orchestrator 的 `[ITER N]` 和 search 的 `POST /search 200 OK` 交錯出現，一眼就能對應「這個 tool call 觸發了哪個服務的哪個 request」。這是微服務架構帶來的天然 observability 提升，不需要額外工具。反面教材也出現了：ONNX model 冷啟動期間完全沒有輸出，等待過程像黑盒——這正是 readiness probe 要解決的問題，也是生產環境需要 Metrics 和 Tracing 的原因。

---

## 部署版本命名慣例（Branch 命名邏輯）

**數字變 = 架構大改；字母變 = 部署方式換**

| Branch | 應用架構 | 部署基礎設施 | 變動層級 |
|---|---|---|---|
| 1 | 單體（monolith） | 直接執行 `python` | — |
| 2a | 微服務（FastAPI × 4） | Docker Compose | 架構大改 → 數字進 2 |
| 2b | 微服務（同 2a） | K8s（minikube） | 只換部署方式 → 加字母 b |
| 3 | 事件驅動 + Serverless | 雲端 Function + Queue | 架構再大改 → 數字進 3 |

**核心洞察：** 2a → 2b 的程式碼幾乎不動，Docker Image 是同一份；換的是 `docker-compose.yml` → K8s YAML。因此它們是同一個「v2 微服務架構」的兩種跑法，而非兩個不同版本。

這個命名邏輯在企業環境中也很常見：同一份 Image 可以先在 Compose 本地驗證，再部署到 K8s 生產，應用層完全不改動。

---

## FastAPI 服務設計

**它是什麼：** Python 的輕量 web framework，用來把 agent 包成一個獨立的 HTTP 服務。  
**為什麼用它：** v2 每個 agent 要能被其他服務呼叫，FastAPI 是最快的方式。  
**學習後的體會：**  
一個 Python 函式加上 `@app.post("/search")` 就變成 HTTP endpoint，程式碼量幾乎沒有增加。Pydantic model 負責輸入驗證，傳錯格式會自動回傳 422，不需要自己寫驗證邏輯。`lifespan` 是 FastAPI 的標準啟動鉤子，用來做「只跑一次的初始化」（如 ChromaDB 預熱），這個模式在 K8s 的 readiness probe 設計中完全對應：服務 ready 之前不接流量。

---

## Docker Client-Server 架構

**它是什麼：** Docker 是 client-server 架構，`docker` CLI 和真正做事的 daemon 是兩個不同程式。

```
你輸入指令
    ↓
docker CLI（Mac，darwin/arm64）
    ↓  API call（透過 socket）
Docker daemon（Colima Linux VM，linux/arm64）
    ↓
實際建容器
```

**為什麼這樣設計：** Client 負責接收指令並翻譯成 API request，Server（daemon）負責實際執行。兩者分離讓 Client 可以遠端控制不同機器上的 daemon——企業 CI/CD 就是這樣：在 MacBook 下指令，容器實際跑在遠端 Linux 機器上，指令完全一樣。

**為什麼 Mac 上需要 Colima：** Docker daemon 需要 Linux kernel 才能跑容器，Mac 的 kernel 是 Darwin。Colima 啟動一個極小的 Linux VM 只為了提供這個 kernel，對使用者完全透明。這也是為什麼 `docker version` 會看到：
- Client OS：`darwin/arm64`（Mac）
- Server OS：`linux/arm64`（Colima VM 裡的 Linux）

**VM 術語注意：** Colima 的 VM 和「WAR on VM」的 VM 雖然都叫 VM，但層次完全不同：
- WAR on VM：VM 是**部署目標**，裡面跑完整 OS + Tomcat + 應用程式
- Colima VM：VM 是**工具的底層依賴**，只提供 Linux kernel，使用者感受不到它存在

---

## Docker Image 與容器化

**它是什麼：** Image 是「程式碼 + 執行環境」的完整快照，Container 是 Image 的執行實例。

**Image vs Container：**
- Image = 食譜（靜態、不可變、可版本控制）
- Container = 照食譜煮出來的菜（執行中的實例）
- 一個 Image 可以同時跑出多個 Container（水平擴展的基礎）

---

### Java 封裝格式歷史沿革（JAR / WAR）

**JAR（Java ARchive）** — 通用格式，兩種用法：
- **Library JAR**：給其他程式引用的函式庫，沒有 main，不能直接跑
- **Fat JAR / Executable JAR**：Spring Boot 常用，把程式碼 + 所有依賴 + 內嵌 Tomcat 全部打包，直接 `java -jar myapp.jar` 啟動

**WAR（Web Application ARchive）** — 專給 web 應用，需部署到外部 app server（Tomcat、JBoss、WebLogic）才能跑

| | WAR | Fat JAR（Spring Boot）|
|---|---|---|
| 需要外部 Tomcat | ✅ 需要 | ❌ 不需要（內嵌） |
| 啟動方式 | 丟進 Tomcat webapps/ | `java -jar` |
| 容器化難度 | Image 裡要先裝 Tomcat | 直接 `FROM openjdk` 即可 |

**公司產品的演化路徑：**

```
WAR on VM（最舊）
  └── VM 裡人工裝 JDK + Tomcat，把 WAR 丟進去
  └── 問題：環境靠人工維護，機器間不一致，擴展要複製整台 VM

↓

支援 Docker（改版後）
  └── 若已改 Spring Boot Fat JAR：Image = openjdk + jar，乾淨簡單
  └── 若仍用 WAR：Image = openjdk + Tomcat + war，較重但一樣可以跑
  └── 好處：環境一致、啟動秒級、Image 可版本控制

↓

支援 K8s
  └── 自動管理 Container：副本數、故障重啟、rolling update
```

---

### 對應到 Relay 專案（Python）

Python 沒有 JAR/WAR，但概念完全對應：

| Java 世界 | Python / Relay |
|---|---|
| WAR（需外部 Tomcat） | 無對應（Python 沒有外部 app server 的傳統） |
| Fat JAR（內嵌 Tomcat） | FastAPI + uvicorn（uvicorn 就是內嵌的 ASGI server） |
| `java -jar myapp.jar` | `uvicorn app:app` 或 `python main.py` |
| Docker Image（含 JDK + jar） | Docker Image（含 Python + 依賴 + FastAPI app） |

**Branch 1（現在）：** 直接跑 `python main.py`，等同於最舊的「裸機執行」，連 jar 都還沒有。

**Branch 2a（下一步）：** 每個 agent 包成 FastAPI + uvicorn，打包成 Docker Image，等同於 Fat JAR → Docker 這一步。

**為什麼用它：** 每個 agent 有了自己的 Image，才能做到「各自部署、各自擴展」。

**學習後的體會：**  
Dockerfile 就是「環境安裝步驟的文字版」：base image 選 Python、複製 requirements.txt、跑 pip install、複製程式碼、設定啟動指令。每一行都對應一個 layer，Docker 會快取沒有改動的 layer，所以只改 main.py 不改 requirements 時，rebuild 幾乎是瞬間完成的。Image 打包完就是不可變的，同一份 Image 可以在 Docker Compose 跑，也可以直接搬到 K8s 跑，這才是「環境一致」的真正意義。

---

## Docker Compose 多服務編排

**它是什麼：** 用一個 YAML 檔定義多個容器如何啟動、如何互連。  
**為什麼用它：** v2a 的四個 agent 服務需要同時跑並互相溝通，Docker Compose 是最直接的方式。  
**學習後的體會：**  
最直接的體會是服務發現：容器內不需要寫 IP，直接用 service name（`http://search:8001`），Docker Compose 的內部網路自動解析。Volume mount 讓 ChromaDB 的資料從宿主機掛進容器，容器刪掉重建也不會遺失資料，這是「有狀態服務」在容器化時必須處理的問題，K8s 的 PersistentVolumeClaim 解決的是同一個問題，只是規模更大。`depends_on` 控制啟動順序，但它只等容器啟動，不等服務 ready——這是 Docker Compose 和 K8s readiness probe 之間的重要差距。

### 真實執行 Trace（Branch 2a）

問題：「什麼是 K8s？」

```
orchestrator-1  | [ITER 1] LLM → TOOL: search({"query": "K8s"})
search-1        | INFO: 172.18.0.5:42232 - "POST /search HTTP/1.1" 200 OK
orchestrator-1  | [ITER 1] TOOL → LLM: ["Kubernetes（K8s）是開源的容器編排平台..."]

orchestrator-1  | [ITER 2] LLM → TOOL: summarize({...})
summarize-1     | INFO: 172.18.0.5:35674 - "POST /summarize HTTP/1.1" 200 OK
orchestrator-1  | [ITER 2] TOOL → LLM: "Kubernetes (K8s) 是一個開源的容器編排平台..."

orchestrator-1  | [ITER 3] LLM → TOOL: write_answer({...})
write-1         | INFO: 172.18.0.5:47790 - "POST /write HTTP/1.1" 200 OK
orchestrator-1  | [ITER 3] TOOL → LLM: "Kubernetes，簡稱 K8s，是一個開源的容器編排..."

orchestrator-1  | [ITER 4] LLM → FINAL: "Kubernetes（簡稱 K8s）是一個開源的容器編排平台..."
orchestrator-1  | INFO: 172.18.0.1:42992 - "POST /query HTTP/1.1" 200 OK
```

**v1 vs v2a 的關鍵差異：** v1 的 log 只有一個 process 的輸出；v2a 的 log 同時來自四個容器，而且可以清楚看到每次 tool 呼叫對應到哪個服務的 HTTP request（`POST /search`、`POST /summarize`、`POST /write`）。這就是微服務架構帶來的可觀察性：每個服務的 log 獨立，出問題時可以直接定位到哪個服務。

**學習後的體會：**  
實際跑起來才感受到 `docker compose logs` 同時混合四個服務輸出的威力：每次 orchestrator 發出 `TOOL: search(...)` 的下一行就出現 `search-1 | POST /search 200 OK`，一眼就能對應「哪個 tool call 打到哪個服務、花了多少時間」。這是把函式切成 HTTP 服務後免費得到的可觀察性，不需要額外工具。另一個具體體驗是 `depends_on` 的局限：它只等容器啟動，不等服務 ready，導致 orchestrator 搶先呼叫 search，但 search 還在載入 ONNX model 而 timeout。這個問題只有在多容器環境才會出現，解法是 FastAPI lifespan 預熱 + K8s readiness probe，兩者解決的是同一個問題，只是粒度不同。

---

## Clean Architecture：Use Case 不依賴 Infrastructure（Branch 2a+）

**它是什麼：** Clean Architecture 的核心規則（Dependency Rule）：業務邏輯（Use Case）不應該知道資料是從 HTTP、資料庫還是本地函式來的。  
**為什麼用它：** 讓 ReAct loop 可以在不啟動任何 HTTP 服務的情況下直接測試，只需傳入 mock callable。

### 拆分前 vs 拆分後

| | 拆分前（main.py） | 拆分後 |
|---|---|---|
| ReAct loop | 和 httpx、FastAPI 混在一起 | `react.py`，只依賴標準庫 |
| HTTP 呼叫 | 散落在 `dispatch()` 和 loop 裡 | `clients.py`，全部集中 |
| 測試 | 需要 `patch("httpx.post")` | 直接傳 mock callable，不碰 httpx |

### 核心設計

```python
# react.py：不 import httpx，不 import fastapi
def run_react_loop(
    question: str,
    dispatch: Callable[[str, dict], str],   # 工具呼叫
    chat_fn: Callable[[list[dict]], dict],   # LLM 呼叫
) -> str: ...

# clients.py：所有 httpx 呼叫集中在這
def make_dispatch(search_url, summarize_url, write_url) -> Callable: ...
def make_chat_fn(ollama_url, model, tools) -> Callable: ...
```

**學習後的體會：**  
最直接的感受是測試變了：原本測 dispatch 需要 `patch("httpx.post")`，現在測 ReAct loop 直接傳一個 lambda，完全不需要 mock 任何 infrastructure。這個設計的深層意義是：`react.py` 描述的是「agent 的決策邏輯」，`clients.py` 描述的是「如何跟外界溝通」。兩件事分開之後，K8s 的 retry、circuit breaker、correlation ID 全部可以加在 `clients.py` 裡，`react.py` 完全不動。這也是為什麼 Branch 2b 的大多數新功能（retry、health check、correlation ID）都只需要碰 `clients.py` 和外部 YAML，核心業務邏輯是穩定的。

---

## K8s：核心概念與 Docker Compose 對照

**它是什麼：** Kubernetes 是容器編排平台，把「多個容器如何一起跑」這件事從手動管理升級到自動化。  
**為什麼用它：** 企業容器編排的業界標準。Docker Compose 解決「本地多服務同時跑」，K8s 解決「生產環境的高可用、自癒、滾動更新」。

---

### minikube 的層次結構

minikube 讓你在本機建一個「假的 K8s cluster」學習用。`--driver=docker` 的意思是：**用一個 Docker container 來模擬一台 K8s Node**。

```
Mac mini（實體機）
└── Colima VM（輕量 Linux VM，提供 Linux kernel）
    └── Docker daemon（跑在 Colima VM 裡）
        └── minikube-node container（這個 container 模擬一台 K8s Node）
            └── K8s cluster（跑在這個 container 裡）
                ├── orchestrator Pod
                ├── search Pod
                ├── summarize Pod
                └── write Pod
```

K8s 在企業裡跑在真實的多台機器（Node）上；minikube 用一個 Docker container 假裝成一台 Node，讓你用 `kubectl` 練習完整的 K8s 操作。

**v2a vs v2b 的層次對比：**

```
v2a（Docker Compose）：
  Docker daemon → 直接管 4 個服務 container

v2b（minikube）：
  Docker daemon → minikube-node container → K8s → 4 個服務 Pod
```

多了一層 K8s 在中間，換來的是 rolling update、replica 管理、readiness probe 這些 Docker Compose 做不到的能力。

---

### Pod 是什麼？

**Pod 是 K8s 的最小部署單位**，等同於 Docker 的 container（實務上 Relay 每個 Pod 只有一個 container）。

差異是：Pod 有**身份**，由 K8s 管理——決定它跑在哪台機器、死掉要不要重建、要跑幾個副本。Docker container 只是你手動跑的一個盒子，死了就死了。

```
Docker:  docker run relay-search    → container（你管）
K8s:     kubectl apply search.yaml  → Pod（K8s 管）
```

---

### Docker Compose → K8s 概念對照

| Docker Compose | K8s 對應 | 說明 |
|---|---|---|
| `services:` 裡的服務名稱 | **Service（ClusterIP）** | cluster 內部服務發現，`http://search:8001` |
| `ports: "8000:8000"` | **Ingress** | 外部流量進入點，加了路徑分流能力 |
| `environment:` | **ConfigMap** | 設定值獨立成資源，多個 Pod 共用 |
| `volumes:` | **PVC（PersistentVolumeClaim）** | 向 K8s 申請一塊持久化硬碟 |
| `build:` + container | **Deployment** 或 **StatefulSet** | 管 Pod 的生命週期 |
| `depends_on:` | **readinessProbe** | Compose 只等容器啟動；K8s 等服務真正 ready |

---

### Ingress 不只是「開 port」

Docker Compose 的 `ports: "8000:8000"` 是直接把 container port 打洞到宿主機，外面只能連那個 port。

Ingress 更像 nginx reverse proxy：一個入口，根據**路徑**或 **domain** 分派流量給不同 Service：

```
外部 POST /query  →  Ingress  →  orchestrator Service  →  orchestrator Pod
外部 GET  /health →  Ingress  →  orchestrator Service  →  orchestrator Pod
（未來可以加）
外部 GET  /search →  Ingress  →  search Service        →  search Pod
```

---

### Deployment vs StatefulSet

**Deployment（無狀態服務）：**  
Pod 是可拋棄的，死了 K8s 建一個新的，名字隨機，沒有固定身份。適合 orchestrator、summarize、write。

**StatefulSet（有狀態服務）：**  
Pod 有固定名稱（`search-0`），綁定專屬 PVC。Pod 死掉重建後名字不變、掛回同一塊硬碟，資料不消失。適合 search（ChromaDB 資料）、資料庫（MySQL、Redis）。

```
Deployment:  orchestrator-7f9b2-xkp3q 死掉 → orchestrator-7f9b2-mn4rs（新名字，一樣）
StatefulSet: search-0 死掉               → search-0（同名字，同 PVC，資料還在）
```

---

### PVC 是什麼？

PVC（PersistentVolumeClaim）是「向 K8s 申請一塊硬碟」的申請書。你說「我要 500Mi」，K8s 幫你找一塊實際的硬碟（PV）給你，Pod 掛上去用。Pod 刪掉，硬碟裡的資料還在。

StatefulSet 的 `volumeClaimTemplates` 讓每個 Pod 自動申請自己專屬的 PVC，不需要手動建立。

---

### kubectl apply：宣告式管理

`kubectl apply -f k8s/` 是把 `k8s/` 目錄裡所有 YAML 送給 K8s，K8s 讀完後把裡面定義的資源全部建立起來。

```bash
# Docker Compose（命令式）
docker compose up       # 直接啟動服務

# K8s（宣告式）
kubectl apply -f k8s/  # 宣告你要的狀態，K8s 負責讓現實符合宣告
```

**宣告式（Declarative）vs 命令式（Imperative）** 是 K8s 和 Docker Compose 最根本的設計差異：

| | Docker Compose | K8s |
|---|---|---|
| 你說的是 | 「執行這些步驟」 | 「我要這個狀態」 |
| Pod 死掉 | 不管（你要手動重啟） | K8s 自動補一個，維持宣告的數量 |
| 改設定 | 重跑指令 | 改 YAML 再 apply，K8s 算出 diff 只改必要的部分 |

例如你的 YAML 宣告「我要 2 個 orchestrator Pod」，K8s 會建 Pod 直到數量變 2。之後某個 Pod 死掉，K8s 自動補一個，永遠維持宣告的狀態——這就是 K8s 自癒能力的根源。

---

### host.minikube.internal

從 minikube Pod 內部連到宿主機（Mac mini）的 hostname，等同於 Docker Compose 的 `host.docker.internal`：

| 環境 | 連到宿主機的寫法 |
|---|---|
| Docker Compose | `host.docker.internal` |
| minikube（K8s） | `host.minikube.internal` |

Relay 的 ConfigMap 用這個連到 Mac mini 上的 Ollama，不需要 hardcode IP。

---

### 部署步驟（v2b）

```bash
# 一次性準備
minikube start --driver=docker
minikube addons enable ingress
eval $(minikube docker-env)   # 切換 Docker CLI 指向 minikube daemon

# 在 v2/ 目錄下 build image（指向 minikube daemon，image 直接在 cluster 裡）
docker build -t relay-search:v2b        ./services/search
docker build -t relay-summarize:v2b     ./services/summarize
docker build -t relay-write:v2b         ./services/write
docker build -t relay-orchestrator:v2b  ./services/orchestrator

# Apply 所有 K8s 資源
kubectl apply -f k8s/

# 等 pod 全部 Running
kubectl get pods -w

# 第一次：seed ChromaDB 資料進 PVC（等 search-0 Running 後）
kubectl cp v1/chroma_db/. search-0:/data/chroma_db/

# 測試
curl -X POST http://$(minikube ip)/query \
  -H "Content-Type: application/json" \
  -d '{"question":"什麼是 K8s？"}'
```

**學習後的體會：**

實際部署踩了三個坑，每個都是 Docker Compose 時代不會遇到的：

**坑一：PVC 第一次是空的。** `kubectl apply` 建好 StatefulSet 後，search-0 啟動時找不到 ChromaDB collection，直接 crash。原因是 PVC 是新申請的空白硬碟，需要手動把 v1 的語料庫 seed 進去：`kubectl cp v1/chroma_db/. search-0:/data/chroma_db/`。這個步驟只有第一次需要，之後 Pod 死掉重建資料都還在。

**坑二：ONNX model 每次 Pod 啟動都重新下載（ADR-006）。** livenessProbe 的 `initialDelaySeconds` 不夠長，Pod 還在下載 79MB model 時就被判死、重啟、再下載，無限循環。解法是在 Dockerfile 的 build 階段就把 model 預熱進 image（`RUN python -c "... f(['warmup'])"`），把下載成本從「執行期每次啟動」移到「build 一次」。

**坑三：kubectl port-forward 對長請求不穩定。** 後來改用 NodePort，再改用 cluster 內部 test-curl pod，最終靠在 cluster 內直接打 `http://orchestrator:8000` 驗通。

---

## K8s：Liveness / Readiness Probe 與 Rolling Update

**它是什麼：** K8s 透過兩個 HTTP 探針決定 Pod 的狀態；Rolling update 讓服務更新時逐步替換 Pod，不中斷服務。  
**為什麼用它：** 零停機部署的核心機制，面試必問。

---

### Liveness vs Readiness：為什麼要分兩個？

| 探針 | 問的問題 | 失敗的後果 | 對應端點 |
|---|---|---|---|
| **livenessProbe** | Process 還活著嗎？ | K8s **重啟** Pod | `/health/live` |
| **readinessProbe** | 可以接流量嗎？ | K8s 把 Pod **從 Service 移除**（不重啟） | `/health/ready` |

兩個分開的原因：有些服務啟動時需要暖機（如 search 載入 ONNX model，要等 120 秒），暖機期間 process 是活的（不該重啟），但還沒準備好接流量（不該讓 Ingress 送請求過來）。

```
search Pod 啟動
    ↓
livenessProbe /health/live → 200（process 活著，K8s 不重啟）
readinessProbe /health/ready → 503（ChromaDB 還在載入，不接流量）
    ↓
ChromaDB warmup 完成，_ready = True
    ↓
readinessProbe /health/ready → 200（加入 Service，開始接流量）
```

這個模式和 Branch 2a 用 FastAPI `lifespan` 解決 ONNX 冷啟動是同一個思路，K8s 只是把它標準化了。

---

### Rolling Update 是什麼？

更新 image 時，K8s 不是把所有 Pod 一次砍掉重建，而是逐一替換：

```
更新前：[orchestrator-v1] [orchestrator-v1] [orchestrator-v1]

替換第一個：
[orchestrator-v2] [orchestrator-v1] [orchestrator-v1]  ← v2 readiness OK 後才換下一個

替換第二個：
[orchestrator-v2] [orchestrator-v2] [orchestrator-v1]

完成：
[orchestrator-v2] [orchestrator-v2] [orchestrator-v2]
```

整個過程中永遠有 Pod 在服務，使用者感受不到中斷。**readinessProbe 是 rolling update 的關鍵**：K8s 等新 Pod ready 才繼續換下一個，確保不會在新 Pod 還沒暖機時就把舊 Pod 砍掉。

**演練指令：**
```bash
# 改 image tag 觸發 rolling update
kubectl set image deployment/orchestrator orchestrator=relay-orchestrator:v2b-new

# 觀察滾動替換過程
kubectl rollout status deployment/orchestrator
```

**學習後的體會：**

Rolling update 在 1 個 replica 下替換太快，`kubectl get pods -w` 還沒開就換完了。從 Pod hash 的改變（`65c4fbbb7d-...` → `647dd8bc7-...`）可以確認是新 Pod，用 `curl /health` 看到 `"version": "v2b-r1"` 確認新版本真的上線。

`kubectl rollout status` 是 CI/CD pipeline 的常客：它同步等待 rolling update 完成才退出，讓後續的 integration test 確保在新版本上跑，而非舊 Pod。

---

## asyncio Event Loop 阻塞診斷（Branch 2b 實戰）

**問題現象：** `/query` 請求打進去，search → summarize 都正常，到 ITER 3（最後一次 LLM 推論）時 curl 回傳 `Empty reply from server`（HTTP 52），pod 以 Exit Code 137 重啟。

**診斷關鍵：** 看 `kubectl logs` 時發現，request 進來後，連 `/health/ready` 的 access log 都完全消失，連一筆都沒有。這是決定性的診斷訊號：

```
INFO: GET /health/ready 200 OK   ← request 前有 probe log
INFO: GET /health/ready 200 OK
[START: 什麼是k8s?]
[ITER 1] LLM → TOOL: search(...)
[ITER 2] LLM → TOOL: summarize(...)
[ITER 2] TOOL → LLM: (summarize 結果)
← 此後完全沒有任何 probe log，直到 pod 被 kill
```

Readiness probe 每 5 秒、Liveness probe 每 10 秒都應該在 log 裡留下 access 記錄。如果全部消失，代表 **asyncio event loop 被阻塞**，uvicorn 完全無法處理任何新的請求，包括 health check。

**Exit Code 137 的意義：** 128 + 9 = SIGKILL。K8s 發現 liveness probe 連續失敗 3 次，先送 SIGTERM，30 秒後 Python process 還沒退出（被 Ollama httpx 呼叫卡住），強制 SIGKILL。這不是 OOM（OOM kill 的 Reason 會是 `OOMKilled`，這裡是 `Error`）。

**原來的做法：**
```python
# 理論上應該讓 event loop 自由，但實際上失效了
loop = asyncio.get_event_loop()
answer = await loop.run_in_executor(None, react.run_react_loop, ...)
```

`run_in_executor` 的設計是把阻塞工作丟到 thread pool，讓 event loop 繼續跑。但在這個案例中 event loop 還是被阻塞了，原因至今不完全清楚（可能與 httpx sync client 在某些情況下 interact 回 asyncio 有關）。

**正確做法：全程 async**

FastAPI 是 async 框架，HTTP 呼叫是 I/O bound 操作，本來就應該是 async：

```python
# clients.py：async def + httpx.AsyncClient
async def chat_fn(messages):
    async with httpx.AsyncClient() as client:
        response = await client.post(...)
    return response.json()["message"]

# react.py：async def run_react_loop
async def run_react_loop(question, dispatch, chat_fn):
    msg = await chat_fn(messages)   # 不阻塞 event loop
    result = await dispatch(name, args)
    ...

# main.py：直接 await，不需要 run_in_executor
answer = await react.run_react_loop(req.question, dispatch, chat_fn)
```

**修完後：** event loop 在 LLM 推論期間（可能 2-3 分鐘）仍能正常回應 health probe，pod 不再被誤殺，最終取得完整答案。

**核心心法：**
- `run_in_executor` 是讓舊有同步程式碼在 async 框架裡「勉強跑」的過渡手段
- async 框架（FastAPI）+ 同步阻塞 I/O（sync httpx）= 遲早出問題
- 診斷 event loop 是否被阻塞：看 health probe 的 access log 是否在 request 期間消失

---

## K8s：Application-level HA

**它是什麼：** 透過 Deployment 的 `replicas` 設定多個 pod 副本，任一 pod 死掉 K8s 自動重建並將流量切到健康的 pod。

**為什麼用它：** 這是客戶端最常問「如何做備援」的應用層答案。和 DB 主從不同，這裡處理的是 stateless 服務的高可用。

**在 Branch 2b 的練習：**
1. 將 agent Deployment 的 `replicas` 設為 2
2. 手動 `kubectl delete pod <pod-name>` 模擬 pod 故障
3. 觀察 K8s 自動重建，Service 持續可用

**學習後的體會：**

Kill pod 演練的實際輸出：

```
search-0   1/1 Running       ← 正常運行中
search-0   1/1 Terminating   ← kubectl delete 觸發
search-0   0/1 Completed     ← Pod 關閉中
search-0   0/1 Pending       ← K8s 立刻建新 Pod（StatefulSet 保證同名）
search-0   0/1 ContainerCreating
search-0   0/1 Running       ← Container 啟動，readinessProbe 開始檢查
search-0   1/1 Running       ← ChromaDB warmup 完成，開始接流量（共 12 秒）
```

三個關鍵觀察：

1. **StatefulSet 保證同名**：新 Pod 還是叫 `search-0`，Deployment 的隨機名字（如 `orchestrator-647dd8bc7-...`）在 StatefulSet 這裡不適用。Pod 名字固定，PVC 自動重新掛回，資料完好。

2. **readinessProbe 讓不可用時間最小化**：`0/1` 到 `1/1` 的 12 秒是 ChromaDB warmup，這段時間 Service 不會把流量送到這個 Pod。Ingress 層完全感知不到這個 Pod 死過一次。

3. **tenacity retry 的意義**：這 12 秒內如果 orchestrator 剛好發出 search 請求，會暫時 503，tenacity 的 exponential backoff 會自動重試到 search ready 為止。這是 ADR-007 以外另一個讓系統有韌性的設計。

---

## DB 主從式架構（Primary-Replica）

**它是什麼：** 資料庫的備援設計。Primary 處理寫入，Replica 同步 Primary 的資料並處理讀取。Primary 故障時，Replica 升主（Failover）繼續服務。

**為什麼重要：** 客戶端被問「你們的備援怎麼設計」，99% 是在問這個。

**學習方式：** 另立專案，以 PostgreSQL streaming replication 為主題實作。本專案（ChromaDB）不支援 replication，不在此學。

---

## Message queue（RabbitMQ / Redis）

**它是什麼：** 服務之間傳遞訊息的中間層，發送方和接收方不需要同時在線。  
**為什麼用它：** v3 的 agent 由事件觸發而非直接 HTTP 呼叫，解耦服務、處理峰值流量。  
**學習後的體會：**  
_（完成 Branch 3 後填寫）_

---

## Serverless function 觸發

**它是什麼：** 函式由事件（HTTP 請求、queue 訊息）觸發，執行完即銷毀，不需要常駐服務。  
**為什麼用它：** 短時間、低頻率的任務（如 Write Agent）不需要佔用常駐容器資源。  
**學習後的體會：**  
_（完成 Branch 3 後填寫）_

---

## 冷啟動 vs 常駐容器取捨

**它是什麼：** Serverless 函式第一次被呼叫時需要初始化（冷啟動），可能造成幾百毫秒延遲；容器一直跑著就沒有這個問題但要持續付費。  
**為什麼重要：** 架構選型的核心取捨，面試時必須能說清楚「什麼情況選哪個」。  
**學習後的體會：**  
_（完成 Branch 3 後填寫）_

---

## 雲端 LLM vs 本地 LLM 選型

**它是什麼：** 兩種 LLM 部署策略：雲端 API（Claude / GPT，按用量付費）vs 本地自建（Ollama，固定硬體成本）。  
**為什麼重要：** 企業導入 AI 最常遇到的決策題，涉及隱私、成本、延遲三角取捨。  
**學習後的體會：**  
_（完成 Branch 3 後填寫）_

---

## 面試故事（持續更新）

> 每完成一個 Branch，用一段話更新這裡，練習用面試語言描述自己做了什麼。

**Branch 0.5 完成後：**  
「我用 Python 從零搭建了一個 multi-agent research pipeline，沒有使用任何 agent 框架。Orchestrator 呼叫 Search、Summarize、Write 三個 agent，每個 agent 都是一個獨立函式，透過 Ollama 本地 LLM 處理任務。這個版本的 Search Agent 用 hardcode 假資料，讓整條 pipeline 先跑通，確認架構方向正確再逐步補強。」

**Branch 1 完成後：**  
「我為 v1 Monolith 實作了 ChromaDB 語意搜尋，取代假資料的 Search Agent。核心是 ReAct pattern 的 agent loop：LLM 透過 tool use 自行決定呼叫 search、summarize、write_answer 的順序，loop 有明確終止條件（無 tool call 或超過 MAX_ITER）。整個 pipeline 在單一 Python process 內跑通，並用 unit test 覆蓋了 loop 終止條件和 dispatch 路由邏輯。」

**Branch 2a 完成後：**  
「我把 v1 的四個 Python 函式各自包成獨立 FastAPI 服務，用 Docker Compose 一鍵啟動。核心架構變化是 orchestrator 從直接呼叫 Python 函式，改成對其他容器發 HTTP POST。服務間透過 Docker Compose 內部網路用 service name 互連，ChromaDB 資料用 volume mount 共享。過程中遇到 ChromaDB ONNX model 冷啟動 timeout 問題，用 FastAPI lifespan 預熱解決，並記錄為 ADR-005。」

**Branch 2b 完成後：**  
_（填寫）_

**Branch 3 完成後：**  
_（填寫）_

**完整故事（Branch 4 完成後）：**  
_（填寫）_
