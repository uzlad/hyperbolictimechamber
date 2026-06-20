from app.chat import handle_chat
from app.models import ChatResponse

class FakeLLM:
    def chat(self, system: str, user: str, temperature: float = 0.2) -> str:
        return "Here is what I found based on your query."


def test_chat_returns_response_with_evidence(db):
    resp = handle_chat("tell me about Inception", db, FakeLLM())
    assert isinstance(resp, ChatResponse)
    assert resp.intent == "detail"
    assert any(e.title == "Inception" for e in resp.evidence)

def test_chat_recommend_intent(db):
    resp = handle_chat("recommend action movies", db, FakeLLM())
    assert resp.intent == "recommend"
    assert len(resp.evidence) > 0

def test_chat_llm_failure_returns_fallback(db):
    class FailingLLM:
        def chat(self, system, user, temperature=0.2):
            raise RuntimeError("Ollama unavailable")

    resp = handle_chat("tell me about Inception", db, FailingLLM())
    assert isinstance(resp.reply, str)
    assert len(resp.reply) > 0
