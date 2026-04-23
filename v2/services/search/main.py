import os
import chromadb
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel

CHROMA_PATH = os.getenv("CHROMA_PATH", "/data/chroma_db")

_collection = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _collection
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    _collection = client.get_collection("software_architecture")
    # 預熱：第一次查詢會載入 ONNX embedding model，之後就快了
    _collection.query(query_texts=["warmup"], n_results=1)
    print("ChromaDB ready.", flush=True)
    yield


app = FastAPI(lifespan=lifespan)


class SearchRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/search")
def search(req: SearchRequest):
    results = _collection.query(query_texts=[req.query], n_results=3)
    return {"documents": results["documents"][0]}
