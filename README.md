# AI-Powered Email Thread Detection, Geolocation & Forensic Intelligence Platform

A working full-stack scaffold: upload raw `.eml` files, reconstruct conversation
threads, geolocate every routing hop, detect authentication failures and
header-tampering anomalies, and generate exportable forensic reports (PDF /
JSON / CSV).

```
├── backend/     FastAPI + SQLAlchemy + PostgreSQL
├── frontend/    React (Vite) + Leaflet map
├── sample_emails/  Demo .eml files (one clean thread, one spoofed BEC attempt)
└── docker-compose.yml
```

## Quick start (Docker — recommended)

Requires Docker + Docker Compose.

```bash
docker compose up --build
```

- Backend API: http://localhost:8000 (interactive docs at `/docs`)
- Frontend: http://localhost:5173
- Postgres: localhost:5432 (user/pass/db: `forensics_user` / `forensics_pass` / `forensics_db`)

Then open http://localhost:5173, go to **Upload**, and drag in the files from
`sample_emails/` — try `sample_legit.eml` + `sample_legit_reply.eml` together
(they reconstruct into one thread) and `sample_spoofed_bec.eml` separately
(it's built to trip SPF/DKIM/DMARC failures and a hop-chronology anomaly).

## Running without Docker

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: for zero-setup local testing, set
#   DATABASE_URL=sqlite:///./forensics.db
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend expects the API at `http://localhost:8000` by default (see
`VITE_API_BASE_URL` in `docker-compose.yml`, or set it in a `frontend/.env`
file for local dev).

## How it works

1. **Parsing** (`backend/app/services/email_parser.py`) — reads raw `.eml`
   bytes with Python's standard `email` library, extracting headers, the
   `Received:` hop chain, and a cleaned body preview.
2. **Thread reconstruction** (`thread_engine.py`) — groups emails by
   `Message-ID` / `In-Reply-To` / `References`, falling back to normalized
   subject matching when linking headers are missing or stripped.
3. **Geolocation** (`geo_service.py`) — parses IPs out of each `Received:`
   header and resolves them to country/city/ISP via ip-api.com (swap in
   MaxMind GeoLite2 for production/offline use — see comments in the file).
4. **Spoofing & anomaly detection** (`auth_check.py`) — reads
   `Authentication-Results` for SPF/DKIM/DMARC verdicts, and flags routing
   hops whose timestamps run backwards (a sign of a forged/reordered header).
5. **AI narrative** (`ai_summary.py`) — calls the Claude API to turn the
   rule-based findings above into a plain-English investigator narrative
   (per-email risk explanation, and a whole-thread summary). Claude explains
   what the deterministic rules found; it does not decide the risk score
   itself, so the evidence trail stays auditable. Requires `ANTHROPIC_API_KEY`
   in `.env` — without it, both endpoints fall back to a clearly-labeled
   rule-based string instead of failing.
6. **Forensic reporting** (`report_generator.py`) — compiles findings (rules
   + AI narrative) into a JSON record, SHA-256 hashes both the original file
   and the findings record for chain-of-custody, and renders a PDF report
   on demand.

## API overview

| Endpoint | Purpose |
|---|---|
| `POST /api/emails/upload` | Upload one or more `.eml` files |
| `GET /api/threads` | List reconstructed threads, highest risk first |
| `GET /api/threads/{id}` | Thread detail with all emails |
| `POST /api/threads/{id}/summarize` | Claude-generated thread summary |
| `GET /api/geo/{email_id}/hops` | Geolocated routing hop chain |
| `POST /api/reports/{email_id}/generate` | Generate a forensic report (includes Claude risk narrative) |
| `GET /api/reports/{report_id}/download/{pdf\|json\|csv}` | Export |

Full interactive docs at `/docs` once the backend is running.

## Notes / known limitations (hackathon scope)

- **Set `ANTHROPIC_API_KEY` in `backend/.env`** to enable the AI narrative
  features (thread summary + per-email risk narrative). Without it, those
  fields fall back to a labeled rule-based string — the rest of the
  platform still works, but slide claims about Claude integration won't be
  demonstrable live without a key.
- Geolocation uses the free ip-api.com endpoint, which is rate-limited
  (~45 req/min) and has no API key — fine for a demo, swap for MaxMind
  GeoLite2 or IPinfo for anything higher-volume.
- Thread reconstruction's linking is Message-ID/In-Reply-To/References with
  a normalized-subject fallback (not sentence-embeddings) — that upgrade's
  seam is `thread_engine.find_thread_key()`, and a trained BEC/phishing
  classifier is a separate future upgrade from the current rule-based
  scoring in `auth_check.py`.
- No authentication/multi-tenant support yet — add before deploying beyond
  a local demo.
