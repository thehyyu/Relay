import chromadb
from pathlib import Path

CHROMA_PATH = Path(__file__).parent.parent / "chroma_db"


def search_agent(query: str, n_results: int = 3) -> list[str]:
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_collection("software_architecture")
    results = collection.query(query_texts=[query], n_results=n_results)
    return results["documents"][0]
