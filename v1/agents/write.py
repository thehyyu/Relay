import httpx
import os


def write_agent(question: str, summary: str) -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    response = httpx.post(
        f"{base_url}/api/chat",
        json={
            "model": "mistral:v0.3",
            "messages": [
                {
                    "role": "system",
                    "content": "你是寫作助手。根據摘要資料，用清晰易懂的方式回答使用者的問題。",
                },
                {
                    "role": "user",
                    "content": f"問題：{question}\n\n參考摘要：\n{summary}\n\n請撰寫完整回答。",
                },
            ],
            "stream": False,
        },
        timeout=60,
    )
    return response.json()["message"]["content"]
