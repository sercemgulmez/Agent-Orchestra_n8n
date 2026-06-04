# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

**YemekTest Orchestrator** — an AI-powered test generation platform for Yemeksepeti web and mobile app scenarios. It models `yemeksepeti.com` and app user journeys in a safe mock/staging mirror instead of running side-effectful login, order, or payment tests against live production.

The stack has four services:
- **Orchestrator** (`main.py` + `agents/`): FastAPI app on port 8000 that drives the AI pipeline
- **Mock API** (`mock_api/server.py`): FastAPI app on port 8001 simulating Yemeksepeti mirror surfaces: Restoran, Gel Al, Marketler, location, coupon, checkout, tracking
- **Mock UI** (`mock_ui/`): React/Vite/TypeScript mirror frontend on port 3000
- **Mobile profiles** (`mobile_appium/`): Android/iOS Appium capability templates for black-box app testing
- **n8n** (Docker): Workflow automation on port 5678, persisted in `n8n_workflows/`

## Running Services

Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY` before starting.

**Full stack (Docker):**
```bash
docker-compose up
```

**Individual services (local dev):**
```bash
# Orchestrator
pip install -r requirements.txt
python main.py                          # port 8000

# Mock API
uvicorn mock_api.server:app --port 8001

# Mock UI
cd mock_ui && npm install && npm run dev   # port 3000
```

**Dashboard:** http://localhost:8000/dashboard (live token/cost stats)  
**API docs:** http://localhost:8000/docs

## Running Tests

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

### `FlexibleCoordinator` (`agents/flexible_coordinator.py`)
Orchestrates the multi-stage pipeline. Each stage calls `_call_anthropic()`, which:
1. Checks `TokenOptimizer` cache (MD5-keyed, skips the API call on hit)
2. Compresses the prompt via `TokenOptimizer.compress()`
3. Calibrates `max_tokens` based on stage + complexity score
4. Calls the Anthropic API and records usage

**Modes** (`CoordinatorMode` enum) map to `(plan_model, execute_model, review_model)` tuples:
- `OPUS_SONNET`: opus/sonnet/opus — highest quality, medium cost
- `OPUS_CODEX`: opus/sonnet/sonnet
- `CODEX_SONNET`: sonnet/sonnet/opus
- `CODEX_CODEX`: sonnet/sonnet/sonnet — fastest, lowest cost

**Complexity routing**: if `ComplexityAnalyzer` scores a task as EASY (score < 60), the execute stage is automatically downgraded to Haiku regardless of mode. If the resulting quality score falls below 75, it optionally upgrades to Sonnet for a FIX pass.

### `ComplexityAnalyzer` (`agents/complexity_analyzer.py`)
Keyword-regex scorer. Detects steps, dependencies, auth keywords, E2E phrases, and assertion words in the task description. Score ≥ 60 → HARD (Sonnet/Opus), < 60 → EASY (Haiku).

### `TokenOptimizer` (`agents/token_optimizer.py`)
- **Cache**: MD5-keyed dict; `brainstorm_check` reads, `cache_write` writes. Persisted to `token_optimizer_data.json` across restarts via `loadData`/`saveData`.
- **Compression**: four levels (NONE/LIGHT/MODERATE/AGGRESSIVE). MODERATE strips filler phrases and trims long JSON arrays to 8 items. AGGRESSIVE also minifies JSON blocks and truncates code blocks to 30 lines.
- **Token graph**: `TokenNode`/`TokenEdge` objects accumulate per-stage usage for the dashboard.

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

## Environment Variables

Key variables (see `.env.example` for full list):

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required — all AI calls fail without it |
| `ORCHESTRATOR_PORT` | Orchestrator port (default 8000) |
| `TOKEN_BUDGET_USD` | Max spend per orchestration (default 5.0) |
| `QUALITY_THRESHOLD` | Min score before FIX stage triggers (default 75) |
| `COMPLEXITY_THRESHOLD` | Score cutoff for EASY/HARD routing (default 60) |
