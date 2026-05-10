"""
main.py — Jyotish AI Backend
FastAPI + pyswisseph + OpenCage + Anthropic Claude

Environment variables required (.env):
  ANTHROPIC_API_KEY   = sk-ant-...
  OPENCAGE_API_KEY    = your_opencage_key
  ALLOWED_ORIGIN      = https://your-vercel-app.vercel.app  (or * for dev)

Run locally:
  uvicorn main:app --reload --port 8000

STATELESS DESIGN (v2)
  /api/chart now returns system_prompt in the response.
  The frontend stores it and sends it back on every /api/ask call.
  This eliminates "Session not found" errors caused by Railway
  container restarts wiping the in-memory SESSIONS dict.
  SESSIONS is kept as an optional short-lived cache only.
"""

import os
import json
import uuid
import asyncio
from datetime import datetime
from typing import AsyncGenerator

import httpx
import pytz
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from vedic_calc import calculate_chart
from prompt_builder import build_system_prompt

load_dotenv()

ANTHROPIC_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
OPENCAGE_KEY    = os.getenv("OPENCAGE_API_KEY", "")
ALLOWED_ORIGIN  = os.getenv("ALLOWED_ORIGIN", "*")
CLAUDE_MODEL    = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")
MAX_TOKENS      = int(os.getenv("MAX_TOKENS", "2500"))

# ─── In-memory session store ──────────────────────────────────────────────────
# { session_id: { "system_prompt": str, "birth_summary": dict } }
# At 10-12 users/mo this is perfectly adequate.
# When you scale to 100+: swap this dict for Redis.
SESSIONS: dict[str, dict] = {}

# ─── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(title="Jyotish AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN] if ALLOWED_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Pydantic models ──────────────────────────────────────────────────────────

class BirthInput(BaseModel):
    name:     str = ""
    dob:      str          # "YYYY-MM-DD"
    tob:      str          # "HH:MM"
    pob:      str          # "Nagpur, India"
    gender:   str = ""
    language: str = "English"


class AskInput(BaseModel):
    session_id:    str       = ""   # kept for backward compat; no longer required
    system_prompt: str       = ""   # preferred: client sends this back every time
    question:      str
    history:       list[dict] = []  # [{role: "user"|"assistant", content: str}]
    language:      str       = "English"


# ─── Geocoding + timezone helper ─────────────────────────────────────────────

async def geocode_city(city: str) -> dict:
    """
    Convert city name → lat, lng, timezone string via OpenCage.
    Returns { lat, lng, timezone, formatted_address }
    """
    if not OPENCAGE_KEY:
        raise HTTPException(500, "OPENCAGE_API_KEY not configured")

    url = "https://api.opencagedata.com/geocode/v1/json"
    params = {
        "q": city,
        "key": OPENCAGE_KEY,
        "limit": 1,
        "no_annotations": 0,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    if not data.get("results"):
        raise HTTPException(400, f"Location not found: {city}")

    result   = data["results"][0]
    geometry = result["geometry"]
    timezone = result["annotations"]["timezone"]["name"]

    return {
        "lat":               geometry["lat"],
        "lng":               geometry["lng"],
        "timezone":          timezone,
        "formatted_address": result["formatted"],
    }


def local_to_utc(dob: str, tob: str, timezone_str: str) -> datetime:
    """
    Convert local birth date + time + timezone → UTC datetime (naive).
    dob: "YYYY-MM-DD"
    tob: "HH:MM"
    """
    tz       = pytz.timezone(timezone_str)
    dt_str   = f"{dob} {tob}:00"
    local_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    local_dt = tz.localize(local_dt)
    utc_dt   = local_dt.astimezone(pytz.utc)
    return utc_dt.replace(tzinfo=None)   # naive UTC for pyswisseph


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "model": CLAUDE_MODEL}


