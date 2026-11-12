# Validation report

## Stage 4 — Agent Desk, 2026-11-11

The initial local workflow verification used mocks while
`OPENROUTER_API_KEY` was unavailable. The actual public model catalog and three
model endpoint checks
returned HTTP 200. The route `liquid/lfm-3-1.7b:free` at `liquid/fp8`
advertised zero pricing and the required JSON Schema parameters. The proposed
NVIDIA route from the master context lacked the required parameters. The
probe used no key and sent zero completion requests.
[Public capability evidence](evidence/stage4/provider-catalog.json).

With explicit mock inference, the API executed all six workflow stages for
four strategies on the real ten-asset snapshot at the 2023-12-20 close.
PPO and DDPG loaded actual Stage 3 seed-42 artifacts. All run records and
event sequences were recovered identically after restarting against the
isolated database. The mock Judge returned approve in all four runs.

| Strategy | Maximum proposed weight | Deterministic outcome |
|---|---:|---|
| Equal-weight | 10.00% | Approved for research |
| PPO | 17.74% | Approved for research |
| DDPG | 16.78% | Approved for research |
| Markowitz | 75.03% | Blocked by the 35% position limit |

These values are weights from a hypothetical first allocation from cash.
The run does not calculate performance or fills. The analyst and Judge labels
in this evidence are mock responses. [Four recorded runs](evidence/stage4/historical-agent-runs.json).

| Verification | Observed result |
|---|---|
| Python | 499 passed, comprising the previous 360 and 139 new cases |
| Agent Desk | 54 provider, 21 workflow, 51 risk and 13 API cases |
| Static checks | Ruff, mypy, ESLint, TypeScript and production build passed |
| OpenAPI | Regeneration reproduced the checked-in JSON and TypeScript contracts byte for byte |
| Chromium | 12 previous cases and one Agent Desk case passed; Agent Desk exercised 1440, 768 and 390 px |
| Failure handling | Timeout, malformed/extra JSON, wrong route, missing key and invalid weights block |
| Temporal boundary | 2024 and non-session dates rejected; later rows and untrusted metadata cannot change supplied facts |

The browser uses real historical facts and an explicitly injected test
provider. It covers approval, risk veto after a positive Judge verdict,
chronological audit history, page reload, responsive layout and the 2024
request boundary. [Desktop](evidence/stage4/agent-desk-1440.png) ·
[Tablet veto](evidence/stage4/agent-desk-768.png) ·
[Mobile](evidence/stage4/agent-desk-390.png) ·
[Browser run records](evidence/stage4/browser-runs.json).

The first Stage 3 browser regression run refreshed its published PNGs because
the existing suite wrote directly to the evidence directory. The original
Stage 3 run records remain in place. Subsequent regression screenshots go
to Playwright's test output directory.

Authenticated inference later passed using
`dots-studio/dots-3-note-preview:free` on `atlas-cloud/fp8`. The adapter
disabled this model's optional reasoning to preserve the 512-token structured
response budget. Both stage replies passed schema and route checks. The run
record survived restart and contains the usage traces and final Judge verdict.
The original Liquid configuration authenticated but did not complete the
historical scenario within its bounded output and time limits.
[Authenticated run](evidence/stage4/authenticated-openrouter.json).

The requested NVIDIA route was also verified at
`nvidia/nemotron-3.5-lightning:free` on `nvidia/nvfp4`. The endpoint advertises
zero pricing and named function responses. Both authenticated stages returned
one validated response envelope. The Judge returned watch and the event log
was recovered after restart. The backend does not execute that function.
[Authenticated NVIDIA run](evidence/stage4/authenticated-nvidia-lightning.json).

The historical data remains
vendor-adjusted retrospectively. Desk results are exploratory, separate from
academic PPO/DDPG performance and contemporary paper tracking.

## Stage 3 — historical PPO and DDPG, 2026-11-11

The recorded study completed 14 CPU jobs on the verified ten-asset snapshot.
Two separate historical smoke jobs ran 256 steps each. PPO took 0.61 s with
354.1 MiB sampled peak interpreter RSS. DDPG took 1.84 s with 358.5 MiB.
All final model, normalizer and DDPG replay-buffer files and the intermediate
checkpoints passed SHA-256 verification. Separate same-seed smoke reruns
matched learned tensors, the normalizer, 500 actions and allocations, the
501-point equity path and validation metrics exactly on this environment.

