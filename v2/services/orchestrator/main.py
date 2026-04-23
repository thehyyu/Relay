import json
import os
import httpx
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
SEARCH_URL = os.getenv("SEARCH_URL", "http://search:8001")
SUMMARIZE_URL = os.getenv("SUMMARIZE_URL", "http://summarize:8002")
WRITE_URL = os.getenv("WRITE_URL", "http://write:8003")
OLLAMA_MODEL = "qwen2.5:32b"
MAX_ITER = 6

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "從語料庫中搜尋與問題相關的文件段落",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜尋關鍵字或問題"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize",
            "description": "將搜尋到的文件段落摘要成重點",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "documents": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["question", "documents"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_answer",
            "description": "根據摘要撰寫清晰的最終回答",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["question", "summary"],
            },
        },
    },
]


def dispatch(tool_name: str, args: dict) -> str:
    if tool_name == "search":
        r = httpx.post(f"{SEARCH_URL}/search", json={"query": args["query"]}, timeout=120)
        return json.dumps(r.json()["documents"], ensure_ascii=False)
    if tool_name == "summarize":
        r = httpx.post(
            f"{SUMMARIZE_URL}/summarize",
            json={"question": args["question"], "documents": args["documents"]},
            timeout=60,
        )
        return r.json()["summary"]
    if tool_name == "write_answer":
        r = httpx.post(
            f"{WRITE_URL}/write",
            json={"question": args["question"], "summary": args["summary"]},
            timeout=60,
        )
        return r.json()["answer"]
    return f"unknown tool: {tool_name}"


class QueryRequest(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query")
def query(req: QueryRequest):
    messages = [
        {
            "role": "system",
            "content": (
                "你是研究助手。使用提供的工具來搜尋資料、摘要、並撰寫最終回答。"
                "請依序：先 search，再 summarize，最後 write_answer。"
            ),
        },
        {"role": "user", "content": req.question},
    ]

    for i in range(MAX_ITER):
        response = httpx.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={"model": OLLAMA_MODEL, "messages": messages, "tools": TOOLS, "stream": False},
            timeout=120,
        ).json()

        msg = response["message"]
        messages.append(msg)

        if not msg.get("tool_calls"):
            answer = msg.get("content", "（無回答）")
            print(f"[ITER {i+1}] LLM → FINAL: {answer[:80]}{'...' if len(answer) > 80 else ''}", flush=True)
            return {"answer": answer}

        for tc in msg["tool_calls"]:
            name = tc["function"]["name"]
            args = tc["function"]["arguments"]
            if isinstance(args, str):
                args = json.loads(args)
            print(f"[ITER {i+1}] LLM → TOOL: {name}({json.dumps(args, ensure_ascii=False)})", flush=True)
            result = dispatch(name, args)
            preview = result[:120] + "..." if len(result) > 120 else result
            print(f"[ITER {i+1}] TOOL → LLM: {preview}", flush=True)
            messages.append({"role": "tool", "content": result})

    return {"answer": "（超過最大迭代次數）"}
