import httpx
from dotenv import load_dotenv
import os

load_dotenv()

base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

response = httpx.post(
    f"{base_url}/api/chat",
    json={
        "model": "mistral:v0.3",
        "messages": [{"role": "user", "content": "Reply with one word: ready"}],
        "stream": False,
    },
    timeout=30,
)

print(response.json()["message"]["content"])
