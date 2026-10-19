from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
FAQ_PATH = ROOT / "data" / "faq.json"
app = FastAPI(title="AI Customer Support Assistant", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

class MessageRequest(BaseModel):
    message: str = Field(min_length=3, max_length=2000)

def load_faq() -> list[dict[str, Any]]:
    return json.loads(FAQ_PATH.read_text(encoding="utf-8"))

def classify(message: str) -> str:
    text = message.lower()
    if any(term in text for term in ["hacked", "compromised", "unauthorized access", "someone accessed", "suspicious login", "stolen account"]):
        return "security"
    if any(term in text for term in ["outage", "service down", "unavailable", "site is down", "system broken"]):
        return "service_outage"
    if any(term in text for term in ["invoice", "billing", "charged", "refund", "payment", "price"]):
        return "billing"
    if any(term in text for term in ["login", "log in", "sign in", "password", "can't access", "cannot access"]):
        return "account_access"
    return "general"

def retrieve(message: str, faq: list[dict[str, Any]]) -> list[dict[str, Any]]:
    text = message.lower()
    stop_words = {"can", "you", "the", "for", "and", "how", "what", "is", "are", "in", "on", "to", "a", "of", "my", "i", "it", "please", "with"}\n    tokens = set(re.findall(r"[a-z0-9]{3,}", text)) - stop_words
    ranked = []
    for item in faq:
        keywords = set(item["keywords"])
        keyword_hits = sum(1 for keyword in keywords if keyword in text or (len(keyword.split()) == 1 and keyword in tokens))
        title_hits = len(set(re.findall(r"[a-z0-9]{3,}", item["title"].lower())) & tokens)
        score = keyword_hits + title_hits
        if score:
            ranked.append((score, item))
    ranked.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
    return [{"id": item["id"], "title": item["title"], "source": item["source"], "score": score, "answer": item["answer"]}
            for score, item in ranked[:2]]

def respond(message: str) -> dict[str, Any]:
    category = classify(message)
    matches = retrieve(message, load_faq())
    high_risk = category in {"security", "service_outage"}
    if high_risk:
        next_action = "Escalate to a human support team"
    elif category == "billing":
        next_action = "Collect invoice reference and route to billing"
    else:
        next_action = "Review suggested reply before sending"
    if matches:
        reply = matches[0]["answer"]
    else:
        reply = "Thanks for contacting support. I couldn't find a confident answer in the current FAQ. I'll flag this for a support teammate to review."
    if high_risk:
        reply += " This issue should be reviewed by a human team; this demo does not contact anyone automatically."
    return {"category": category, "reply": reply, "sources": [{"title": m["title"], "source": m["source"], "score": m["score"]} for m in matches],
            "escalation_required": high_risk, "next_action": next_action, "sent": False}

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home():
    return (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")

@app.get("/health")
def health():
    return {"status": "ok", "faq_entries": len(load_faq())}

@app.get("/faq")
def faq():
    return {"items": [{"id": x["id"], "title": x["title"], "category": x["category"], "source": x["source"]} for x in load_faq()]}

@app.post("/message")
def message(request: MessageRequest):
    return respond(request.message)
