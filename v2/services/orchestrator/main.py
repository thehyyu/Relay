import os
from fastapi import FastAPI
from pydantic import BaseModel
import react  # type: ignore[import]
import clients  # type: ignore[import]

app = FastAPI()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
SEARCH_URL = os.getenv("SEARCH_URL", "http://search:8001")
SUMMARIZE_URL = os.getenv("SUMMARIZE_URL", "http://summarize:8002")
WRITE_URL = os.getenv("WRITE_URL", "http://write:8003")


class QueryRequest(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query")
def query(req: QueryRequest):
    dispatch = clients.make_dispatch(SEARCH_URL, SUMMARIZE_URL, WRITE_URL)
    chat_fn = clients.make_chat_fn(OLLAMA_BASE_URL, react.OLLAMA_MODEL, react.TOOLS)
    answer = react.run_react_loop(req.question, dispatch, chat_fn)
    return {"answer": answer}
