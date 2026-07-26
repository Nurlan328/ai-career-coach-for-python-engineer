# AI Career Coach for Python Backend Engineers

FastAPI backend that helps engineers prepare for Python backend interviews:
analyzes a resume, detects the experience level, generates topic questions,
runs a text **mock interview** and scores the answers — powered by **Claude**.

> Works **with or without** an API key. Without `ANTHROPIC_API_KEY` it falls back
> to a built-in question bank and heuristic resume analysis, so every endpoint is
> fully runnable offline.

## Stack

| Layer        | Choice                                   |
|--------------|------------------------------------------|
| Web          | FastAPI + Uvicorn                        |
| Validation   | Pydantic v2 / pydantic-settings          |
| ORM          | SQLAlchemy 2.0 (async)                   |
| DB           | SQLite (default) · PostgreSQL (asyncpg)  |
| Migrations   | Alembic                                  |
| Auth         | JWT (PyJWT) + bcrypt                      |
| LLM          | Claude via the `anthropic` SDK           |
| RAG          | Qdrant (in-memory) + fastembed embeddings |
| Jobs / cache | Celery + Redis (graceful in-memory fallback) |
| Parsing      | pypdf · python-docx                      |
| Tests / CI   | pytest + ruff · GitHub Actions           |
| Deploy       | AWS (EKS · ECR · ALB · RDS · ElastiCache) · Docker |

## MVP scope (implemented)

1. Register / login (JWT)
2. Resume upload (PDF / DOCX / TXT) + parsing
3. Resume analysis — skills, detected level, strengths, recommendations
4. Python-backend question generation (14 categories)
5. Text mock interview
6. Answer evaluation (score + strengths/weaknesses/missing topics)
7. Interview history
8. **Vacancy gap-analysis** — analyze a posting, compare to a resume, generate a
   weekly prep roadmap
9. **AI tutor** — free-form Q&A with multi-turn context and token streaming
10. **RAG knowledge base** — tutor answers grounded in a curated corpus with cited
    sources (Qdrant + fastembed; works offline, returns snippets without a key)
11. **Voice interview** — read questions aloud (TTS) and dictate answers (STT) via
    the browser Web Speech API (no backend/keys; Chrome/Edge)
12. **Billing & plans** — real Stripe Checkout + customer portal, subscription
    state driven by idempotent webhooks, monthly interview limits per plan;
    runs in mock mode (instant upgrade) without a Stripe key

_The full ТЗ scope is implemented._

> The first `/coach/rag` call downloads the embedding model
> (`paraphrase-multilingual-MiniLM-L12-v2`, ~hundreds of MB) and builds the index
> in-memory. Verify retrieval offline with `python rag_smoke.py`.

## Quick start

```bash
# 1. install
python -m venv .venv && .venv/Scripts/activate      # Windows
# source .venv/bin/activate                          # macOS/Linux
pip install -r requirements.txt

# 2. (optional) configure
cp .env.example .env        # add ANTHROPIC_API_KEY to enable real Claude output

# 3. run
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/docs** for interactive Swagger UI. Click **Authorize**,
log in with your registered email/password, and try the endpoints.

Verify everything end-to-end (no API key needed):

```bash
python smoke_test.py        # registers a user and exercises the full flow
```

## API

Base prefix: `/api`

| Method | Path                              | Description                          |
|--------|-----------------------------------|--------------------------------------|
| POST   | `/auth/register`                  | Create account                       |
| POST   | `/auth/login`                     | OAuth2 password form → JWT           |
| GET    | `/auth/me`                        | Current user                         |
| POST   | `/resumes/upload`                 | Upload + analyze a resume            |
| GET    | `/resumes`                        | List my resumes                      |
| GET    | `/resumes/{id}/analysis`          | Full analysis of one resume          |
| POST   | `/vacancies/analyze`              | Analyze a job posting → required skills |
| GET    | `/vacancies`                      | List my vacancies                    |
| POST   | `/vacancies/compare-with-resume`  | Gap analysis: resume vs vacancy      |
| POST   | `/vacancies/roadmap`              | Personalized weekly prep roadmap     |
| GET    | `/questions/categories`           | Categories + levels                  |
| POST   | `/questions/generate`             | Generate questions                   |
| POST   | `/interviews/start`               | Start a mock interview               |
| POST   | `/interviews/{id}/answer`         | Submit an answer, get feedback       |
| GET    | `/interviews/{id}/result`         | Full result + per-question feedback  |
| GET    | `/interviews/history`             | My interviews                        |
| POST   | `/coach/ask`                      | Ask Claude any Python/backend question (supports `history`) |
| POST   | `/coach/ask/stream`               | Same, streamed token-by-token (`text/plain`) |
| POST   | `/coach/rag`                      | Answer grounded in the knowledge base, with cited sources |
| GET    | `/billing/plans`                  | Subscription plans + limits          |
| GET    | `/billing/me`                     | Current plan + monthly usage         |
| POST   | `/billing/checkout`               | Stripe Checkout session (or mock upgrade) |
| POST   | `/billing/portal`                 | Stripe customer portal link (cancel / change card) |
| POST   | `/billing/webhook`                | Stripe webhook (subscription lifecycle) |

## Billing (Stripe)

Without `STRIPE_SECRET_KEY` billing runs in **mock mode**: "checkout" upgrades the
user instantly and nothing is charged, so the flow is demoable offline. Set the
three variables below and the same buttons drive real Stripe Checkout.

```bash
# .env — test keys are enough, no real money moves
STRIPE_SECRET_KEY=sk_test_...      # dashboard.stripe.com/test/apikeys
STRIPE_PRICE_PRO=price_...         # a recurring (monthly) price from the catalog
STRIPE_WEBHOOK_SECRET=whsec_...    # printed by `stripe listen`, see below
```

Locally, forward events with the Stripe CLI (the webhook is public, so it is
authenticated *only* by the signature — without a secret we refuse the payload):

```bash
stripe listen --forward-to localhost:8000/api/billing/webhook
```

In production, create the endpoint in the dashboard and subscribe to
`checkout.session.completed`, `customer.subscription.updated`,
`customer.subscription.deleted`, `invoice.payment_failed`.

Test card: `4242 4242 4242 4242`, any future expiry, any CVC.

How it holds together:

* one Stripe **Customer** per user (`users.stripe_customer_id`), created lazily and
  reused — that is what makes the portal, invoices and webhook lookups line up;
* subscription state is mirrored onto `users` by webhooks, so the quota check
  never makes a network call — Stripe stays the source of truth;
* every event id is claimed in `stripe_events` **before** it is applied, so
  Stripe's at-least-once redelivery can't double-apply anything;
* entitlement is `effective_plan()`, not the stored plan: a `past_due`
  subscription silently drops back to Free limits until the payment recovers;
* cancel / change-card go through the Stripe-hosted portal, so card data never
  touches this app.

## Frontend (React)

A Vite + React + TypeScript SPA lives in [`frontend/`](frontend/) and covers the
whole MVP: login/register, resume analysis, question generator, mock interview,
and the **streaming** AI tutor chat.

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173  (proxies to the API via VITE_API_BASE)
```