@app.post("/api/chart")
async def create_chart(birth: BirthInput):
    """
    1. Geocode the place of birth
    2. Convert local birth time → UTC
    3. Calculate Vedic chart (D1, D9, D10)
    4. Build full system prompt
    5. Store session and return session_id + chart summary
    """
    # Geocode
    try:
        geo = await geocode_city(birth.pob)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Geocoding failed: {str(e)}")

    # Convert to UTC
    try:
        birth_utc = local_to_utc(birth.dob, birth.tob, geo["timezone"])
    except Exception as e:
        raise HTTPException(400, f"Invalid date/time: {str(e)}")

    # Calculate chart
    try:
        chart = calculate_chart(birth_utc, lat=geo["lat"], lon=geo["lng"])
    except Exception as e:
        raise HTTPException(500, f"Chart calculation failed: {str(e)}")

    # Build system prompt
    try:
        system_prompt = build_system_prompt(
            chart,
            birth_dt=birth_utc,
            query_date=datetime.utcnow(),
            language=birth.language,
        )
    except Exception as e:
        raise HTTPException(500, f"Prompt build failed: {str(e)}")

    # Store session
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {
        "system_prompt": system_prompt,
        "birth_data": {
            "name":    birth.name,
            "dob":     birth.dob,
            "tob":     birth.tob,
            "pob":     geo["formatted_address"],
            "gender":  birth.gender,
            "language": birth.language,
            "lat":     geo["lat"],
            "lng":     geo["lng"],
            "timezone": geo["timezone"],
        }
    }

    # Build a clean summary to return to the UI
    ct  = chart["core_trinity"]
    d1  = chart["d1"]

    summary = {
        "session_id":    session_id,
        # ── Stateless fix: return system_prompt so the client can ──────────
        # re-send it on every /api/ask request. This survives server restarts.
        "system_prompt": system_prompt,
        "name":          birth.name or "Friend",
        "ascendant":     ct["ascendant"]["sign"],
        "asc_nakshatra": ct["ascendant"]["nakshatra"],
        "asc_pada":      ct["ascendant"]["pada"],
        "sun_sign":      ct["sun"]["sign"],
        "moon_sign":     ct["moon"]["sign"],
        "moon_nakshatra": ct["moon"]["nakshatra"],
        "moon_pada":     ct["moon"]["pada"],
        "location":      geo["formatted_address"],
        "timezone":      geo["timezone"],
        "language":      birth.language,
    }
    return summary


@app.post("/api/ask")
async def ask_question(req: AskInput):
    """
    Streaming endpoint.
    Takes session_id + user question + conversation history.
    Returns Server-Sent Events with Claude's streamed response.
    """
    # ── Stateless mode: client sends system_prompt directly ──────────────
    # This survives container restarts (e.g. Railway deploys).
    # Fall back to in-memory SESSIONS cache for older clients.
    if req.system_prompt:
        system_prompt = req.system_prompt
    elif req.session_id and req.session_id in SESSIONS:
        system_prompt = SESSIONS[req.session_id]["system_prompt"]
    else:
        raise HTTPException(404, "Session not found. Please re-enter birth details.")

    # ── Inject language instruction at the top of the system prompt ───────
    language = req.language or "English"
    if language and language.lower() != "english":
        lang_instruction = (
            f"LANGUAGE INSTRUCTION: You must respond entirely in {language}. "
            f"All your answers, explanations, and astrological insights must be written in {language}. "
            f"Do not mix languages — respond only in {language}.\n\n"
        )
        system_prompt = lang_instruction + system_prompt

    if not ANTHROPIC_KEY:
        raise HTTPException(500, "ANTHROPIC_API_KEY not configured")

    # Build messages array — include history + new question
    messages = []
    for msg in req.history:
        if msg.get("role") in ("user", "assistant") and msg.get("content"):
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": req.question})

    async def stream_claude() -> AsyncGenerator[str, None]:
        headers = {
            "x-api-key":         ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        }
        payload = {
            "model":      CLAUDE_MODEL,
            "max_tokens": MAX_TOKENS,
            "system":     system_prompt,
            "messages":   messages,
            "stream":     True,
        }

        try:
            async with httpx.AsyncClient(timeout=90) as client:
                async with client.stream(
                    "POST",
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        error_msg = body.decode()
                        yield f"data: {json.dumps({'error': error_msg})}\n\n"
                        return

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        raw = line[6:].strip()
                        if raw == "[DONE]":
                            break
                        try:
                            event = json.loads(raw)
                        except json.JSONDecodeError:
                            continue

                        etype = event.get("type")

                        if etype == "content_block_delta":
                            delta = event.get("delta", {})
                            if delta.get("type") == "text_delta":
                                text = delta.get("text", "")
                                if text:
                                    yield f"data: {json.dumps({'text': text})}\n\n"

                        elif etype == "message_stop":
                            yield f"data: {json.dumps({'done': True})}\n\n"
                            break

                        elif etype == "error":
                            err = event.get("error", {}).get("message", "Unknown error")
                            yield f"data: {json.dumps({'error': err})}\n\n"
                            break

        except httpx.ReadTimeout:
            yield f"data: {json.dumps({'error': 'Claude response timed out. Please try again.'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        stream_claude(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",     # important for nginx proxies
        }
    )
