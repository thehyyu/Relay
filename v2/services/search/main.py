import os
import chromadb
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

CHROMA_PATH = os.getenv("CHROMA_PATH", "/data/chroma_db")

_collection = None
_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _collection, _ready
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    _collection = client.get_collection("software_architecture")
    _collection.query(query_texts=["warmup"], n_results=1)
    _ready = True
    print("ChromaDB ready.", flush=True)
    yield


app = FastAPI(lifespan=lifespan)


class SearchRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/live")
def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready():
    if not _ready:
        return JSONResponse(status_code=503, content={"status": "not ready"})
    return {"status": "ok"}


@app.post("/search")
def search(req: SearchRequest, request: Request):
    request_id = request.headers.get("X-Request-ID", "")
    if request_id:
        print(f"[{request_id}] search: {req.query[:60]}", flush=True)
    results = _collection.query(query_texts=[req.query], n_results=3)
    return {"documents": results["documents"][0]}
