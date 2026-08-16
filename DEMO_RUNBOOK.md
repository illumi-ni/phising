# 🎬 Demonstration Runbook — Phishing Simulation & Benchmarking Web App

Step-by-step script for running the system end to end (and for recording a demo video).
Every command below was executed against this stack and the **expected outputs are the real ones**.

> ⚠️ **Before you record:** do a full dry run once without recording so the video is smooth.
> The first `docker compose up --build` is slow (the backend installs ML packages incl. PyTorch) — do it *before* recording.

> **Compose syntax:** this runbook uses Compose v2 (`docker compose`). The older
> `docker-compose` binary works too if that is what you have installed.

> 🧹 **Recording a take?** Run [CLEANUP.md](CLEANUP.md) first — it resets the
> database to a pristine state and pre-warms the embedding model so
> `evaluate-all` returns in 0.1s on camera instead of 11s.

---

## PART 0 — Prerequisites (do these before pressing record)

1. Docker Desktop is running (green whale icon).
2. A `.env` file exists in the project root — `cp .env.example .env` if not.
3. (Optional but impressive) Put a real Groq API key in `.env`: `LLM_API_KEY=gsk_...`
   - Without it, email generation still works but uses the built-in **template fallback** (`model_used = "template-fallback"`).
   - Get a free key (no credit card) at https://console.groq.com/keys
   - After adding a key: `docker compose up -d --build backend`

---

## PART 1 — Start the whole stack (0:00 – 1:30)

Open a terminal in the project root and run:

```bash
docker compose up --build -d
```

**Show on camera:** the build log scrolling, then the containers starting.

Verify everything is up:

```bash
docker compose ps
```

You should see 3 containers — `phising-db-1` (healthy), `phising-backend-1`, `phising-frontend-1`:

```
NAME                 STATUS                    PORTS
phising-backend-1    Up 17 seconds             0.0.0.0:8000->8000/tcp
phising-db-1         Up 23 seconds (healthy)   0.0.0.0:5432->5432/tcp
phising-frontend-1   Up 17 seconds             0.0.0.0:3000->3000/tcp
```

Then verify the health endpoint:

```bash
curl http://localhost:8000/health
```

**Expected:** `{"status":"ok"}`

**Say:** *"The stack is three containers — a Next.js frontend, a FastAPI backend, and PostgreSQL."*

**URLs to keep handy:**
| What | URL |
|------|-----|
| Homepage | http://localhost:3000 |
| Scenario Builder | http://localhost:3000/scenarios |
| Human Baseline | http://localhost:3000/human-baseline |
| Dashboard | http://localhost:3000/dashboard |
| Backend API (Swagger UI — great for the batch buttons) | http://localhost:8000/docs |

---

## PART 2 — Database setup (one-time, 0:30)

