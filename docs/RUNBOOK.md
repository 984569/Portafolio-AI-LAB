# Runbook — local research and verification

From the repository root in PowerShell:

```powershell
uv sync --python 3.11 --frozen
./scripts/setup_node.ps1
./scripts/web.ps1 install --frozen-lockfile
uv run python scripts/check_bootstrap.py
```

Run API in one terminal: `uv run python scripts/run_api.py`.
Run frontend in another: `./scripts/web.ps1 dev`.
Open http://127.0.0.1:3000/dashboard . API documentation: http://127.0.0.1:8000/docs .
Select the historical dataset/strategy and click **Ejecutar prueba**. The run
is queued, calculated, persisted and polled. Inspect curve data, allocations
and manifest; refresh the page to verify persistence.

API readiness: `Invoke-RestMethod http://127.0.0.1:8000/ready`.
Historical validation without services: `uv run python scripts/validate_stage2.py`.
Stop each local service with Ctrl+C. Ports 3000/8000 must be free for E2E.

For production-mode verification locally: `./scripts/web.ps1 build`, then
`./scripts/web.ps1 --filter @portfolio/web start` instead of the dev command. This starts
only a loopback process; no service is deployed or published.

## Configuration

Root `.env.example` documents optional process variables; it is not loaded
automatically. API defaults to PAPER and `.runtime/portfolio.sqlite3` resolved
from repository root regardless of shell directory. Next's proxy defaults to
http://127.0.0.1:8000 and accepts only local HTTP API origins. To override in
PowerShell before starting the process:

```powershell
$env:PORTFOLIO_DB_PATH = '.runtime/another-demo.sqlite3'
$env:MARKET_DATA_ROOT = '.runtime/datasets'
$env:API_BASE_URL = 'http://127.0.0.1:8000'
```

## Real historical pipeline and benchmarks

From root, before selecting historical data:

```powershell
uv run python scripts/download_history.py --root .runtime/datasets
uv run python scripts/validate_stage2.py
```

Download requires public internet but no credentials. Responses/raw hashes,
progress, quality and Parquet snapshots stay under .runtime/datasets. A second
run reuses verified originals. A partial failure exits nonzero and does not
register a snapshot or insert synthetic replacements. Corrupt/incomplete cache
is rejected; preserve it for inspection and use a new local root to retry fresh
data rather than deleting evidence. If choosing another root, set MARKET_DATA_ROOT
for the API before startup. Registry paths are resolved from repository root.

In the dashboard choose **Origen de datos → HISTÓRICO**, then Equal weight or
Markowitz and train/validation. Defaults:60-return window, aversion5,10bps,
capital10000USD, seed42. These are declared assumptions, not optimized settings.
Signals stop at t-1; exact fees apply at t; next-close ratios value the portfolio.
The result and history row label HISTORICAL, source and strategy separately from
the FIXTURE mode. Quality/splits/source/hash appear in dataset and run manifests.
2024 is ingested for quality only; final_test is not an available evaluation.

validate_stage2.py executes both real validation benchmarks twice, compares
deterministic hashes, runs Gymnasium/SB3 check_env and a1741-step training-only
equal-weight rollout, comparing environment accounting against the benchmark.
It does not train PPO/DDPG or open final2024 evaluation. Report defaults to
.runtime/stage2-validation.json. Negative benchmark results are retained.
Baseline parameters are read from experiments/stage2-baseline.json; the report
records its SHA256. Use --config to replay another declared local configuration
without editing code. Final2024 remains disallowed by the research engine.

Node setup uses the official24.22.2 Windows ZIP and SHA256 file. web.ps1 changes
PATH only for its child process and restores it on exit. Global Node25 remains
installed. Linux/macOS users can use their supported Node24 and ordinary pnpm
commands; the Windows wrapper is not required in CI.

No credentials or OpenRouter calls are needed. No live-mode switch exists.
Normal runtime has ENABLE_TEST_FIXTURES=false: no synthetic dataset, new job
or fixture result is exposed. The original persisted fixtures are preserved.
Pytest and the baseline Playwright runner enable test mode only in their own
processes; the historical browser suite explicitly disables it. There is no
UI toggle for synthetic research data or fallback to fixtures on provider failure.
One API process owns the database/worker; do not launch multiple API instances
against the same DB. A restart marks interrupted jobs failed explicitly; submit
a new experiment. Completed results remain available. No automatic deletion.
Shutdown waits for the current bounded job so an old writer cannot overwrite
restart recovery. Pending jobs are failed on next startup; no invisible retries.

## Stage 3 model training

Import the verified historical snapshot first. In **AI Research Lab**, choose
PPO or DDPG, set the seed, learning rate, policy width and number of steps,
then click **Entrenar modelo**. The dashboard polls the persisted job. A
completed job can be evaluated on 2022–2023 or selected in the backtest form.
After evaluating both algorithms, **Comparar estrategias** shows the evaluated
matching models alongside Markowitz and equal-weight. Model details contain the
configuration, learning metrics and checkpoint paths.

The training supervisor allows four unfinished jobs and runs one child at a
time. Pending cancellation is immediate. Running cancellation asks the child
to stop and terminates it after a grace period if needed. Startup marks jobs
interrupted by the previous API session as failed. A terminal job can start a
new job from a verified checkpoint via **Reanudar checkpoint** or the API.
For API resume, use `resume_from_job_id` and keep data, architecture, learning
and economic parameters unchanged. The requested steps are additional steps.
An episode and its random stream restart on resume.

