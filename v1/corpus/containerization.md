# 容器化技術

容器化是將應用程式與其依賴（函式庫、設定、執行環境）打包在一起的技術，確保在任何環境下都能一致執行。

## Docker 核心概念

- **Image**：唯讀的應用程式模板，包含程式碼和執行環境，透過 Dockerfile 定義。
- **Container**：Image 的執行實例，有獨立的檔案系統、網路和 Process 空間。
- **Dockerfile**：定義如何建構 Image 的腳本，每個指令建立一個層（layer）。
- **Volume**：容器外部的持久儲存，容器刪除後資料仍保留。
- **Network**：容器間的虛擬網路，可隔離或互連不同容器。

## 容器 vs 虛擬機

| 面向 | 容器 | 虛擬機 |
|------|------|--------|
| 啟動時間 | 毫秒級 | 分鐘級 |
| 資源佔用 | 輕量（共享 OS 核心） | 重量（各自有 OS） |
| 隔離程度 | Process 級隔離 | 硬體級隔離 |
| 適合場景 | 微服務、CI/CD | 強隔離需求 |

## Docker Compose

用一個 YAML 檔定義多個容器的啟動方式和互連關係，適合本地開發和測試多服務架構。

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
  db:
    image: postgres:16
    volumes:
      - db_data:/var/lib/postgresql/data
```

## 容器網路模式

- **bridge**：預設模式，容器在虛擬網路中互連，透過 port mapping 對外暴露。
- **host**：容器直接使用主機網路，效能最佳但隔離性低。
- **none**：完全隔離，無網路存取。
