"""
main.py — Astro-gyaani Backend
FastAPI + pyswisseph + OpenCage + Anthropic Claude

Environment variables required (.env):
  ANTHROPIC_API_KEY   = sk-ant-...
  OPENCAGE_API_KEY    = your_opencage_key
  ALLOWED_ORIGIN      = https://your-vercel-app.vercel.app  (or * for dev)

Run locally:
  uvicorn main:app --reload --port 8000

STATELESS DESIGN (v2)
  /api/chart returns system_prompt in the response.
  The frontend stores it and sends it back on every /api/ask call.
  This eliminates "Session not found" errors caused by Railway
  container restarts wiping the in-memory SESSIONS dict.
  SESSIONS is kept as an optional short-lived cache only.

TOKEN OPTIMISATION (v4)
  • Base system prompt: D1 + D9 + D10 only (not all 19 charts).
  • Additional charts injected on first mention, kept for the session.
  • Pratyantar Dasha table removed from prompt (~350 tokens saved).
  • Prompt caching header: system prompt cached for 5 minutes.
    After the 1st call, input tokens drop ~80-90% on cache hits.

CACHING FIX (v4)
  Previously, include_references=False appended a large string to
  system_prompt, creating a *different* string that never matched the
  cached version — every call paid full input cost.

  Fix: the main system_prompt is sent as block[0] with cache_control.
  The no-references instruction is sent as a second, uncached block[1]
  only when needed.  Block[0] remains identical and always cache-hits.
"""

import os
import json
import uuid
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
from prompt_builder import build_system_prompt, detect_extra_charts

load_dotenv()

ANTHROPIC_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
OPENCAGE_KEY   = os.getenv("OPENCAGE_API_KEY", "")
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")
CLAUDE_MODEL   = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")
MAX_TOKENS     = int(os.getenv("MAX_TOKENS", "2500"))

# Plain-language instruction injected as a second (uncached) system block
# when include_references=False.  Kept separate so block[0] stays cached.
_NO_REF_INSTRUCTION = (
    "DISPLAY INSTRUCTION (MANDATORY): Answer the user's question "
    "using the complete chart knowledge above, but do NOT mention any "
    "specific planet names (Sun, Moon, Mars, etc.), sign names (Aries, "
    "Scorpio, etc.), house numbers, nakshatra names, dasha period names, "
    "yoga names, or any other astrological terminology in your response. "
    "Translate every insight into plain observations about the person's "
    "personality, tendencies, patterns, and practical guidance. "
    "Write as if you are a wise counsellor who just happens to understand "
    "this person deeply — no astrology-speak at all."
)

# ─── In-memory session store ──────────────────────────────────────────────────
SESSIONS: dict[str, dict] = {}

# ─── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(title="My Destiny", version="3.0.0")

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
    session_id:         str        = ""
    system_prompt:      str        = ""
    question:           str
    history:            list[dict] = []
    language:           str        = "English"
    include_references: bool       = True


# ─── Geocoding + timezone helper ─────────────────────────────────────────────

async def geocode_city(city: str) -> dict:
    """Convert city name → lat, lng, timezone via OpenCage."""
    if not OPENCAGE_KEY:
        raise HTTPException(500, "OPENCAGE_API_KEY not configured")

    url    = "https://api.opencagedata.com/geocode/v1/json"
    params = {"q": city, "key": OPENCAGE_KEY, "limit": 1, "no_annotations": 0}

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
    """Convert local birth date + time + timezone → naive UTC datetime."""
    tz       = pytz.timezone(timezone_str)
    dt_str   = f"{dob} {tob}:00"
    local_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    local_dt = tz.localize(local_dt)
    utc_dt   = local_dt.astimezone(pytz.utc)
    return utc_dt.replace(tzinfo=None)


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "model": CLAUDE_MODEL}