First boot starts with an **empty database**. Create the tables and seed 3 sample scenarios:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
```

**Expected:** `INFO [alembic.runtime.migration] Running upgrade -> b815f1b34939, initial`
followed by `✅ Seeded 3 scenarios.`

Verify the tables exist:

```bash
docker compose exec db psql -U phishing_user -d phishing_db -c "\dt"
```

**Expected:** 7 tables — `scenarios`, `generated_emails`, `human_emails`, `tactic_labels`, `eval_scores`, `detection_results`, `alembic_version`.

Verify the seed data:

```bash
docker compose exec db psql -U phishing_user -d phishing_db -c "SELECT id, type, tone, urgency_level FROM scenarios ORDER BY id;"
```

**Expected:** 3 rows — `PASSWORD_RESET` / `INVOICE` / `IT_ALERT`.

> 💡 **Enum casing:** Postgres stores enum values as the Python enum *names*
> (`PASSWORD_RESET`), while the API returns the lowercase values
> (`password_reset`). Both are correct — don't be surprised on camera.

**Say:** *"Alembic migrations create the six schema tables, and a seed script inserts three starting scenarios."*

---

## PART 3 — Demo 1: Scenario Builder (~1:30)

Open **http://localhost:3000/scenarios**.

1. Fill the form:
   - **Scenario Type:** dropdown → "Password Reset"
   - **Tone:** dropdown → "Alarming"
   - **Urgency Level:** slider → 5
2. Click **Create Scenario** → green success message appears, the new row shows at the top of the table.
3. Create 1–2 more scenarios (e.g. Invoice / Formal, urgency 3) so the table has variety.

**Show on camera:** the form, the submit, the success message, the new rows.

Optionally confirm in Postgres:

```bash
docker compose exec db psql -U phishing_user -d phishing_db -c "SELECT id, type, tone, urgency_level FROM scenarios ORDER BY id;"
```

**Say:** *"The Scenario Builder lets me define phishing scenarios with a type, tone, and urgency level — validated on the backend and persisted to the scenarios table."*

---

## PART 4 — Demo 2: LLM Email Generation (~1:30)

Back on **http://localhost:3000/scenarios**, each scenario row has a **Generate Email** button.

1. Click **Generate Email** on the first scenario → an expandable row opens showing the generated **subject + body**.
2. Do the same for the second and third scenarios (one per type — password_reset, invoice, it_alert).
3. Expand each to read the generated email — the tone and urgency from the scenario are reflected in the copy.

**Show on camera:** each click, the expand, the generated subject/body text.

Verify all three saved to the database:

```bash
docker compose exec db psql -U phishing_user -d phishing_db -c "SELECT id, scenario_id, model_used, left(subject, 60) AS subject FROM generated_emails;"
```

**Expected (no API key):** `model_used = template-fallback` on every row.

**Say:** *"Each scenario generates a realistic phishing-style email. It's a synthetic, lab-only template — a prompt built per scenario type injects the tone and urgency, and every prompt and response is logged. With an LLM API key set, this uses Groq's free tier; otherwise it falls back to a deterministic template so the pipeline always works."*

> 💡 The full prompt sent to the model is stored in `generated_emails.prompt_used` — show that column in psql to prove logging:
> ```bash
> docker compose exec db psql -U phishing_user -d phishing_db -c "SELECT model_used, prompt_used FROM generated_emails WHERE id = 1;"
> ```
> The same prompt/response pair is also appended to `backend/logs/llm_generator.log`.

---

## PART 5 — Demo 3: Human Baseline Import (~1:30)

Open **http://localhost:3000/human-baseline**.

1. **Upload the sample CSV:** click the file input → choose `ml/sample_data/human_emails_sample.csv` → **Upload CSV**.
   - **Expected:** `✅ Uploaded: 5 inserted, 0 skipped.`
2. **Manual entry:** add one email by hand (subject, body, source, label dropdown e.g. "legitimate").
3. The table below lists human emails — 20 per page with pagination controls.

**Show on camera:** the file picker, the upload result, the manual form, the table.

Verify in Postgres:

```bash
docker compose exec db psql -U phishing_user -d phishing_db -c "SELECT id, source, label, left(subject, 60) AS subject FROM human_emails ORDER BY id;"
```

> ⚠️ **Demo tip:** the sample CSV is only 5 rows. Add at least one **legitimate**
> email manually — the classifier in Part 8 needs both labels present to train.

**Say:** *"The Human Baseline module imports real-world emails — labeled phishing or legitimate — either by CSV upload with validation, or one at a time. These become the reference data the system benchmarks LLM emails against."*

---

## PART 6 — Demo 4: Tactic Labeling (~1:00)

Two ways to demo this:

**Option A — single email (UI):** on `/human-baseline` or `/scenarios`, click **Label Tactics** on an email row → tactic badges appear (urgency, authority, scarcity, fear, curiosity) with confidence percentages.

**Option B — all emails (Swagger UI):**
1. Open **http://localhost:8000/docs**
2. Find **POST /label-all** → click **Try it out** → **Execute**
3. Show the response — e.g. `{"generated":3,"human":6,"tactics_created":12}`

Verify in Postgres:

```bash
docker compose exec db psql -U phishing_user -d phishing_db -c "SELECT email_source, tactic_type, count(*), round(avg(confidence)::numeric, 2) AS avg_confidence FROM tactic_labels GROUP BY 1, 2 ORDER BY 1, 2;"
```

**Say:** *"A rule-based labeler detects persuasion tactics — urgency, authority, scarcity, fear, curiosity — using keyword patterns, with confidence as the match ratio. It runs per-email from the UI or across everything with one batch call."*

---

## PART 7 — Demo 5: Evaluation Engine (~1:00)

Run evaluation on every email that doesn't have scores yet (from Swagger UI):

1. In **http://localhost:8000/docs**, find **POST /evaluate-all** → **Try it out** → **Execute**.
2. Show the response counts — e.g. `{"generated":3,"human":6,"scores_created":9}`.

Verify in Postgres:

```bash
docker compose exec db psql -U phishing_user -d phishing_db -c "SELECT email_source, round(avg(readability_score)::numeric, 2) AS readability, round(avg(sentiment_score)::numeric, 2) AS sentiment, round(avg(persuasion_score)::numeric, 2) AS persuasion, round(avg(similarity_score)::numeric, 2) AS similarity FROM eval_scores GROUP BY email_source;"
```

**Say:** *"The evaluation engine scores every email four ways: readability via Flesch Reading Ease, sentiment via VADER, a persuasion-trigger heuristic, and similarity to known phishing emails via sentence-transformer embeddings. The first run downloads the embedding model — later runs are fast."*

> ⏱️ **Timing:** the first `evaluate-all` takes ~35s (one-time download of
> `all-MiniLM-L6-v2` into `ml/hf-cache/`). Pre-warm it before recording; on
> camera, run it again on a freshly added email so it returns instantly.

> 🔍 **Note on similarity:** an email is never compared against itself. Human
> phishing emails *are* the reference corpus, so without that exclusion every
> one of them would score a perfect 1.0 and the human-vs-generated comparison
> would be meaningless.

---

## PART 8 — Demo 6: Detection Classifier (~1:30)

**Step 1 — Train the classifier** (needs the labeled human emails from Part 5):

```bash
docker compose exec backend python -c "
from classifier import train
from app.database import SessionLocal
from app.models import HumanEmail

