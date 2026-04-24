import os
import httpx
from fastapi import FastAPI, Request
from pydantic import BaseModel

app = FastAPI()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


class SummarizeRequest(BaseModel):
    question: str
    documents: list[str]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/live")
def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready():
    return {"status": "ok"}


@app.post("/summarize")
def summarize(req: SummarizeRequest, request: Request):
    request_id = request.headers.get("X-Request-ID", "")
    if request_id:
        print(f"[{request_id}] summarize: {req.question[:60]}", flush=True)
    docs_text = "\n\n".join(req.documents)
    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={
            "model": "mistral:v0.3",
            "messages": [
                {
                    "role": "system",
                    "content": "你是資料摘要助手。將提供的文件整理成與問題相關的重點摘要。",
                },
                {
                    "role": "user",
                    "content": f"問題：{req.question}\n\n文件：\n{docs_text}\n\n請摘要出與問題相關的重點。",
                },
            ],
            "stream": False,
        },
        timeout=60,
    )
    return {"summary": response.json()["message"]["content"]}
