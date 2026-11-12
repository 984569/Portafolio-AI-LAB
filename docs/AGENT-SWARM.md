# Native agent swarm and file ownership

Current ownership: [STAGE4-CONTRACTS.md](STAGE4-CONTRACTS.md).

## Stage 4 delivery

Three native subagents worked concurrently. Root owned shared contracts,
SQLite and API integration, the dashboard, and final test execution.

- `stage4_provider` delivered the OpenRouter adapter, explicit mocks,
  provider transport tests and observed public model/endpoint capability evidence.
- `stage4_workflow` delivered the Analyst, Quant Strategist, Judge, Chief
  workflow and tests of causal dossiers and saved-model inference.
- `stage4_safety` delivered deterministic risk checks and their adversarial
  tests, including malformed data, exposure and provider failure.

Stage 3 and earlier sections remain historical delivery records.

## Stage 3 delivery and continuation

- `stage3_ppo`: PPO trainer, configurable policy, checkpoints, and six tests.
- `stage3_ddpg`: DDPG trainer, action noise, replay-buffer checkpoints, and
  eight tests. Continuation ownership covers the historical reproducibility
  script and its JSON evidence.
- `stage3_evaluation`: causal replay, walk-forward selection, financial
  metrics and statistical comparison with 70 tests. Continuation ownership
  covers `playwright.training.config.ts`, `tests/e2e/training.spec.ts` and its
  browser captures.
- `stage3_mlops_qa`: 28 supervisor/API regressions in
  `tests/api/test_training_api.py`. Its review identified cancellation races,
  startup failure and artifact integrity cases addressed by root.
- Root: contracts, shared training code, API and dashboard integration, study
  orchestration and evidence. The continuation reuses completed study jobs
  after configuration and hash verification.

PPO, DDPG and Evaluation ran concurrently with root. MLOps/QA followed as a
slot opened. The continuation delegates only independent verification tasks.

Current Stage2 ownership supersedes the historical Stage1 table below:
[STAGE2-CONTRACTS.md](STAGE2-CONTRACTS.md). Three real specialist agents run
concurrently; root owns contracts, integration, installations and evidence.

## Stage2 actual delivery

- stage2_data: Yahoo JSON downloads for all ten real instruments, strict quality/
  calendar/action validation, immutable Parquet/raw/manifest registry,41 tests.
- stage2_quant: rolling mean-variance Markowitz and comparable EW,53 tests,
  independent review found long-job shutdown fencing and extreme log-return issues.
- stage2_simulation: Gymnasium environment and actual Gym/SB3 checks,35 initial
  tests; independent core/optimizer review contrasted200 cases each with independent
  numerical/analytic calculations. Root added the log-reward regression (36 total).
- Root: shared exact accounting, typed contracts, API/UI,246-test integration,
  real-data benchmark replays,1741-step historical environment validation,10 browser
  cases, local Node24 setup, docs/evidence. Detected review issues are fixed/tested.

No two agents wrote a shared file. No worktrees were created without a commit
base. Native delegation was used; no additional personas are claimed as agents.

Four actual concurrency slots: root plus three subagents. First wave read-only:
`environment_audit` (DevOps), `quant_academic_audit` (Quant/Data/Documentation),
`architecture_design_audit` (Architecture/Frontend/QA).

Implementation wave begins only after root publishes contracts and Stage 0.

| Agent | Exclusive writes | Read-only dependencies | Acceptance |
|---|---|---|---|
| Quant/Data | packages/portfolio_quant/, tests/quant/ | docs/architecture.md | arithmetic, invalid-data, causality tests |
| Backend | apps/api/, tests/api/ | portfolio_quant, architecture | validation, queued jobs, persistence/restart/failure tests |
| Frontend/Design | apps/web/ except generated API declarations | DESIGN, architecture, generated contracts | form/results/states, responsive UI, typecheck/lint/build |
| Root | root config/locks, docs/, scripts/, packages/contracts/, tests/e2e/, CI | all outputs | review, contract generation, integration/browser evidence |

No shared lockfile edits. Frontend may create its package.json, but root runs
the only pnpm install after package inputs stabilize. Agents do not commit,
merge, publish or touch original master. Backend cannot install packages or
change root pyproject. Deferred specialist roles are not claimed as active.

## Observed delivery

- Quant/Data: engine, ten-asset/20-observation synthetic CSV, manifest, CLI,
  51 tests; then independent API review found dead-worker acceptance and
  fixture hash divergence. Backend corrected both with regression tests.
- Backend/DevOps: FastAPI models, SQLite queue, lifecycle worker, runtime
  provenance, 36 API tests; reviewed proxy/contract boundaries read-only.
- Frontend/Design: Next/Tailwind/shadcn dashboard, proxy, states, themes,
  computed chart/tables. Root added explicit /dashboard route, corrected local
  Origin comparison and scroll containment, and made chart labels responsive.
- Root: docs, configuration/locks, generated contracts, CI/run scripts, E2E,
  independent integration checks and reviewed browser captures. No worktrees,
  commits, remote writes or platform-setting changes were made.