db = SessionLocal()
emails = [{'subject': e.subject, 'body': e.body, 'label': e.label.value} for e in db.query(HumanEmail).all()]
db.close()
print(train(emails))
"
```

**Show on camera:** the printed metrics — **Accuracy / Precision / Recall / F1** — and `Model saved to: /ml/models/classifier.pkl`.

> ⚠️ **Be honest on camera:** with only ~6 labeled emails the metrics come out
> at 1.0. That is a dataset artifact, not real accuracy. To show meaningful
> numbers, drop a larger public phishing corpus at
> `ml/sample_data/nazario_phishing.csv` — the trainer auto-augments with it
> whenever the local set has fewer than 20 rows and says so in its output.

You can also train on the built-in samples without touching the DB:

```bash
docker compose exec backend python -m classifier --demo
```

**Step 2 — Run detection on everything** (Swagger UI):
1. In **http://localhost:8000/docs**, find **POST /detect-all** → **Try it out** → **Execute**.
2. Show the counts — e.g. `{"generated":3,"human":6,"results_created":9}`.

**Step 3 — The money shot — detection report:**

```bash
curl http://localhost:8000/detection-report
```

**Expected:** detection rate % for `generated` vs `human` email sources, e.g.

```json
{"report":[{"email_source":"generated","total":3,"detected":3,"detection_rate":100.0},
           {"email_source":"human","total":6,"detected":3,"detection_rate":50.0}]}
