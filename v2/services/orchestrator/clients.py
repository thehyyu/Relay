import json
import httpx
from typing import Callable
from tenacity import retry, stop_after_attempt, wait_exponential


def make_dispatch(
    search_url: str,
    summarize_url: str,
    write_url: str,
    request_id: str = "",
) -> Callable[[str, dict], str]:
    headers = {"X-Request-ID": request_id} if request_id else {}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def call_search(query: str) -> str:
        r = httpx.post(f"{search_url}/search", json={"query": query}, headers=headers, timeout=120)
        r.raise_for_status()
        return json.dumps(r.json()["documents"], ensure_ascii=False)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def call_summarize(question: str, documents: list) -> str:
        r = httpx.post(
            f"{summarize_url}/summarize",
            json={"question": question, "documents": documents},
            headers=headers,
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["summary"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def call_write(question: str, summary: str) -> str:
        r = httpx.post(
            f"{write_url}/write",
            json={"question": question, "summary": summary},
            headers=headers,
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["answer"]

    def dispatch(tool_name: str, args: dict) -> str:
        if tool_name == "search":
            return call_search(args["query"])
        if tool_name == "summarize":
            return call_summarize(args["question"], args["documents"])
        if tool_name == "write_answer":
            return call_write(args["question"], args["summary"])
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
