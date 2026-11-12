# Architecture — Agent Desk and quantitative research

Stage 4 introduces a separate exploratory historical workflow. The
[Stage 4 contract](STAGE4-CONTRACTS.md) records interfaces and ownership.

- The desk queues a date, snapshot and strategy in SQLite. Its worker loads
  the verified historical snapshot and, for PPO/DDPG, the verified policy.
  The quantitative decision only uses the required window through the
  decision close. It estimates a first target from cash.
- The OpenRouter adapter pins a free model and endpoint and validates strict
  structured output. The Nemotron Lightning transport uses the arguments of
  one named response function as data. The backend never executes that
  function. Market Analyst sees numeric aggregates. Portfolio Judge
  receives those aggregates, the analyst's closed labels and the proposed
  weights. The application provides no tools or news retrieval. It stores
  validated labels, timing, route and token telemetry when available.
- The Chief coordinates the workflow. The deterministic engine applies
  independent temporal, provenance, data, simplex, position, volatility,
  turnover and fee gates. A positive Judge verdict requires a risk pass to
  become a research approval. There is no order endpoint.
- `desk_runs` and `desk_events` are separate from Stage 3's training and
  backtest tables. The event table is append-only through the application.
  The terminal event and outcome commit together. The dashboard reads the
  persisted events, explanations and source identifiers through its proxy.

## Stage 3 quantitative research

Stage 3 adds CPU training without replacing the historical engine or Gym
environment. The [research contract](STAGE3-CONTRACTS.md) defines boundaries.

- `portfolio_rl` wraps SB3 PPO and DDPG. It fits an observation transform on
  each training partition, freezes it, and saves it with the policy and manifest.
  DDPG also saves its replay buffer. Inference checks the local artifact hashes.
- The API persists training requests in SQLite and returns HTTP 202. A separate
  supervisor claims one job at a time and starts a child process. It tracks
  progress, wall time, CPU time and sampled RSS, and handles cancellation,
  launch failure and interrupted-job recovery. The backtest worker remains
  separate. One API instance owns each database.
- `portfolio_evaluation` replays frozen policies deterministically with the same
  timing, capital, fees and exact accounting as the historical baselines.
  It separates pre-2022 candidate selection from the 2022–2023 validation.
  Model training and replay reject dates that would expose the 2024 holdout.
- The dashboard reads jobs, checkpoints and validation results via the existing
  proxy. Saved-model backtests use an artifact ID and require matching dataset,
  algorithm, lookback, starting capital, cost and risk-free rate.

## Stage 2 implementation (historical reference)

Current implementation (2026-11-10) extends the baseline below. The active
research interfaces and ownership are in [STAGE2-CONTRACTS.md](STAGE2-CONTRACTS.md).

- market_data downloads the ten public histories into immutable verified
  Parquet/raw/quality/manifest snapshots. No network operation runs inside HTTP.
- portfolio_core owns typed PricePanel and exact post-fee self-financing
  accounting. portfolio_research and portfolio_env use this same engine.
- Markowitz and historical equal-weight use signals through t-1, execute
  stylized adjusted close t and value t→t+1. Default W60/risk aversion5 are
  research assumptions, not tuned against the reserved2024 holdout.
- API lists verified local datasets and dispatches persisted jobs to either
  unchanged fixture-v1 or historical replay. Dataset.kind is FIXTURE|HISTORICAL;
  strategy equal_weight|markowitz. Historical request adds split=train|validation,
  lookback2..252, risk_aversion>0. Final-test2024 is422.
- MARKET_DATA_ROOT defaults to repo/.runtime/datasets. Invalid snapshots fail
  closed with503; missing snapshot404. Neither is replaced by a fixture.
- Shutdown joins the current bounded job before recovery may occur, preventing
  stale worker writes from overwriting restart status.
- UI selects datasets/strategies and labels source per result/history row.
- Fixture exposure is disabled by default. Only automated harnesses opt into
  ENABLE_TEST_FIXTURES; normal research data/jobs/history are historical-only.

The fixture remains version0.1 with original approximate fees and tests;
historical engine0.2 uses exact-self-financing-v1. Do not compare synthetic
and historical performance or silently change the fixture accounting.
CPU PyTorch/SB3 are installed only for compatibility checks; no model is trained.
Future expensive training still requires a separate worker process.

## Preserved Stage 1 specification (historical reference)

