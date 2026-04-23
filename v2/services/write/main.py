import os
import httpx
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


class WriteRequest(BaseModel):
    question: str
    summary: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/write")
def write(req: WriteRequest):
    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={
            "model": "mistral:v0.3",
            "messages": [
                {
                    "role": "system",
                    "content": "你是寫作助手。根據摘要資料，用清晰易懂的方式回答使用者的問題。",
                },
                {
                    "role": "user",
                    "content": f"問題：{req.question}\n\n參考摘要：\n{req.summary}\n\n請撰寫完整回答。",
                },
            ],
            "stream": False,
        },
        timeout=60,
    )
    return {"answer": response.json()["message"]["content"]}
