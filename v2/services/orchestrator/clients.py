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
    async def call_search(query: str) -> str:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{search_url}/search", json={"query": query}, headers=headers, timeout=120)
        r.raise_for_status()
        return json.dumps(r.json()["documents"], ensure_ascii=False)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    async def call_summarize(question: str, documents: list) -> str:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{summarize_url}/summarize",
                json={"question": question, "documents": documents},
                headers=headers,
                timeout=120,
            )
        r.raise_for_status()
        return r.json()["summary"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    async def call_write(question: str, summary: str) -> str:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{write_url}/write",
                json={"question": question, "summary": summary},
                headers=headers,
                timeout=120,
            )
        r.raise_for_status()
        return r.json()["answer"]

    async def dispatch(tool_name: str, args: dict) -> str:
        if tool_name == "search":
            return await call_search(args["query"])
        if tool_name == "summarize":
            return await call_summarize(args["question"], args["documents"])
        if tool_name == "write_answer":
            return await call_write(args["question"], args["summary"])
        return f"unknown tool: {tool_name}"

    return dispatch


def make_chat_fn(ollama_base_url: str, model: str, tools: list) -> Callable[[list[dict]], dict]:
    async def chat_fn(messages: list[dict]) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ollama_base_url}/api/chat",
                json={"model": model, "messages": messages, "tools": tools, "stream": False},
                timeout=300,
            )
        return response.json()["message"]
    return chat_fn
