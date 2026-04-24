import os
import uuid
from fastapi import FastAPI, Request
from pydantic import BaseModel
import react  # type: ignore[import]
import clients  # type: ignore[import]

app = FastAPI()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
SEARCH_URL = os.getenv("SEARCH_URL", "http://search:8001")
SUMMARIZE_URL = os.getenv("SUMMARIZE_URL", "http://summarize:8002")
WRITE_URL = os.getenv("WRITE_URL", "http://write:8003")


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


class QueryRequest(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/live")
def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready():
    return {"status": "ok"}


@app.post("/query")
async def query(req: QueryRequest, request: Request):
    request_id = request.state.request_id
    print(f"[{request_id}] START: {req.question[:60]}", flush=True)
    dispatch = clients.make_dispatch(SEARCH_URL, SUMMARIZE_URL, WRITE_URL, request_id=request_id)
    chat_fn = clients.make_chat_fn(OLLAMA_BASE_URL, react.OLLAMA_MODEL, react.TOOLS)
    try:
        answer = await react.run_react_loop(req.question, dispatch, chat_fn)
    except Exception as e:
        print(f"[{request_id}] ERROR: {type(e).__name__}: {e}", flush=True)
        raise
    print(f"[{request_id}] DONE: {answer[:60]}", flush=True)
    return {"answer": answer}
