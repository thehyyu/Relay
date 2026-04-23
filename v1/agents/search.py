# Branch 0.5：固定回傳假資料，讓 pipeline 先跑通
# Branch 1 會換成真正的 ChromaDB 語意搜尋

FAKE_DOCUMENTS = [
    "分散式系統由多台電腦透過網路協同工作。核心挑戰是 CAP 理論：一致性、可用性、分區容錯性三者只能同時滿足兩個。",
    "微服務架構將應用程式拆分為多個小型獨立服務，每個服務負責單一業務功能，透過 API 互相溝通，可以獨立部署與擴展。",
    "容器化技術讓應用程式在任何環境下一致執行。Docker 打包應用程式與其依賴，Kubernetes 負責容器的編排、自動擴展與自我修復。",
]


def search_agent(question: str) -> list[str]:
    return FAKE_DOCUMENTS
