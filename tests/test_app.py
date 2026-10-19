from fastapi.testclient import TestClient
from app.main import app, classify, respond

client = TestClient(app)

def test_security_message_escalates():
    result = respond("I think someone accessed my account without permission")
    assert result["category"] == "security"
    assert result["escalation_required"] is True
    assert result["sent"] is False

def test_billing_message_returns_faq_source():
    result = respond("I was charged twice for my invoice")
    assert result["category"] == "billing"
    assert result["sources"]
    assert "Billing FAQ" in result["sources"][0]["source"]

def test_unknown_message_has_safe_fallback():
    result = respond("Can you explain the purple moon?")
    assert result["sources"] == []
    assert "couldn't find" in result["reply"]

def test_message_endpoint_validation():
    assert client.post("/message", json={"message": "hi"}).status_code == 422

def test_faq_endpoint():
    result = client.get("/faq")
    assert result.status_code == 200
    assert result.json()["items"]
