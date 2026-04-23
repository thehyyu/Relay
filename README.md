# Relay

A multi-agent research system built to learn how the same business logic evolves across three deployment architectures.

The complexity budget is spent entirely on architecture — not business logic.

## What I'm learning

| Version | Deployment | Key concepts |
|---|---|---|
| v1 | Python monolith | Tool use, agent loop, ReAct pattern |
| v2a | FastAPI + Docker Compose | Microservices, containerization |
| v2b | minikube | Kubernetes, StatefulSet, rolling update |
| v3 | Hybrid serverless | Event-driven, message queue, cloud LLM |

Built from raw API (no AutoGen / LangGraph / CrewAI) — that's the point.

## Setup

```bash
cp .env.example .env   # fill in OLLAMA_BASE_URL
uv venv
uv pip install httpx python-dotenv
```

## Full spec

See [AGENTS.md](AGENTS.md).
