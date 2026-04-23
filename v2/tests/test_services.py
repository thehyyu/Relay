"""
v2a FastAPI endpoint contract tests.
用 TestClient 測試各服務的輸入輸出格式，不啟動真實容器，不呼叫 LLM。
"""
import json
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


# --- Search ---

def test_search_returns_documents():
    mock_collection = MagicMock()
    mock_collection.query.return_value = {"documents": [["doc1", "doc2", "doc3"]]}

    with patch("v2.services.search.main._collection", mock_collection):
        from v2.services.search.main import app
        client = TestClient(app)
        response = client.post("/search", json={"query": "K8s"})

    assert response.status_code == 200
    assert "documents" in response.json()
    assert isinstance(response.json()["documents"], list)


def test_search_health():
    from v2.services.search.main import app
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}


# --- Summarize ---

def test_summarize_returns_summary():
    mock_response = MagicMock()
    mock_response.json.return_value = {"message": {"content": "摘要內容"}}

    with patch("v2.services.summarize.main.httpx.post", return_value=mock_response):
        from v2.services.summarize.main import app
        client = TestClient(app)
        response = client.post("/summarize", json={
            "question": "什麼是 K8s？",
            "documents": ["文件一", "文件二"],
        })

    assert response.status_code == 200
    assert response.json()["summary"] == "摘要內容"


def test_summarize_health():
    from v2.services.summarize.main import app
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}


# --- Write ---

def test_write_returns_answer():
    mock_response = MagicMock()
    mock_response.json.return_value = {"message": {"content": "最終回答"}}

    with patch("v2.services.write.main.httpx.post", return_value=mock_response):
        from v2.services.write.main import app
        client = TestClient(app)
        response = client.post("/write", json={
            "question": "什麼是 K8s？",
            "summary": "K8s 是容器編排平台",
        })

    assert response.status_code == 200
    assert response.json()["answer"] == "最終回答"


def test_write_health():
    from v2.services.write.main import app
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}


# --- Orchestrator dispatch ---

def test_orchestrator_dispatch_search():
    mock_response = MagicMock()
    mock_response.json.return_value = {"documents": ["doc1"]}

    with patch("v2.services.orchestrator.main.httpx.post", return_value=mock_response):
        from v2.services.orchestrator.main import dispatch
        result = dispatch("search", {"query": "K8s"})

    assert "doc1" in result


def test_orchestrator_dispatch_unknown():
    from v2.services.orchestrator.main import dispatch
    result = dispatch("nonexistent", {})
    assert "unknown" in result
