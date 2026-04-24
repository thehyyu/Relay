import json
import httpx
from typing import Callable


def make_dispatch(search_url: str, summarize_url: str, write_url: str) -> Callable[[str, dict], str]:
    def dispatch(tool_name: str, args: dict) -> str:
        if tool_name == "search":
            r = httpx.post(f"{search_url}/search", json={"query": args["query"]}, timeout=120)
            return json.dumps(r.json()["documents"], ensure_ascii=False)
        if tool_name == "summarize":
            r = httpx.post(
                f"{summarize_url}/summarize",
                json={"question": args["question"], "documents": args["documents"]},
                timeout=60,
            )
            return r.json()["summary"]
        if tool_name == "write_answer":
            r = httpx.post(
                f"{write_url}/write",
                json={"question": args["question"], "summary": args["summary"]},
                timeout=60,
            )
            return r.json()["answer"]
        return f"unknown tool: {tool_name}"
    return dispatch


def make_chat_fn(ollama_base_url: str, model: str, tools: list) -> Callable[[list[dict]], dict]:
    def chat_fn(messages: list[dict]) -> dict:
        response = httpx.post(
            f"{ollama_base_url}/api/chat",
            json={"model": model, "messages": messages, "tools": tools, "stream": False},
            timeout=120,
        ).json()
        return response["message"]
    return chat_fn
