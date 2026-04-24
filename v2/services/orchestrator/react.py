import json
from typing import Callable

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

SYSTEM_PROMPT = (
    "你是研究助手。使用提供的工具來搜尋資料、摘要、並撰寫最終回答。"
    "請依序：先 search，再 summarize，最後 write_answer。"
)


def run_react_loop(
    question: str,
    dispatch: Callable[[str, dict], str],
    chat_fn: Callable[[list[dict]], dict],
) -> str:
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    for i in range(MAX_ITER):
        msg = chat_fn(messages)
        messages.append(msg)

        if not msg.get("tool_calls"):
            answer = msg.get("content", "（無回答）")
            print(f"[ITER {i+1}] LLM → FINAL: {answer[:80]}{'...' if len(answer) > 80 else ''}", flush=True)
            return answer

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

    return "（超過最大迭代次數）"