The backend must be running on `http://127.0.0.1:8000` (or set `VITE_API_BASE`
in `frontend/.env`). See [frontend/README.md](frontend/README.md).

## Deployment (AWS / EKS)

Production deploy to **EKS** (API + Celery worker), with **RDS**, **ElastiCache**,
**ECR**, and an **ALB** ingress. Multi-stage [Dockerfile](Dockerfile) (non-root),
Kubernetes manifests in [`deploy/k8s/`](deploy/k8s/), and a CI deploy workflow
([.github/workflows/deploy.yml](.github/workflows/deploy.yml)) that builds → pushes
to ECR → runs the Alembic migration Job → rolls out. Full runbook:
[deploy/README.md](deploy/README.md).

## PostgreSQL

```bash
pip install asyncpg
# in .env:
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/career_coach
```

Or use Docker (Postgres + API):

```bash
docker compose up --build
```

## Project layout

```
app/
├── main.py            # FastAPI app + lifespan (creates tables)
├── core/              # config, async DB, security (JWT/bcrypt), deps
├── models/            # SQLAlchemy models: user, resume, interview*
├── schemas/           # Pydantic request/response models
├── services/          # ai_service + resume/question/evaluation/interview logic
├── api/               # routers: auth, resumes, questions, interviews
└── utils/             # file_parser (pdf/docx/txt)
```

## Tests & lint

```bash
pip install -r requirements-dev.txt
pytest -q          # 28 tests, fully offline (no API key, no Redis, no Stripe)
ruff check app tests
```

Tests run with `CELERY_TASK_ALWAYS_EAGER=true` (tasks run inline, no broker) and
the cache's in-memory fallback, so the suite needs neither Redis nor an API key.
CI (GitHub Actions) runs ruff + pytest and builds the frontend — see
[.github/workflows/ci.yml](.github/workflows/ci.yml).

## Background jobs (Celery + Redis)

Heavy work (re-running resume analysis) can run off the request via Celery:

```bash
# needs a running Redis (docker compose up redis)
celery -A app.core.celery_app worker --loglevel=info
```

`POST /resumes/{id}/reanalyze` enqueues the job (returns `202` + `task_id`).
Redis also backs a small response cache (`/coach/rag`); if Redis is unreachable
the cache transparently falls back to an in-memory dict.

## Migrations (Alembic)

By default tables are auto-created on startup (`AUTO_CREATE_TABLES=true`) for
zero-setup dev. For production, let Alembic own the schema:

```bash
# in .env: AUTO_CREATE_TABLES=false
alembic upgrade head                              # apply migrations
alembic revision --autogenerate -m "change X"     # after editing models
alembic downgrade -1                              # roll back
```

The DB URL comes from `DATABASE_URL` (injected in `alembic/env.py`). See
[alembic/README.md](alembic/README.md).

## Notes

- `LLM_MODEL` defaults to `claude-sonnet-4-6`; set `claude-opus-4-8` for max
  quality or `claude-haiku-4-5` for speed/cost.
