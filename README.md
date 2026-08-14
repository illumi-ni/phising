# Phishing Simulation & Benchmarking Web App

A research tool for generating synthetic phishing emails, building a human-written baseline, and benchmarking defensive detection — with an analytics dashboard.

> **Purpose & safety:** This project generates *synthetic, fictional* phishing-style emails for a **controlled lab research environment** only. They are never sent to real people. The LLM system prompt explicitly labels all content as research/synthetic.

---

## Architecture

```
┌────────────┐      ┌────────────┐      ┌────────────┐
│  frontend  │ ───▶ │  backend   │ ───▶ │    db      │
│ Next.js 14 │ HTTP │  FastAPI   │ SQL  │ PostgreSQL │
│   :3000    │      │   :8000    │      │   :5432    │
└────────────┘      └─────┬──────┘      └────────────┘
                          │  imports (PYTHONPATH=/ml)
                   ┌──────▼──────┐      ┌─────────────┐
                   │   /ml       │ ───▶ │  LLM API    │
                   │ NLP modules │      │ (Groq, opt.)│
                   └─────────────┘      └─────────────┘
```

- **frontend/** — Next.js 14 (App Router) + TypeScript + Tailwind. Pages: Home, Scenarios, Human Baseline, Dashboard.
- **backend/** — FastAPI + SQLAlchemy + Alembic. REST API for scenarios, email generation, imports, labeling, evaluation, detection, exports.
- **ml/** — Python NLP/ML modules (`tactic_labeler.py`, `evaluator.py`, `classifier.py`), imported by the backend at runtime.
- **docker-compose.yml** — wires up `frontend`, `backend`, and `db` (PostgreSQL 16).

---

## Prerequisites

- **Docker Desktop** (or Docker Engine + Compose) — with the engine **running**.
  - On Windows: Docker Desktop uses WSL2. If containers fail to start, check that WSL is healthy: `wsl --status` (an admin may need to restart `WSLService` or reboot).
- ~4 GB free disk space (backend image includes ML libraries — PyTorch, sentence-transformers).
- Git (optional, to clone).

---

## Quick start (Docker — recommended)

### Step 1 — Get the code

```bash
git clone <this-repo-url> phising
cd phising
```

### Step 2 — Create the environment file

`.env` is **not** committed (it holds secrets). Create it from the template:

```bash
cp .env.example .env
```

Open `.env` and optionally set `LLM_API_KEY` (see [LLM email generation](#llm-email-generation)). The default values work out of the box.

### Step 3 — Build and start all services

```bash
docker-compose up --build
```

- **First build takes 10–30 min** (backend installs ML dependencies, including PyTorch). Later builds are fast.
- Use `-d` to run in the background: `docker-compose up --build -d`.

When ready you should see three containers:

| Service  | URL                        |
|----------|----------------------------|
| Frontend | http://localhost:3000      |
| Backend  | http://localhost:8000      |
| Database | localhost:5432             |

### Step 4 — Verify everything is up

```bash
# Backend health check
curl http://localhost:8000/health
# → {"status":"ok"}

# Frontend serves the app
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
# → 200

# Create a scenario via the API
curl -s -X POST http://localhost:8000/scenarios \
  -H "Content-Type: application/json" \
  -d '{"type":"password_reset","tone":"Formal","urgency_level":3}'

# Containers status
docker-compose ps
```

Open **http://localhost:3000** — the Home page should show a green *"Status: ok"*.

### Step 5 — One-time database setup

The database volume starts empty on a fresh machine. Run migrations and seed data **once**:

```bash
# Create all tables (runs Alembic migrations)
docker-compose exec backend alembic upgrade head

# Insert 3 sample scenarios (idempotent — skips if data exists)
docker-compose exec backend python -m app.seed
```

Verify:

```bash
docker-compose exec db psql -U phishing_user -d phishing_db -c "\dt"
# → scenarios, generated_emails, human_emails, tactic_labels,
#   eval_scores, detection_results, alembic_version
```

### Step 6 — Import the human baseline (sample data)

The UI has an upload form, or use the API:

```bash
curl -s -F "file=@ml/sample_data/human_emails_sample.csv" http://localhost:8000/human-emails/upload
# → {"inserted": 5, "skipped": []}
```

*(Or click "Human Baseline" → choose `ml/sample_data/human_emails_sample.csv` → Upload.)*

### Step 7 — Train the detection classifier

The classifier needs labeled emails first (step 6 provides them). Train inside the backend container:

```bash
docker-compose exec backend python -c "
from classifier import train
from app.database import SessionLocal
from app.models import HumanEmail

db = SessionLocal()
emails = [{'subject': e.subject, 'body': e.body, 'label': e.label.value} for e in db.query(HumanEmail).all()]
db.close()
print(train(emails))
"
```

> The model is saved to `ml/models/classifier.pkl` on your machine. Detection endpoints return an error until it's trained. If your local dataset is too small (< 20 rows), the trainer automatically augments with a public phishing corpus placed at `ml/sample_data/nazario_phishing.csv` (CSV with `text`/`body` + `label` columns) — the log tells you which source was used.

### Step 8 — Run the full pipeline (label → evaluate → detect)

```bash
# Rule-based tactic labeling on every unlabeled email
curl -s -X POST http://localhost:8000/label-all

# Evaluation scores (readability, sentiment, persuasion, similarity)
curl -s -X POST http://localhost:8000/evaluate-all

# Classifier predictions on every email
curl -s -X POST http://localhost:8000/detect-all
```

> **Note:** the first `evaluate-all` downloads the sentence-transformers model (`all-MiniLM-L6-v2`) into `ml/hf-cache/` — one-time, ~90 MB.

---

## Using the app

| Page | URL                     | What it does |
|------|-------------------------|--------------|
| Home | `/`                     | Backend health status |
| Scenarios | `/scenarios`        | Create scenarios (type/tone/urgency), generate an LLM email per row, view results inline |
| Human Baseline | `/human-baseline` | Upload CSV, add a single email manually, browse the paginated table |
| Dashboard | `/dashboard`       | 3 charts (avg scores, tactic frequency, detection rate), sortable/filterable table, **Export CSV** and **Export PDF** buttons |

---

## LLM email generation

`POST /scenarios/{id}/generate` calls an OpenAI-compatible chat API to produce the subject + body for a scenario.

- **Provider:** [Groq](https://console.groq.com/keys) free tier by default (no credit card).
- **To enable:** set `LLM_API_KEY` in `.env`, then recreate the backend container:
  ```bash
  # edit .env → LLM_API_KEY=gsk_...
  docker-compose up -d backend
  ```
- **Without a key:** the generator falls back to a deterministic template email so the pipeline is always testable. `model_used` will read `template-fallback`.
- **Audit log:** every generation writes the full prompt, raw model response, scenario ID, timestamp, and model name to `backend/logs/llm_generator.log`.

Config (all optional, in `.env`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `LLM_API_KEY` | *(empty)* | Groq API key; empty = template fallback |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | Model name |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | Any OpenAI-compatible endpoint |

---

## API reference

Base URL: `http://localhost:8000`

### Scenarios & generation
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/scenarios` | Create scenario — body: `{"type": "password_reset\|invoice\|it_alert", "tone": "...", "urgency_level": 1–5}` |
| GET | `/scenarios` | List scenarios, most recent first |
| POST | `/scenarios/{id}/generate` | Generate + save an LLM email for a scenario |

### Human emails
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/human-emails/upload` | CSV upload (`subject, body, source, label`) → `{"inserted": n, "skipped": [...]}` |
| POST | `/human-emails/manual` | Insert one email — body: `{"subject","body","source","label"}` |
| GET | `/human-emails?limit=20&offset=0` | Paginated list |

### Labeling / evaluation / detection
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/emails/{source}/{id}/label` | Rule-based tactic labels for one email (`source`: `generated`\|`human`) |
| POST | `/label-all` | Label every unlabeled email |
| POST | `/emails/{source}/{id}/evaluate` | All 4 evaluation scores for one email |
| POST | `/evaluate-all` | Evaluate every email without scores |
| POST | `/emails/{source}/{id}/detect` | Classifier verdict + confidence for one email |
| POST | `/detect-all` | Detect every email without results |
| GET | `/detection-report` | Detection rate (%) per source (generated vs human) |

### Dashboard & exports
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard/summary` | Aggregated JSON for the charts |
| GET | `/export/csv` | Full dataset as CSV (download) |
| GET | `/export/pdf` | Summary report as PDF (download) |

Interactive docs: **http://localhost:8000/docs** (Swagger UI).

---

## Useful commands

```bash
# Start / stop / restart
docker-compose up -d          # start (background)
docker-compose up --build -d  # rebuild + start (after changing code/deps)
docker-compose down           # stop (keeps database volume)
docker-compose down -v        # stop AND delete database data

# Logs
docker-compose logs -f backend

# Database shell
docker-compose exec db psql -U phishing_user -d phishing_db

# New schema change? (after editing backend/app/models.py)
docker-compose exec backend alembic revision --autogenerate -m "describe change"
docker-compose exec backend alembic upgrade head
```

---

## Running without Docker (development only)

The Docker path above is the supported setup. For frontend-only work, the backend must already be running (Docker or native):

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev   # http://localhost:3000
```

Running the backend natively requires Python 3.11, a local PostgreSQL, and installing `backend/requirements.txt` into a virtualenv — only do this if you can't use Docker.

---

## Project structure

```
├── docker-compose.yml
├── .env.example               # copy to .env
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/               # migration config + versions/
│   ├── logs/                  # LLM audit log (gitignored)
│   └── app/
│       ├── main.py            # FastAPI app (all routers)
│       ├── database.py        # engine / session / Base
│       ├── models.py          # 6 SQLAlchemy models + enums
│       ├── schemas.py         # Pydantic request/response models
│       ├── seed.py            # 3 sample scenarios
│       ├── routers/           # scenarios, emails, dashboard
│       └── services/llm_generator.py
├── frontend/
│   ├── Dockerfile
│   └── src/app/               # page.tsx, scenarios/, human-baseline/, dashboard/
└── ml/
    ├── tactic_labeler.py      # rule-based tactic detection
    ├── evaluator.py           # textstat + VADER + sentence-transformers
    ├── classifier.py          # TF-IDF + Logistic Regression training/prediction
    ├── models/                # trained classifier.pkl (gitignored)
    ├── hf-cache/              # sentence-transformers cache (gitignored)
    └── sample_data/
        └── human_emails_sample.csv
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `docker-compose` fails: *env file .env not found* | `cp .env.example .env` |
| Detection endpoint errors: *classifier not trained yet* | Run the training command from [Step 7](#step-7--train-the-detection-classifier) |
| `generated_emails.model_used` = `template-fallback` | No `LLM_API_KEY` set — expected; add one in `.env` and `docker-compose up -d backend` |
| Frontend shows API errors | Confirm backend is up: `curl http://localhost:8000/health`; `NEXT_PUBLIC_API_URL` is baked into the image at build time, so after changing it run `docker-compose up --build frontend` |
| First `evaluate-all` is slow | One-time model download into `ml/hf-cache/` |
| Container won't start on Windows | WSL issue — run `wsl --status`; may require restarting `WSLService` as admin or rebooting |
| Tables missing after fresh clone | Run `docker-compose exec backend alembic upgrade head` (Step 5) |
