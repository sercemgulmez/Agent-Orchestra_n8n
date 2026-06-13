# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

**YemekTest Orchestrator** — an AI-powered test generation platform for Yemeksepeti web and mobile app scenarios. It models `yemeksepeti.com` and app user journeys in a safe mock/staging mirror instead of running side-effectful login, order, or payment tests against live production.

The stack has six services:
- **Orchestrator** (`main.py` + `agents/`): FastAPI app on port 8000 that drives the AI pipeline
- **Mock API** (`mock_api/server.py`): FastAPI app on port 8001 simulating Yemeksepeti mirror surfaces: Restoran, Gel Al, Marketler, location, coupon, checkout, tracking
- **Mock UI** (`mock_ui/`): React/Vite/TypeScript mirror frontend on port 3000
- **Mobile profiles** (`mobile_appium/`): Android/iOS Appium capability templates for black-box app testing
- **n8n** (Docker): Workflow automation on port 5678, persisted in `n8n_workflows/`
- **Obsidian Maps Plugin** (`obsidian_maps_plugin/`): TypeScript Obsidian plugin with map view and commands; uses the orchestrator's token profile APIs

Infrastructure: PostgreSQL (5432) and Redis (6379) are Docker-only dependencies.

## Running Services

Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY` before starting.

**Full stack (Docker):**
```bash
docker-compose up
```

Docker also requires `POSTGRES_PASSWORD`, `N8N_ENCRYPTION_KEY`, `N8N_BASIC_AUTH_USER`, and `N8N_BASIC_AUTH_PASSWORD` in `.env`.

**Individual services (local dev):**
```bash
# Orchestrator
pip install -r requirements.txt
python main.py                          # port 8000

# Mock API
uvicorn mock_api.server:app --port 8001

# Mock UI
cd mock_ui && npm install && npm run dev   # port 3000
cd mock_ui && npm run build               # tsc + vite build (no separate lint script)
```

**Dashboard:** http://localhost:8000/dashboard (live token/cost stats)  
**API docs:** http://localhost:8000/docs

## Running Tests

Most tests require the Mock API (port 8001) and Mock UI (port 3000) to be running. Override with `MOCK_API_URL` and `MOCK_UI_URL` env vars.

```bash
pytest tests/                           # all tests
pytest tests/test_foo.py::test_bar      # single test
pytest -v                               # verbose
```

Playwright tests require browsers installed:
```bash
playwright install chromium
```

## Test Profiles

The orchestrator exposes `/api/test-profiles` and supports:

- `mock`: full safe mirror testing for API, web, mobile, and E2E.
- `web-prod-smoke`: read-only live `https://www.yemeksepeti.com/` navigation/smoke checks. No login, cart, payment, scraping, or order submission.
- `mobile-android`: Appium Android profile. App path and test account are env-only.
- `mobile-ios`: Appium iOS profile. App path and test account are env-only.

Valid `test_type` values are `api`, `web`, `mobile`, `e2e`, and `prod-smoke`.

The safety policy is runtime-enforced in `/api/orchestrate`. Non-mock profiles reject cart, checkout, payment, order, coupon, personal data, and login-submit intent before any AI pipeline stage starts. `web-prod-smoke` only accepts `prod-smoke`.

## Agent Architecture (`agents/`)

Three classes form the core pipeline:

### `MultiAgentCoordinator` + `TestOrchestrationPipeline` (`agents/flexible_coordinator.py`)

`TestOrchestrationPipeline.run()` drives the four-stage flow: PLAN → EXECUTE → REVIEW → (optional) FIX. Each stage calls `MultiAgentCoordinator._call_api()`, which:
1. Checks `TokenOptimizer` cache (MD5-keyed, skips the API call on hit)
2. Compresses the prompt via `TokenOptimizer.compress_prompt()`
3. Calibrates `max_tokens` based on stage
4. Calls the Anthropic API (or `codex` CLI subprocess for CODEX models) and records usage

The FIX stage triggers when `"critical"` appears in the review text **and** quality score is below 80.

**Modes** (`CoordinatorMode` enum) accepted by `POST /api/orchestrate` as `mode` (takes precedence over individual `plan_model`/`execute_model` fields):
- `OPUS_SONNET`: plan=opus, execute=sonnet, review=codex
- `OPUS_CODEX`: plan=opus, execute=codex, review=sonnet
- `CODEX_SONNET`: plan=codex, execute=sonnet, review=codex
- `CODEX_CODEX`: plan=codex, execute=codex, review=sonnet

The review model always alternates with the execute model (SONNET↔CODEX).

**Complexity routing**: if `ComplexityAnalyzer` scores a task as EASY (score < 60), the execute stage is automatically downgraded to Haiku regardless of mode.

