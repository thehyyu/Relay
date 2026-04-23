import json
from unittest.mock import patch, MagicMock
from agents.orchestrator import dispatch, orchestrator, MAX_ITER


# --- dispatch 路由 ---

def test_dispatch_search():
    with patch("agents.orchestrator.search_agent", return_value=["doc1"]) as mock:
        result = dispatch("search", {"query": "K8s"})
        mock.assert_called_once_with("K8s")
        assert "doc1" in result


def test_dispatch_summarize():
    with patch("agents.orchestrator.summarize_agent", return_value="summary") as mock:
        result = dispatch("summarize", {"question": "q", "documents": ["d"]})
        mock.assert_called_once_with("q", ["d"])
        assert result == "summary"


def test_dispatch_write_answer():
    with patch("agents.orchestrator.write_agent", return_value="answer") as mock:
        result = dispatch("write_answer", {"question": "q", "summary": "s"})
        mock.assert_called_once_with("q", "s")
        assert result == "answer"


def test_dispatch_unknown():
    result = dispatch("nonexistent", {})
    assert "unknown" in result


# --- loop 終止條件 ---

def _mock_response(content=None, tool_calls=None):
    msg = {"role": "assistant"}
    if content:
        msg["content"] = content
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return MagicMock(json=MagicMock(return_value={"message": msg}))


def test_loop_terminates_on_no_tool_calls():
    """成功路徑：LLM 回傳無 tool_call，loop 結束並回傳 content。"""
    with patch("agents.orchestrator.httpx.post", return_value=_mock_response(content="最終答案")):
        result = orchestrator("什麼是 K8s？")
    assert result == "最終答案"


def test_loop_terminates_on_max_iter():
    """失敗路徑：LLM 持續呼叫 tool 超過 MAX_ITER，強制結束。"""
    tool_response = _mock_response(tool_calls=[{
        "function": {"name": "search", "arguments": {"query": "test"}}
    }])
    with patch("agents.orchestrator.httpx.post", return_value=tool_response):
        with patch("agents.orchestrator.search_agent", return_value=["doc"]):
            result = orchestrator("問題")
    assert result == "（超過最大迭代次數）"
