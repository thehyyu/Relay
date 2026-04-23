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
| FastAPI 服務設計 | 未開始 | 微服務 API 契約 |
| Docker Compose 多服務編排 | 未開始 | 本地模擬多容器環境 |
| K8s：Deployment / Service / Ingress | 未開始 | 企業容器編排標準 |
| K8s：rolling update / health check | 未開始 | 零停機部署 |
| K8s：Application-level HA（replicas + probe） | 未開始 | Pod 失效自動重建、流量切換 |
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
_（完成 Branch 1 後填寫）_

---

## Agent loop（ReAct pattern）

**它是什麼：** Reasoning + Acting 的迴圈：LLM 思考 → 決定呼叫工具 → 看結果 → 再思考，直到任務完成。  
**為什麼用它：** 這是所有 agent 框架（AutoGen、LangGraph）的底層邏輯，自己實作一次才真正理解框架在做什麼。  
**學習後的體會：**  
_（完成 Branch 1 後填寫）_

---

## Orchestrator pattern

**它是什麼：** 一個 agent 負責把任務分派給其他 agent，收集結果後整合輸出。  
**為什麼用它：** 單一 agent 做所有事會讓 prompt 爆炸複雜，拆開職責讓每個 agent 的 prompt 保持簡單。  
**學習後的體會：**  
_（完成 Branch 1 後填寫）_

---

## FastAPI 服務設計

**它是什麼：** Python 的輕量 web framework，用來把 agent 包成一個獨立的 HTTP 服務。  
**為什麼用它：** v2 每個 agent 要能被其他服務呼叫，FastAPI 是最快的方式。  
**學習後的體會：**  
_（完成 Branch 2a 後填寫）_

---

## Docker Compose 多服務編排

**它是什麼：** 用一個 YAML 檔定義多個容器如何啟動、如何互連。  
**為什麼用它：** v2a 的四個 agent 服務需要同時跑並互相溝通，Docker Compose 是最直接的方式。  
**學習後的體會：**  
_（完成 Branch 2a 後填寫）_

---

## K8s：Deployment / Service / Ingress

**它是什麼：** Kubernetes 的三個核心物件：Deployment 管 pod 生命週期，Service 管服務發現，Ingress 管外部流量進入。  
**為什麼用它：** 企業容器編排的業界標準，把 Docker Compose 的概念升級到可擴展、可自癒的版本。  
**學習後的體會：**  
_（完成 Branch 2b 後填寫）_

---

## K8s：rolling update / health check

**它是什麼：** Rolling update 讓服務在更新時逐步替換 pod，不中斷服務；health check 讓 K8s 知道哪些 pod 可以接流量。  
**為什麼用它：** 零停機部署的核心機制，面試必問。  
**學習後的體會：**  
_（完成 Branch 2b 後填寫）_

---

## K8s：Application-level HA

**它是什麼：** 透過 Deployment 的 `replicas` 設定多個 pod 副本，任一 pod 死掉 K8s 自動重建並將流量切到健康的 pod。

**為什麼用它：** 這是客戶端最常問「如何做備援」的應用層答案。和 DB 主從不同，這裡處理的是 stateless 服務的高可用。

**在 Branch 2b 的練習：**
1. 將 agent Deployment 的 `replicas` 設為 2
2. 手動 `kubectl delete pod <pod-name>` 模擬 pod 故障
3. 觀察 K8s 自動重建，Service 持續可用

**學習後的體會：**  
_（完成 Branch 2b 後填寫）_

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
_（填寫）_

**Branch 2b 完成後：**  
_（填寫）_

**Branch 3 完成後：**  
_（填寫）_

**完整故事（Branch 4 完成後）：**  
_（填寫）_