Eight jobs with 2,048 steps each covered the two predeclared rates and two
walk-forward folds for each algorithm. Mean fold Sharpe selected PPO 0.0001
(2.1181 across folds) and DDPG 0.001 (−0.3709). Six final jobs retrained
from 2015–2021 with seeds 7, 42 and 123. PPO ran 16,384 steps per seed in
34.03–35.64 s with 359.7 MiB maximum sampled interpreter RSS. DDPG ran 8,192
steps per seed in 50.73–154.89 s with 449.8 MiB maximum sampled interpreter RSS.
The interrupted DDPG seed-123 job ended with last recorded step 2,080 and no
checkpoint. The continuation reused 13 verified jobs and retried that seed
with identical configuration. The failed record remains in SQLite.

Validation used 500 close-to-close intervals from 2022-01-03 through
2023-12-29. Capital was USD 10,000, lookback 60, fee 10 bps and risk-free rate
zero. The RL rows show arithmetic means over the three seeds. The benchmark
metrics reproduce the Stage 2 validation.

| Strategy | Net return | CAGR | Volatility | Sharpe | Max drawdown | Fees USD | Total turnover |
|---|---:|---:|---:|---:|---:|---:|---:|
| Equal-weight | 14.49% | 7.06% | 14.27% | 0.5492 | 14.70% | 50.82 | 5.05 |
| Markowitz | −31.00% | −17.06% | 24.50% | −0.6403 | 37.76% | 1,260.41 | 161.02 |
| PPO | −13.94% | −7.29% | 14.88% | −0.4340 | 23.00% | 3,008.48 | 342.38 |
| DDPG | −42.56% | −24.39% | 16.69% | −1.6116 | 44.38% | 3,830.52 | 537.94 |

Sample standard deviation across seeds for net return was 2.12 percentage
points for PPO and 3.01 for DDPG. For Sharpe it was 0.0732 and 0.3276.
The exploratory 95% paired block-bootstrap intervals for seed-42 annualized
mean net-return differences versus equal-weight were [−20.78, −10.73]
percentage points for PPO and [−45.68, −19.86] for DDPG. The calculation uses
20-session blocks and 1,000 resamples. Both learned strategies had much higher
realized turnover and fees than equal-weight in this window.

The first supervisor measured the Windows virtualenv launcher instead of the
training interpreter. The historical report uses in-process RSS samples for
these jobs. The corrected supervisor samples the full process tree, includes
descendants in forced shutdown, and applies terminal-state cancellation checks
within the SQLite transaction. Restart and process-launch failures retain
explicit terminal states. The 2024 holdout remains locked.

The [historical study evidence](evidence/stage3/historical-study.json) retains
each seed, candidate/fold scores, job IDs, settings, resource measurements,
artifact hashes, metrics and weight summaries. The local runtime report also
retains every equity point and allocation. See the [reproducibility evidence](evidence/stage3/reproducibility.json)
and the [research protocol](RL-RESEARCH.md).

| Verification | Observed result |
|---|---|
| Python 3.11 pytest | 360 passed, including 78 API cases; 109 third-party deprecation warnings |
| Ruff and mypy | Passed; mypy checked 20 domain modules |
| ESLint, TypeScript, production build | Passed under repository-local Node 24.22.2 |
| OpenAPI and TypeScript contract generation | Byte-for-byte match on regeneration |
| Baseline and historical Chromium | 8 baseline and 2 real-history cases passed |
| Stage 3 Chromium | 2 passed using production build, real history, isolated SQLite and 1440/390 px viewports |
| Actual persisted study through API | All six final models in registry and eight comparison rows including both baselines |
| Real checkpoint resume through API | Both smoke policies resumed from 256 to 512 steps, with verified artifacts and worker-process RSS |
| 2024 isolation | Training and replay boundaries tested. All recorded results end by 2023-12-29 |

The Stage 3 browser run exercised both train-to-evaluation paths, the
four-strategy comparison, saved-model replay with exactly matching curves and
metrics, page reload and active cancellation. The cancelled job was absent
from the model registry. Sampled full-tree peak RSS in this run was 367.6 MiB
for PPO and 554.5 MiB for DDPG. See the
[browser run records](evidence/stage3/browser-runs.json),
[comparison capture](evidence/stage3/training-comparison-1440.png),
[mobile replay capture](evidence/stage3/training-replay-ddpg-390.png), and
[API verification](evidence/stage3/api-checkpoints.json).

Stage 3 meets its local acceptance criteria. This is an initial CPU study
using a small candidate grid, three seeds and one validation period. The
final 2024 protocol, original academic PDFs, tutor feedback and evidence for
TRL 5 remain outside this verification.

## Stage2 — real historical gate, 2026-11-10

Completed locally on Windows, Python3.11.9 and repository-local Node24.22.2.
Stage2 acceptance is supported by a real pipeline execution and actual benchmark/
environment runs, in addition to offline tests. No model training or TRL5 claim.

