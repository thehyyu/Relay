from .search import search_agent
from .summarize import summarize_agent
from .write import write_agent


def orchestrator(question: str) -> str:
    documents = search_agent(question)
    summary = summarize_agent(question, documents)
    answer = write_agent(question, summary)
    return answer