```

**Say:** *"A TF-IDF + Logistic Regression classifier is trained on the labeled human emails, then run against both human and LLM-generated emails. The detection report shows the headline comparison: what fraction of LLM-generated emails are flagged as phishing vs. real human ones — the core benchmark of this system."*

---

## PART 9 — Demo 7: Analytics Dashboard & Exports (~1:30)

Open **http://localhost:3000/dashboard** — the finale:

1. **Chart 1:** average evaluation scores — generated vs human. All four metrics
   share a 0–1 axis; readability (Flesch 0–100) is plotted as `÷100`, and the
   tooltip shows the true un-scaled value.
2. **Chart 2:** tactic frequency bar chart (urgency / authority / scarcity / fear / curiosity) — generated vs human.
3. **Chart 3:** detection rate comparison (LLM vs human).
4. **Table:** all emails with their scores — click a column header to **sort**, use the **Source** filter (generated/human) and **Scenario** filter.
5. **Export CSV:** click **Export CSV** → a CSV of all data downloads.
6. **Export PDF:** click **Export PDF** → a summary report PDF downloads.

**Show on camera:** each chart, a sort, a filter, and both downloads opening.

**Say:** *"The dashboard ties everything together — score comparisons, tactic frequencies, and the detection-rate benchmark, with sortable tables and CSV/PDF export for reporting."*

---

## PART 10 — Optional bonus shots

- **Swagger UI tour:** http://localhost:8000/docs — collapse all endpoints to show the full API surface.
- **DB tour in psql:** run `\dt` and a `SELECT *` on 2–3 tables to show data end-to-end.
- **Batch flow in one line** (rerun after adding new emails):

```bash
curl -X POST http://localhost:8000/label-all
curl -X POST http://localhost:8000/evaluate-all
curl -X POST http://localhost:8000/detect-all
curl http://localhost:8000/detection-report
```

> The batch endpoints only process emails that have no results yet, so they are
> safe to re-run. The per-email endpoints (`/emails/{source}/{id}/label`,
> `/evaluate`, `/detect`) **replace** any existing row for that email, so
> clicking a button twice never creates duplicates.

To force a full re-scoring from scratch:

```bash
docker compose exec db psql -U phishing_user -d phishing_db -c "DELETE FROM eval_scores; DELETE FROM detection_results;"
curl -X POST http://localhost:8000/evaluate-all
curl -X POST http://localhost:8000/detect-all
```

---

## PART 11 — Stopping / resetting (after recording)

```bash
docker compose down          # stop everything (data kept)
docker compose down -v       # stop AND wipe the database (fresh start next time)
```

To start fresh for a second take:

```bash
docker compose up -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
```

---

## ⚡ TL;DR — full run from zero

```bash
cp .env.example .env                                   # once
docker compose up --build -d                           # ~5-10 min first time
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
curl http://localhost:8000/health                      # {"status":"ok"}

# Then in the UI: create scenarios + generate emails (/scenarios),
# upload ml/sample_data/human_emails_sample.csv and add one legitimate
# email by hand (/human-baseline). Then:

curl -X POST http://localhost:8000/label-all
curl -X POST http://localhost:8000/evaluate-all        # ~35s first run
docker compose exec backend python -c "
from classifier import train
from app.database import SessionLocal
from app.models import HumanEmail
db = SessionLocal()
emails = [{'subject': e.subject, 'body': e.body, 'label': e.label.value} for e in db.query(HumanEmail).all()]
db.close()
print(train(emails))
"
curl -X POST http://localhost:8000/detect-all
curl http://localhost:8000/detection-report            # open /dashboard to see it all
```

---

## 🎬 Suggested video outline (timings)

| # | Segment | Time |
|---|---------|------|
| 1 | Stack startup + health check | 1:30 |
| 2 | DB migration + seed | 0:30 |
| 3 | Scenario Builder | 1:30 |
| 4 | LLM Email Generation | 1:30 |
| 5 | Human Baseline import | 1:30 |
| 6 | Tactic Labeling | 1:00 |
| 7 | Evaluation Engine | 1:00 |
| 8 | Classifier train + detection report | 1:30 |
| 9 | Dashboard + exports | 1:30 |
| 10 | (Bonus) Swagger tour | 0:30 |
| | **Total** | **~12 min** |

## ❗ Common snags during the demo

| Problem | Fix |
|---------|-----|
| `docker compose up` fails: *env file .env not found* | `cp .env.example .env` and retry |
| `docker compose` not recognised | Older Docker — use `docker-compose` (hyphen) for every command here |
| Detection endpoint: *classifier not trained yet* | Run the training command from Part 8 |
| Training fails: *must contain both phishing and legitimate labels* | The human_emails table has only one label — add a legitimate email on `/human-baseline` |
| Generated emails say `template-fallback` | No `LLM_API_KEY` — expected. Optional: add one to `.env`, then `docker compose up -d --build backend` |
| Frontend shows API errors | Check backend: `curl http://localhost:8000/health`. `NEXT_PUBLIC_API_URL` is baked in at build time — after changing it: `docker compose up -d --build frontend` |
| First `evaluate-all` is slow (~35s) | One-time embedding-model download into `ml/hf-cache/` — pre-warm before recording |
| DB port 5432 already in use | Another Postgres on the host is occupying it — stop it or change the port mapping in `docker-compose.yml` |
| Backend edits don't take effect | `backend/` and `ml/` are volume-mounted; uvicorn only watches `/app`, so after editing `ml/*.py` run `docker compose restart backend` |