| Check | Observed result |
|---|---|
| Real provider | ten Yahoo HTTP200 responses; exact JSON/request/fetch metadata retained |
| Snapshot | 2516 aligned XNYS sessions,10 assets,2015-01-02 to2024-12-31 |
| Quality | zero missing sessions/duplicates/invalid price cells; raw OHLC/actions retained |
| Chronology | train1763, validation501, final_test252; final2024 evaluation locked |
| uv run pytest -q | 246 passed:51 legacy quant,50 API,15 core,41 data,53 research,36 environment |
| Ruff / mypy | clean; mypy checks11 new domain source files |
| TypeScript / ESLint / production build | passed under local Node24 |
| Baseline browser suite |8 passed; original fixture flow preserved |
| Historical browser suite |2 passed: real Markowitz1440px, real EW390px, persistence/reload/provenance |
| Reproducibility | two identical result hashes per historical strategy; immutable source hashes |
| Gymnasium/SB3 | both real check_env calls pass;1741-step training-only rollout matches benchmark accounting |
| Dependency compatibility |67 installed Python packages compatible; frozen offline installs pass |

Source Parquet SHA256:
`bfc0b8e79e60e0c5dfaff18c52af7a113734a4c2be7fd4c849949deec3d4ebd0`.
The final root ingestion reused the ten verified responses already downloaded
by Data Agent; it did not duplicate provider traffic. JSON fetch times and hashes
are recorded in [pipeline progress](evidence/stage2/pipeline-progress.json).
All raw prices remain local/ignored; evidence contains metadata and derived results.

### Actual validation outputs

Defaults fixed before observing these results: initial10000USD, fee10bps on
buys+sells, W60, risk aversion5, risk-free0, seed42, long-only. Both use exactly
500 close-to-close intervals,2022-01-03 through2023-12-29. No final2024 return
was evaluated and no parameter was changed to improve the observed result.

| Metric | Equal weight | Markowitz |
|---|---|---|
| Final simulated equity USD |11448.86 |6900.21 |
| Net cumulative return |14.49% |-31.00% |
| Annualized volatility |14.27% |24.50% |
| Sharpe |0.5492 |-0.6403 |
| Maximum drawdown magnitude |14.70% |37.76% |
| Total simulated fees USD |50.82 |1260.41 |

Markowitz's loss and high turnover are retained as observed. Functional
optimization is not evidence of superiority or profitability. Full precision,
configuration, solver settings and result hashes are in
[historical validation](evidence/stage2/historical-validation.json).

### Review findings repaired

- Worker.close's5-second join could leave a running writer after lifespan ended.
  Shutdown now waits for the current bounded calculation; a regression exercises
  a job exceeding5seconds before reopening the same database.
- For an extreme positive valuation, net_return can round to-1; log1p became
  negative infinity. Log reward now uses log(next_equity)-log(previous_equity).
- Corrupt historical registries return503, missing snapshot404, without synthetic
  fallback. Historical snapshot hashes are checked against the submitted run.
- Synthetic datasets/jobs/history are disabled in normal runtime. Automated
  harnesses opt in explicitly; historical E2E disables fixture mode. A regression
  verifies normal mode hides old fixture records without deleting evidence.
- Current execution-time drift stays internal; Gym observations only contain
  lagged targets/returns. Tests perturb the same/future close and2024 data.

### Durable current evidence

[Quality report](evidence/stage2/data-quality.json),
[actual browser run metadata](evidence/stage2/browser-runs.json),
[desktop](evidence/stage2/dashboard-markowitz-1440.png),
[Markowitz curve](evidence/stage2/chart-markowitz-1440.png),
[mobile curve](evidence/stage2/chart-equal_weight-390.png).
Successful historical E2E uses the real local snapshot/API/worker/SQLite;
it has no network mock and fails if the required historical dataset is absent.

### Remaining limits

Yahoo adjusted history is retrospectively revised and actions are not independently
reconciled. Index-causality tests do not establish a point-in-time data vintage.
The current universe has selection/survivorship limitations. Trades are stylized
adjusted-price simulations with proportional fees, not live fills or impact models.
Only Chromium is browser-tested. This is not a full accessibility/security audit.
Five third-party deprecation warnings (httpx and pandas/calendar) remain; tests pass.