`FlexibleCoordinator` is a thin wrapper around `TestOrchestrationPipeline` — it is not the primary entry point; `main.py` instantiates `TestOrchestrationPipeline` directly.

### `ComplexityAnalyzer` (`agents/complexity_analyzer.py`)
Keyword-regex scorer. Detects steps, dependencies, auth keywords, E2E phrases, and assertion words in the task description. Score ≥ 60 → HARD (Sonnet/Opus), < 60 → EASY (Haiku).

### `TokenOptimizer` (`agents/token_optimizer.py`)
- **Cache**: MD5-keyed dict; `check_cache` reads, `store_cache` writes. Persisted to `token_optimizer_data.json` across restarts via `loadData`/`saveData`.
- **Compression**: four levels (NONE/LIGHT/MODERATE/AGGRESSIVE). MODERATE strips filler phrases and trims long JSON arrays to 8 items. AGGRESSIVE also minifies JSON blocks and truncates code blocks to 30 lines.
- **Token graph**: `TokenNode`/`TokenEdge` objects accumulate per-stage usage for the dashboard.
- **Pricing table**: `MODEL_PRICING` dict maps model IDs (and short aliases) to per-million input/output rates.

## Mock API (`mock_api/server.py`)

All state is in-memory (resets on restart):
- `USERS` / `ACTIVE_TOKENS`: bearer-token auth via `POST /v2/user/login`
- `RESTAURANTS`: 5 hard-coded restaurants with nested menu categories and items
- `MARKETS`: market listings and product catalogs for the Marketler surface
- `ADDRESS_SUGGESTIONS`: safe district-level address suggestions, no personal addresses
- `CARTS` / `ORDERS`: per-user cart and order lifecycle
- `COUPONS`: test-only coupon validation (`TEST10`, `YSAPP`)

Order status advances each time `GET /v2/orders/{id}/track` is called (RECEIVED → CONFIRMED → PREPARING → ON_THE_WAY → DELIVERED).

Test credentials: `test@test.com / Test123!`, `admin@test.com / Admin123!`

## Mock UI (`mock_ui/`)

React Router v6 SPA with four routes: `/login`, `/` (Restoran/Gel Al/Marketler home), `/restaurant/:id`, `/cart`. Auth token is stored in `localStorage`. All API calls go through `mock_ui/src/api/client.ts`.

The home page includes a mirror safety banner. Product tabs and location entry are testable via `data-testid` selectors.

## n8n Workflows (`n8n_workflows/`)

n8n is the **trigger and reporting layer only** — not the decision-maker. Safety policy, profile validation, and side-effect blocking all run inside FastAPI. n8n workflows only: schedule/manual trigger, call `/api/orchestrate`, fetch token/cost reports, and send notifications.

Four workflow JSON files are mounted into the n8n container:
- `api_only_pipeline.json` — triggers the orchestrator API pipeline only
- `complete_orchestration.json` — full end-to-end orchestration workflow
- `prod_smoke_pipeline.json` — smoke-only pipeline for the `web-prod-smoke` profile
- `token_monitor.json` — polls `/api/token-report` and alerts on budget overrun

CI/nightly workflows run only with `profile=mock`; the live smoke workflow is kept separate and uses only `profile=web-prod-smoke, test_type=prod-smoke`.

**n8n security rules:**
- `executeCommand` and `readWriteFile` nodes are blocked via `NODES_EXCLUDE` in docker-compose.
- Use the n8n credential store for Slack/webhook/token values — never embed secrets in workflow JSON files.
- `N8N_ENCRYPTION_KEY` must remain constant after first setup; changing it makes all stored credentials unreadable.
- n8n binds to `127.0.0.1:5678` locally; add a reverse proxy with TLS before exposing externally.

## Environment Variables

Key variables (see `.env.example` for full list):

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required — all AI calls fail without it |
| `POSTGRES_PASSWORD` | Required for Docker — PostgreSQL password |
| `N8N_ENCRYPTION_KEY` | Required for Docker — n8n credential encryption |
| `N8N_BASIC_AUTH_USER` | Required for Docker — n8n web UI login |
| `N8N_BASIC_AUTH_PASSWORD` | Required for Docker — n8n web UI password |
| `ORCHESTRATOR_PORT` | Orchestrator port (default 8000) |
| `TOKEN_BUDGET_USD` | Max spend per orchestration (default 5.0) |
| `QUALITY_THRESHOLD` | Min score before FIX stage triggers (default 75) |
| `COMPLEXITY_THRESHOLD` | Score cutoff for EASY/HARD routing (default 60) |
| `MOCK_API_URL` | Override mock API base in tests (default `http://localhost:8001`) |
| `MOCK_UI_URL` | Override mock UI base in tests (default `http://localhost:3000`) |