## Decisions

Use a local monorepo: Next.js App Router/strict TypeScript/Tailwind/shadcn UI,
FastAPI/Pydantic v2, an independent Python quant package, SQLite and a single
bounded background worker. PostgreSQL, Redis, PyTorch and provider adapters
are deferred until required. Docker CLI exists but its daemon is unavailable.

Browser requests `/api/backend/...`; a Next.js server proxy forwards only
allowlisted paths to `API_BASE_URL` (loopback by default). No client API key,
arbitrary upstream URL or live execution endpoint. Local services bind loopback.
API lifespan owns one worker; HTTP handlers enqueue persisted jobs and return
202. Worker executes quant outside the event loop. At restart, interrupted jobs
must become failed explicitly (no silent completion). Queue has a finite cap.
SQLite uses short transactions, DELETE journaling and busy timeout; one API
process only. A multi-process durable scheduler is a later-stage change.

## Frozen v1 contracts

JSON uses snake_case; UTC ISO timestamps; dates use YYYY-MM-DD; fractions for
returns/volatility/drawdown; money in simulated USD. OpenAPI is exported and
TypeScript declarations generated from it before integration acceptance.

`GET /health` → `{status:"ok",service:"portfolio-ai-lab-api",mode:"PAPER"}`.
`GET /ready` verifies persistence, returns `{status:"ready",mode:"PAPER"}`.
`GET /api/v1/datasets` → `{items: Dataset[]}`.
`GET /api/v1/experiments` → `{items: Experiment[]}` (newest first, bounded).
`POST /api/v1/experiments` accepts Config; returns Experiment, HTTP 202.
`GET /api/v1/experiments/{id}` → Experiment or 404.

Config: `name` (1–80 chars), `strategy:"equal_weight"`, `dataset_id:"fixture-v1"`,
`initial_capital` (>0, ≤1e9), `transaction_cost_bps` (0–100),
`risk_free_rate` (annual effective, -0.99–1), `seed` (0–2147483647).
Reject extra fields and non-finite numbers. Defaults: 10000, 10bps, 0, 42.

Dataset: `id`, `kind:"FIXTURE"`, `source`, `sha256`, `assets:string[]`,
`start_date`, `end_date`, `observations`. Fixture assets are fictional symbols,
not actual ticker histories. No provider or 2024 holdout data in Stage 1.

Experiment: `id`, `name`, `status:"queued"|"running"|"completed"|"failed"`,
`created_at`, `completed_at:string|null`, `config`, `dataset`,
`result:Result|null`, `error:string|null`.

Result: `metrics`, `equity`, `allocations`, `audit`, `manifest`.
Metrics: `cumulative_return`, `annualized_volatility:number|null`,
`sharpe_ratio:number|null`, `max_drawdown`, `final_equity`, `total_costs`.
Equity points: `{date,equity,net_return}` including initial pre-fee capital.
Allocation: `{date,weights:Record<string,number>,turnover,cost}`.
Audit: `{date,event,detail}`; manifest JSON includes engine version, fixture
hash, configuration, timing convention and metric definitions.

## Quant timing and accounting

`portfolio_quant.run_backtest(config:dict) -> dict` returns Result;
`portfolio_quant.fixture_metadata() -> dict` returns Dataset. Only read the
versioned local fixture resource; no network or external storage writes.
Quant package owns its fixture and tests. Equal-weight target is exogenous,
fixed before any price is observed. At close t rebalance to equal weights,
deduct one-way L1 turnover cost from pre-trade equity, then apply t→t+1 price
relatives. First turnover is 1 from cash. Later turnover compares target with
drifted weights. Approximate fee model is explicit, not a claim of exact
share-level self-financing execution; no terminal liquidation fee. Daily
returns include entry fee in first interval, and equity includes initial cash.
Use sample std ddof=1, annualization 252, daily rf=(1+annual_rf)^(1/252)-1;
undefined volatility/Sharpe are null. Drawdown is nonnegative magnitude.
Signals from close t cannot assume same-close execution in future strategies;
Stage 2 must freeze an execution lag or next-open price protocol first.

## Deferred boundaries

RF1–RF7, Markowitz/PPO/DDPG, full risk engine, source snapshots, walk-forward,
Agent Desk and real academic validation are not delivered by a synthetic demo.
Deterministic input/weight integrity checks are required now. No TRL5 claim.
