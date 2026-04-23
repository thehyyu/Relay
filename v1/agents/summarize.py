import httpx
import os


def summarize_agent(question: str, documents: list[str]) -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    docs_text = "\n\n".join(documents)

    response = httpx.post(
        f"{base_url}/api/chat",
        json={
            "model": "mistral:v0.3",
            "messages": [
                {
                    "role": "system",
                    "content": "你是資料摘要助手。將提供的文件整理成與問題相關的重點摘要。",
                },
                {
                    "role": "user",
                    "content": f"問題：{question}\n\n文件：\n{docs_text}\n\n請摘要出與問題相關的重點。",
                },
            ],
            "stream": False,
        },
        timeout=60,
    )
    return response.json()["message"]["content"]
