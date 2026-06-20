import httpx

from app.config import settings

class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 120.0, #specified to allow for potential long responses from LLM
    ) -> None:
        self.base_url = (base_url or settings.ollama_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout = timeout

    def chat(self, system: str, user: str, temperature: float = 0.2) -> str: #set low to avoid hallucinations - limited context
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"temperature": temperature},
            "stream": False,
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            return response.json()["message"]["content"]

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.get(f"{self.base_url}/api/tags")
                if r.status_code != 200:
                    return False
                tags = r.json().get("models", [])
                return any(m.get("name", "").startswith(self.model.split(":")[0]) for m in tags)
        except Exception:
            return False
