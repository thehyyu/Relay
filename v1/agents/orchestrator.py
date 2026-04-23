"""
ReAct pattern：LLM 透過 tool use 自己決定要呼叫哪個 agent、何時結束。

loop：
  1. LLM 收到問題和可用 tools
  2. LLM 決定呼叫哪個 tool
  3. 執行 tool，將結果加回 messages
  4. 重複，直到 LLM 不再呼叫 tool（回傳最終答案）
  5. 若超過 MAX_ITER 則強制結束
"""
import httpx
import json
import os
from .search import search_agent
from .summarize import summarize_agent
from .write import write_agent

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
        results = search_agent(args["query"])
        return json.dumps(results, ensure_ascii=False)
    if tool_name == "summarize":
        return summarize_agent(args["question"], args["documents"])
    if tool_name == "write_answer":
        return write_agent(args["question"], args["summary"])
    return f"unknown tool: {tool_name}"


def orchestrator(question: str) -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    messages = [
        {
            "role": "system",
            "content": (
                "你是研究助手。使用提供的工具來搜尋資料、摘要、並撰寫最終回答。"
                "請依序：先 search，再 summarize，最後 write_answer。"
            ),
        },
        {"role": "user", "content": question},
    ]

    for _ in range(MAX_ITER):
        response = httpx.post(
            f"{base_url}/api/chat",
            json={"model": OLLAMA_MODEL, "messages": messages, "tools": TOOLS, "stream": False},
            timeout=120,
        ).json()

        msg = response["message"]
        messages.append(msg)

        if not msg.get("tool_calls"):
            return msg.get("content", "（無回答）")

        for tc in msg["tool_calls"]:
            name = tc["function"]["name"]
            args = tc["function"]["arguments"]
            if isinstance(args, str):
                args = json.loads(args)
            result = dispatch(name, args)
            messages.append({"role": "tool", "content": result})

    return "（超過最大迭代次數）"