Study commands from the repository root, with the API stopped when it owns the
default database:

```powershell
uv run --python 3.11 python scripts/run_stage3.py --mode smoke
uv run --python 3.11 python scripts/run_stage3.py --mode study
uv run --python 3.11 python scripts/run_stage3.py --mode study --continue-study
```

Use the third command for an interrupted study. It checks the snapshot and
protocol hashes, matches saved configurations, and verifies each reused model.
The study is serial on CPU with one PyTorch thread per training child. Budgets,
seeds and candidate rates are in `experiments/stage3-protocol.json`.
Reports are under `.runtime/stage3`. Set `TRAINING_ROOT` for an alternate model
directory. Keep SQLite and artifacts together when moving a local experiment.
Each job directory contains a process log, telemetry, model, normalizer and
manifest. DDPG also retains the replay buffer. Load checkpoints only from the
trusted local training directory. Inspect the process log for a failed run.

The API exposes `GET/POST /api/v1/training`, job detail and POST actions
`cancel`, `evaluate` and `compare` under `/api/v1/training/{id}`, plus
`GET /api/v1/models`. Trained-model backtests use the existing experiments API
with `model_id`. The 2024 holdout stays locked.

## Stage 4 AI Agent Desk

The desk stays disabled until the API process has all three OpenRouter settings.
Set `OPENROUTER_API_KEY` through a local secret source or in the ignored root
`.env`. The following route passed the authenticated Analyst and Judge smoke
test. For `.env`, put these two settings alongside the key:

```dotenv
OPENROUTER_MODEL=nvidia/nemotron-3.5-lightning:free
OPENROUTER_PROVIDER=nvidia/nvfp4
```

```powershell
uv run --python 3.11 --env-file .env python scripts/run_api.py
```

Use an OpenRouter workspace without mandatory web search or other tool
plugins. The adapter disables web search and response healing per request,
but OpenRouter workspace settings can prevent overrides. Keep the key out of
the frontend environment and Git. `.env.example` is a settings reference.
The backend rejects paid model IDs, verifies the selected endpoint's zero
pricing and structured-response capabilities before each completion, and blocks
failed calls. Nemotron Lightning returns its structured data in the arguments
of one named response function. The backend validates the arguments without
executing a function.
Defaults are 12 seconds per provider stage, at most one retry for transient
errors, and a process-local cap of 12 attempts/minute and 40/day. The provider
enforces its own account limits.

Open **AI Agent Desk** from the dashboard. Choose a snapshot, a valid
2022–2023 market session and a strategy, then click **Analizar propuesta**.
PPO/DDPG require a compatible saved Stage 3 model. Inspect the dated dossier,
the Judge verdict, the proposed weights, the risk gates and the recorded
provider metadata. A configured provider badge confirms local configuration.
An analysis with valid Analyst and Judge responses and both OpenRouter
traces verifies authenticated inference. A blocked run records
the failing stage and reason. The desk creates no orders or performance curve.

`GET /api/v1/agent-desk/status` shows local configuration. Submit with
`POST /api/v1/agent-desk/runs` and poll `GET /api/v1/agent-desk/runs/{id}`.
Each request contains `dataset_id`, `decision_date`, `strategy` and
`model_id` when required. The history endpoint is `GET /api/v1/agent-desk/runs`.
Jobs interrupted by a service restart are blocked with a durable event.

For explicit mock inference over the real local snapshot, build the web app
and run:

```powershell
./scripts/web.ps1 exec playwright test --config playwright.agent-desk.config.ts
```

This test harness uses ports 3124/8124, a separate SQLite file and a mock
provider injected by a test launcher. It requires the verified historical
snapshot. The normal application never substitutes mock inference.

## Tests and failure diagnosis

`uv run pytest` checks all Python modules offline. `uv run mypy` checks the new
domain modules. Ruff, `./scripts/web.ps1 typecheck`, lint/build and contracts
check application code and regenerate OpenAPI/TS.

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) '.runtime/browsers'
./scripts/web.ps1 exec playwright install chromium
./scripts/web.ps1 test:e2e
./scripts/web.ps1 test:e2e:historical
./scripts/web.ps1 exec playwright test --config playwright.training.config.ts
uv run --python 3.11 python scripts/verify_stage3_reproducibility.py
```

The baseline and historical runners own temporary services on 3000/8000.
The training runner uses separate ports and an isolated database and artifact
directory. The training and historical suites require the verified snapshot.
It stops those services on completion. Screenshots/traces live in test-results.
Browser binaries are local to `.runtime/browsers`. If ports are busy, stop your
own demo instances first; do not kill unrelated user processes.

The8 baseline browser cases remain offline-compatible. The separate2-case
historical suite requires an actually downloaded snapshot and fails if absent;
it never skips the real-data requirement or creates a synthetic substitute.
CI runs the offline suite without downloading financial data automatically.

API unavailable: verify `/health`, then `/ready`; readiness distinguishes
worker/persistence failures. The dashboard shows an error and retry button;
it never substitutes mock results when the API is offline. HTTP429 means the
16-job queue is full; HTTP422 means configuration failed validation.

Docker CLI is installed but its daemon was unavailable during audit. SQLite is
intentional. CI configuration is provided; no remote CI run or push was performed.
