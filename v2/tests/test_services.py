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


# --- Orchestrator: clients.make_dispatch ---

def test_clients_dispatch_search():
    from clients import make_dispatch
    mock_response = MagicMock()
    mock_response.json.return_value = {"documents": ["doc1"]}

    with patch("clients.httpx.post", return_value=mock_response):
        dispatch = make_dispatch("http://search:8001", "http://summarize:8002", "http://write:8003")
        result = dispatch("search", {"query": "K8s"})

    assert "doc1" in result


def test_clients_dispatch_unknown():
    from clients import make_dispatch
    dispatch = make_dispatch("http://search:8001", "http://summarize:8002", "http://write:8003")
    result = dispatch("nonexistent", {})
    assert "unknown" in result


# --- Orchestrator: react.run_react_loop ---

def test_react_loop_returns_on_no_tool_calls():
    from react import run_react_loop

    def mock_chat(messages):
        return {"role": "assistant", "content": "最終回答"}

    result = run_react_loop("什麼是 K8s？", dispatch=lambda n, a: "", chat_fn=mock_chat)
    assert result == "最終回答"


def test_react_loop_dispatches_tool_calls():
    from react import run_react_loop

    call_log = []

    def mock_chat(messages):
        if len(messages) == 2:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": "search", "arguments": {"query": "K8s"}}}],
            }
        return {"role": "assistant", "content": "done"}

    def mock_dispatch(name, args):
        call_log.append(name)
        return "mocked result"

    result = run_react_loop("test", dispatch=mock_dispatch, chat_fn=mock_chat)
    assert "search" in call_log
    assert result == "done"


def test_react_loop_max_iter():
    from react import run_react_loop, MAX_ITER

    def always_tool(messages):
        return {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": "search", "arguments": {"query": "x"}}}],
        }

    result = run_react_loop("test", dispatch=lambda n, a: "r", chat_fn=always_tool)
    assert result == "（超過最大迭代次數）"
