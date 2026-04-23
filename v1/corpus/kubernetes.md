# Kubernetes

Kubernetes（K8s）是開源的容器編排平台，負責自動化容器的部署、擴展與管理。

## 核心物件

- **Pod**：K8s 最小部署單位，包含一個或多個容器，共享網路和儲存。
- **Deployment**：管理無狀態應用的 Pod 副本數，支援 rolling update 和 rollback。
- **StatefulSet**：管理有狀態應用（如資料庫），每個 Pod 有穩定的網路識別和持久儲存。
- **Service**：提供穩定的網路端點，將流量路由到一組 Pod，支援負載均衡。
- **Ingress**：管理外部 HTTP/HTTPS 流量進入 cluster，支援路由規則和 TLS 終止。
- **ConfigMap / Secret**：分離設定與程式碼，Secret 用於敏感資訊。
- **PersistentVolume（PV）/ PersistentVolumeClaim（PVC）**：管理持久儲存，Pod 重啟後資料不遺失。

## Deployment vs StatefulSet

- **Deployment**：Pod 可隨意替換，適合無狀態服務（API server、worker）。
- **StatefulSet**：Pod 有固定名稱和儲存，適合有狀態服務（資料庫、訊息佇列）。

## Rolling Update

Deployment 更新時逐步替換舊 Pod，確保服務不中斷：
1. 建立新版本 Pod
2. 確認新 Pod health check 通過
3. 移除舊版本 Pod
4. 重複直到全部更新完成

## Health Check

- **Liveness Probe**：檢查容器是否仍在正常執行，失敗則重啟。
- **Readiness Probe**：檢查容器是否準備好接收流量，失敗則從 Service 移除。
