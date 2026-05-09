# Jyotish AI — Vedic Astrology Advisor

An AI-powered Vedic astrology chatbot. Enter birth details → receive a personalised reading grounded in real Swiss Ephemeris calculations (D1/D9/D10 charts, Vimshottari Dasha, Yoga detection) powered by Claude AI.

**Stack:** FastAPI + pyswisseph (backend on Railway) · React + Vite (frontend on Vercel)

---

## Project Structure

```
AstroChatBot/
├── .gitignore
├── README.md
├── backend/
│   ├── main.py              # FastAPI server — geocoding, chart endpoint, Claude streaming
│   ├── vedic_calc.py        # Swiss Ephemeris engine — D1/D9/D10, nakshatras, yogas
│   ├── prompt_builder.py    # Vimshottari Dasha + yoga detection + system prompt builder
│   ├── requirements.txt
│   ├── Procfile             # Railway start command (fallback)
│   ├── railway.json         # Railway deployment config
│   ├── nixpacks.toml        # Tells Railway to install gcc for pyswisseph (C extension)
│   ├── .env.example         # ← copy to .env, fill in keys, never commit .env
│   └── ephemeris/
│       ├── seas_18.se1      # Swiss Ephemeris asteroid data
│       ├── semo_18.se1      # Swiss Ephemeris moon data
│       └── sepl_18.se1      # Swiss Ephemeris planet data
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── main.jsx
    │   ├── index.css
    │   └── components/
    │       ├── BirthForm.jsx
    │       ├── ChatInterface.jsx
    │       └── Stars.jsx
    ├── public/
    ├── index.html
    ├── package.json
    ├── package-lock.json
    ├── vite.config.js
    ├── vercel.json          # SPA routing fix for Vercel
    └── .env.example         # ← copy to .env.local, fill in URL, never commit .env.local
```

---

## API Keys You Need

| Key | Where to get | Free tier |
|-----|-------------|-----------|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | Pay-per-use (~$2–5/mo for light use) |
| `OPENCAGE_API_KEY` | [opencagedata.com](https://opencagedata.com) | 2,500 requests/day free |

---

## Local Development

### 1. Backend

```bash
cd backend

# Create your local env file (never committed)
cp .env.example .env
# Edit .env — fill in ANTHROPIC_API_KEY, OPENCAGE_API_KEY
# Set ALLOWED_ORIGIN=http://localhost:5173

# Install dependencies (Python 3.11+ required)
pip install -r requirements.txt

# Run
uvicorn main:app --reload --port 8000
```

Test it: open `http://localhost:8000/health` — should return `{"status":"ok"}`.

### 2. Frontend

```bash
cd frontend

# Create your local env file (never committed)
cp .env.example .env.local
# Edit .env.local — set VITE_API_URL=http://localhost:8000

npm install
npm run dev
```

App runs at: `http://localhost:5173`

> **Tip:** The `vite.config.js` dev proxy means you can also leave `VITE_API_URL` empty locally — Vite will forward `/api/*` to `localhost:8000` automatically.

---

## Deployment

### Step 1 — Push to GitHub

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_USERNAME/AstroChatBot.git
git push -u origin main
```

Make sure `.env` and `.env.local` are **not** in the commit — `.gitignore` already covers this. Double-check with `git status` before pushing.

---

### Step 2 — Deploy Backend to Railway

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Select your `AstroChatBot` repo
3. Railway will detect the project. When asked, set **Root Directory** to `backend`
4. Railway will find `nixpacks.toml` and `railway.json` automatically

**Add these environment variables in the Railway dashboard** (Settings → Variables):

| Variable | Value |
|----------|-------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` (your real key) |
| `OPENCAGE_API_KEY` | your opencage key |
| `ALLOWED_ORIGIN` | `*` for now (update after Vercel deploy) |
| `CLAUDE_MODEL` | `claude-sonnet-4-5` |
| `MAX_TOKENS` | `2000` |

5. Click **Deploy**. Wait for the build to complete (2–3 min first time).
6. Copy your Railway URL — looks like `https://astrochatbot-production.up.railway.app`
7. **Test it:** open `https://your-railway-url.railway.app/health` — should return `{"status":"ok"}`

---

### Step 3 — Deploy Frontend to Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New Project** → import your GitHub repo
2. Set **Root Directory** to `frontend`
3. Framework preset will auto-detect as **Vite**
4. **Add environment variable:**

| Variable | Value |
|----------|-------|
| `VITE_API_URL` | `https://your-railway-url.railway.app` (no trailing slash) |

5. Click **Deploy**. Vercel runs `npm run build` automatically.
6. Copy your Vercel URL — looks like `https://astrochatbot.vercel.app`

---

### Step 4 — Lock Down CORS

Go back to Railway → Variables → update `ALLOWED_ORIGIN` to your exact Vercel URL:

```
ALLOWED_ORIGIN=https://astrochatbot.vercel.app
```

Railway will redeploy automatically.

---

## Cost Estimate (10–20 users/month)

| Service | Cost |
|---------|------|
| Vercel | Free |
| Railway | ~$5/mo (Hobby plan) |
| OpenCage | Free |
| Anthropic API | ~$2–5/mo |
| **Total** | **~$7–10/mo** |

---

## Troubleshooting

**`pyswisseph` build fails on Railway**
The `nixpacks.toml` in `backend/` tells Railway to install `gcc` before pip. If you still see build errors, go to Railway → Settings → Build and add the environment variable `NIXPACKS_PYTHON_VERSION=3.11`.

**CORS errors in browser console**
`ALLOWED_ORIGIN` in Railway does not match your Vercel URL exactly. Update it and redeploy.

**"Session not found" after a while**
Sessions are stored in memory. Railway restarts the container periodically (free tier). This is expected — the user just re-enters birth details. For persistence, add a Redis addon in Railway.

**`VITE_API_URL` not working**
Vercel only injects env vars that start with `VITE_` into the frontend build. Make sure you added it in Vercel's dashboard under **Environment Variables**, not somewhere else.

---

## Scaling Beyond 100 Users

- **Sessions:** Swap the in-memory `SESSIONS` dict in `main.py` for Redis (Railway has a Redis addon, ~$5/mo)
- **Queue:** Add Celery + Redis for background chart calculations if response times grow
- **Ephemeris:** The `.se1` files are included in the repo (~2MB total). For very high traffic, move them to object storage and mount at runtime.
