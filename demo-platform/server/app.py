"""AgentNexLiFy Demo — Chat API Backend (FastAPI + Anthropic)."""

import os
import json
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Try to import Anthropic
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

api_key = os.environ.get("ANTHROPIC_API_KEY", "")
client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    if HAS_ANTHROPIC and api_key:
        client = anthropic.Anthropic(api_key=api_key)
        print(f"[API] Anthropic client initialized (key: ...{api_key[-6:]})")
    else:
        reason = "no API key" if HAS_ANTHROPIC else "anthropic package not installed"
        print(f"[API] Running without AI backend ({reason})")
    yield


app = FastAPI(title="AgentNexLiFy Demo API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    system: str = ""


@app.get("/api/health")
async def health():
    return {"status": "ok", "ai_enabled": client is not None}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    if not client:
        return {"error": "AI backend not configured. Set ANTHROPIC_API_KEY env var."}

    try:
        # Filter to only user/assistant messages for Claude API
        messages = [
            {"role": m.role, "content": m.content}
            for m in req.messages
            if m.role in ("user", "assistant")
        ]

        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            system=req.system or "",
            messages=messages,
        )

        text = response.content[0].text if response.content else "I'm sorry, I couldn't generate a response."
        return {"response": text}

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
