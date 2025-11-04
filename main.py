from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import re

app = FastAPI(title="Tommy Backend API", version="1.0.0")

# Allow all origins so the Chrome extension can call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConciseRequest(BaseModel):
    question: Optional[str] = ""
    title: Optional[str] = ""
    text: Optional[str] = ""
    selection: Optional[str] = ""
    hostname: Optional[str] = ""


class ConciseResponse(BaseModel):
    answer: str


@app.get("/test")
def test():
    return {"ok": True}


@app.post("/concise", response_model=ConciseResponse)
def concise(req: ConciseRequest):
    text = (req.selection or "").strip() or (req.title or "").strip() or (req.text or "")[:500]
    q = (req.question or "").strip()

    # If prompt asks for one word explicitly
    if re.search(r"\b(one\s*word|single\s*word)\b", q, flags=re.I):
        w = top_keyword(text)
        return {"answer": w or "OK"}

    # If short selection, produce one word
    if len(text.split()) <= 3:
        return {"answer": top_keyword(text) or text or "OK"}

    # Otherwise produce one short sentence (max ~12 words)
    sentence = summarize_to_one_sentence(text, q)
    return {"answer": sentence}


STOP = set(
    "the a an and or of to in on for with is are was were be as by at from that this it its into over under than then but so if".split()
)


def top_keyword(text: str) -> str:
    words = re.findall(r"[a-zA-Z][a-zA-Z\-']+", text.lower())
    words = [w for w in words if w not in STOP]
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    top = max(freq.items(), key=lambda kv: kv[1])[0] if freq else ""
    return top.capitalize() if top else ""


def summarize_to_one_sentence(text: str, question: str) -> str:
    sentences = re.findall(r"[^.!?]+[.!?]", text) or [text]
    s = sentences[0].strip() if sentences else text.strip()
    if question:
        q_words = re.findall(r"[a-zA-Z][a-zA-Z\-']+", question.lower())[:5]
        scored = [(sn.strip(), sum(1 for qw in q_words if qw in sn.lower())) for sn in sentences]
        scored.sort(key=lambda x: x[1], reverse=True)
        if scored and scored[0][1] > 0:
            s = scored[0][0]
    words = s.split()[:12]
    short = " ".join(words)
    if not re.search(r"[.!?]$", short):
        short += "."
    return short


# Utility endpoint mirroring the algorithm can be extended later to call LLMs