Docker daemon remains unavailable, so SQLite is intentional. Local Node24 ZIP
checksum was verified against nodejs.org:
`CA1BFF5D8EAD13C9F2EA404A176DB46BD430704D5B5113734049FA365E7799E2`.
Global Node25 was not modified; the official [Node release table](https://nodejs.org/en/about/previous-releases)
marks25 EOL. CI is configured for24 but has not run remotely. No credential use,
global changes, publication or commits. Academic source PDFs/tutor feedback remain
unavailable in the repository and matching Downloads search. PPO/DDPG, training
walk-forward, final holdout evaluation, notebook/Colab validation and TRL5 are pending.

## Previous Stage 0 / 1 validation evidence — 2026-11-09

Verified locally on Windows, Python3.11.9, Node25.2.1; recorded 2026-11-09
(America/Bogota). The scope is an engineering fixture vertical slice, not
historical strategy performance, completed academic requirements or TRL5.

| Command/check | Observed outcome |
|---|---|
| uv sync --python 3.11 | local .venv, uv.lock, 24 installed packages |
| pnpm install | workspace dependencies installed, pnpm-lock.yaml |
| uv sync --frozen --offline / pnpm install --frozen-lockfile --offline | locks reused successfully, no resolution or dependency changes |
| uv run python scripts/check_bootstrap.py | 11 required files, valid TOML/JSON, Python3.11 |
| uv run pytest | 87 pass: 51 quant and 36 API |
| uv run ruff check . | pass |
| pnpm contracts | OpenAPI exported and TS generated successfully |
| pnpm typecheck | pass; latest production build also runs TypeScript |
| pnpm lint | pass, no lint warnings after PostCSS config correction |
| pnpm build | pass, /, /dashboard and dynamic backend proxy built |
| pnpm test:e2e | 8 pass in Chromium, final run 12.7 seconds |
| uv pip check | 24 installed packages compatible |
| pnpm audit --prod | no known vulnerabilities reported at check time |
| uv run python scripts/run_fixture.py | valid finite JSON, 20 points, ten fictional assets |
| development servers | API/ready and /dashboard HTTP200; Next dev started successfully |

After the demonstration, owned preview processes were stopped and ports3000/
8000 verified free. A completed fixture demonstration remains in the ignored
default local database; no real market data is stored there.

Successful E2E runs use real FastAPI, worker, quant and SQLite, with a unique
ignored database per suite. The browser submits capital/cost configuration,
waits for completion, compares rendered numbers to API persistence and reloads.
Other cases verify proxy rejections, error/retry UI (explicit502 injection),
1440/1280/768/390 widths, theme persistence and visible keyboard focus.

## Regressions found and repaired

- Worker crash accepted new queued jobs: now rejects503 without persistence.
- Fixture changed after enqueue: hash mismatch fails the job, never completed.
- Same-origin127.0.0.1 browser writes were403 because Next normalizes nextUrl:
  proxy compares Origin against the validated local Host header. Both127 and
  localhost origins are covered by E2E.
- Mobile document overflow: absolute screen-reader text in a horizontally
  scrolling table lacked a containing block. Positioning the scroll region
  contains it; the full document now fits390px without hiding page overflow.
- Fixed SVG viewBox shrank mobile labels: responsive measured viewBox preserves
  label size and reduces mobile date ticks; reviewed [mobile chart](evidence/chart-390.png).

## Durable artifacts

- [Desktop](evidence/dashboard-1440-viewport.png),
  [1280](evidence/dashboard-1280-viewport.png),
  [tablet](evidence/dashboard-768-viewport.png),
  [mobile](evidence/dashboard-390.png),
  [light](evidence/dashboard-light.png), [empty](evidence/dashboard-empty.png).
- [Persisted fixture run](evidence/stage1-fixture-run.json) exported read-only
  from the final E2E database. Screenshots show distinct actual runs in that
  suite; all visual runs use the same documented fixture configuration.
- SHA256 of source fixture:
  `b6fed50dcf0ffb19c3ba0dd257f139fbc72ccdace0ed7cddedeb679959dbbc91`.

## Limits and warnings

- Docker daemon unavailable; PostgreSQL/Compose not run. CI workflow is written
  but not executed remotely. No publication or credential use.
- Actual browser checks used Chromium only. 1280 was tested at900px height,
  not the800px variant from the original suggested matrix. No full accessibility
  audit, independent security scan or RL training is claimed.
- FastAPI/Starlette TestClient emits an httpx deprecation warning; tests still
  pass. pnpm flags ESLint9 as deprecated on install; framework-compatible lint
  runs clean. Node25 is installed; Node24LTS is the unexecuted CI target.
- Academic PDFs/tutor feedback absent, historical data absent, Markowitz,
  Gymnasium, PPO/DDPG, walk-forward and Agent Desk not started.
- Git exists but has no commits. Manifest records git_commit=null and dirty
  state honestly. Worktrees require a commit base; this wave used exclusive
  directory ownership. No commit/push/remote permission changes performed.
