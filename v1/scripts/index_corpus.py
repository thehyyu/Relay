"""
一次性腳本：將 v1/corpus/ 的 markdown 文件 index 進 ChromaDB。
執行方式：PYTHONPATH=v1 python v1/scripts/index_corpus.py
"""
import os
import chromadb
from pathlib import Path

CORPUS_DIR = Path(__file__).parent.parent / "corpus"
CHROMA_PATH = Path(__file__).parent.parent / "chroma_db"


def main():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    # 若 collection 已存在則重建
    client.delete_collection("software_architecture") if "software_architecture" in [
        c.name for c in client.list_collections()
    ] else None
    collection = client.create_collection("software_architecture")

    docs, ids, metadatas = [], [], []
    for md_file in CORPUS_DIR.glob("*.md"):
        text = md_file.read_text(encoding="utf-8")
        # 依段落切分（空行分隔）
        chunks = [c.strip() for c in text.split("\n\n") if len(c.strip()) > 30]
        for i, chunk in enumerate(chunks):
            docs.append(chunk)
            ids.append(f"{md_file.stem}-{i}")
            metadatas.append({"source": md_file.name})

    collection.add(documents=docs, ids=ids, metadatas=metadatas)
    print(f"indexed {len(docs)} chunks from {len(list(CORPUS_DIR.glob('*.md')))} files")


if __name__ == "__main__":
    main()