@app.post("/api/chart")
async def create_chart(birth: BirthInput):
    """Geocode → UTC → Vedic chart → system prompt → return to client."""
    try:
        geo = await geocode_city(birth.pob)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Geocoding failed: {str(e)}")

    try:
        birth_utc = local_to_utc(birth.dob, birth.tob, geo["timezone"])
    except Exception as e:
        raise HTTPException(400, f"Invalid date/time: {str(e)}")

    try:
        chart = calculate_chart(birth_utc, lat=geo["lat"], lon=geo["lng"])
    except Exception as e:
        raise HTTPException(500, f"Chart calculation failed: {str(e)}")

    birth_details = {
        "name": birth.name,
        "dob":  birth.dob,
        "tob":  birth.tob,
        "pob":  geo["formatted_address"],
    }

    try:
        system_prompt = build_system_prompt(
            chart,
            birth_dt=birth_utc,
            query_date=datetime.utcnow(),
            language=birth.language,
            birth_details=birth_details,
        )
    except Exception as e:
        raise HTTPException(500, f"Prompt build failed: {str(e)}")

    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {
        "chart":         chart,
        "birth_dt":      birth_utc,
        "loaded_charts": set(),
        "system_prompt": system_prompt,
        "birth_data": {
            "name":     birth.name,
            "dob":      birth.dob,
            "tob":      birth.tob,
            "pob":      geo["formatted_address"],
            "gender":   birth.gender,
            "language": birth.language,
            "lat":      geo["lat"],
            "lng":      geo["lng"],
            "timezone": geo["timezone"],
        },
        "birth_details": birth_details,
        "language": birth.language,
    }

    ct = chart["core_trinity"]

    return {
        "session_id":     session_id,
        "system_prompt":  system_prompt,
        "name":           birth.name or "Friend",
        # Birth details returned so the frontend can store them in the profile
        "dob":            birth.dob,
        "tob":            birth.tob,
        "pob":            geo["formatted_address"],
        # Chart identity
        "ascendant":      ct["ascendant"]["sign"],
        "asc_nakshatra":  ct["ascendant"]["nakshatra"],
        "asc_pada":       ct["ascendant"]["pada"],
        "sun_sign":       ct["sun"]["sign"],
        "moon_sign":      ct["moon"]["sign"],
        "moon_nakshatra": ct["moon"]["nakshatra"],
        "moon_pada":      ct["moon"]["pada"],
        "location":       geo["formatted_address"],
        "timezone":       geo["timezone"],
        "language":       birth.language,
    }


@app.post("/api/ask")
async def ask_question(req: AskInput):
    """
    Streaming endpoint with prompt caching + on-demand divisional charts.

    CACHING DESIGN
    ──────────────
    system_content[0]  = full system prompt  + cache_control (ephemeral)
    system_content[1]  = no-references instruction (only when needed, NO cache)

    Because block[0] is always identical for a given session, it hits the
    5-minute Anthropic prompt cache on every subsequent call regardless of
    whether include_references changes between turns.
    """
    language = req.language or "English"

    # ── Resolve system prompt ────────────────────────────────────────────
    session = SESSIONS.get(req.session_id) if req.session_id else None

    if session and "chart" in session:
        new_extras = detect_extra_charts(req.question)
        session["loaded_charts"].update(new_extras)
        extra_charts = list(session["loaded_charts"]) or None

        system_prompt = build_system_prompt(
            session["chart"],
            session["birth_dt"],
            query_date=datetime.utcnow(),
            language=language,
            extra_charts=extra_charts,
            birth_details=session.get("birth_details"),
        )
    elif req.system_prompt:
        system_prompt = req.system_prompt
    elif req.session_id and req.session_id in SESSIONS:
        system_prompt = SESSIONS[req.session_id]["system_prompt"]
    else:
        raise HTTPException(404, "Session not found. Please re-enter birth details.")

    if not ANTHROPIC_KEY:
        raise HTTPException(500, "ANTHROPIC_API_KEY not configured")

    # Build messages array (cap history at 10 turns to control token use)
    messages = []
    for msg in req.history[-10:]:
        if msg.get("role") in ("user", "assistant") and msg.get("content"):
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": req.question})

    async def stream_claude() -> AsyncGenerator[str, None]:
        headers = {
            "x-api-key":         ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            # Prompt caching beta — block[0] cached for 5 minutes
            "anthropic-beta":    "prompt-caching-2024-07-31",
            "content-type":      "application/json",
        }

        # Block[0]: the full system prompt — always cached
        system_content = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        # Block[1]: plain-language override — only when needed, never cached
        # This keeps block[0] identical across all calls so caching always hits.
        if not req.include_references:
            system_content.append({
                "type": "text",
                "text": _NO_REF_INSTRUCTION,
            })

        payload = {
            "model":      CLAUDE_MODEL,
            "max_tokens": MAX_TOKENS,
            "system":     system_content,
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
                        yield f"data: {json.dumps({'error': body.decode()})}\n\n"
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
            yield f"data: {json.dumps({'error': 'Response timed out. Please try again.'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        stream_claude(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
        }
    )
