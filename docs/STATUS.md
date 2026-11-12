# Verified status

As-of: 2026-11-11, America/Bogota.

- Stage 0: complete. Audit, permanent rules, design, architecture, ownership,
  plan, local environments and locked dependencies created. Bootstrap check passes.
- Stage 1: complete for the defined synthetic vertical slice. Browser submits
  a configuration, API enqueues, worker calculates, SQLite persists and the UI
  polls/renders results. Dashboard is served at / and /dashboard, with dark/light,
  data tables, allocations, audit events and provenance manifest.
- Stage 2: complete for the requested historical-data/financial-engine scope.
  Actual Yahoo responses for all ten instruments were validated and persisted
  as a2516-session Parquet snapshot. Both historical benchmarks and the Gym
  environment executed on real data. Synthetic tests alone are not this gate.
- Stage 3: complete for the requested local research scope. PPO and DDPG
  trained on the verified historical snapshot. Two smoke
  jobs, eight walk-forward candidate jobs and six final jobs completed. The
  API exposes stored models, job progress, cancellation, resume and validation.
  The dashboard shows the four-strategy comparison and saved-model backtests.
  Historical same-seed smoke reruns matched exactly in this environment.
- Current validation: 360 Python tests, 12 Chromium cases (8 baseline,
  2 historical and 2 training), Ruff, mypy, TypeScript, ESLint and production
  build passed. The generated API contracts reproduced byte for byte.
- Prior Stage1 validation:87 Python tests (51 quant +36 API),8 Chromium cases, Ruff,
  TypeScript, ESLint and production build passed. Dependency compatibility check
  passed; pnpm production audit reported no known vulnerabilities at check time.
- Visual evidence reviewed at 1440×900, 1280×900, 768×900 and 390×844,
  plus light mode and mobile chart. No page-level horizontal overflow.
- Stage 4: complete for the local PAPER research scope. Agent Desk was verified
  with real historical data, actual Stage 3 checkpoints and explicitly mocked
  inference. The Analyst and Judge also passed authenticated inference through
  the fixed free OpenRouter route `nvidia/nemotron-3.5-lightning:free` at
  `nvidia/nvfp4`. The prior Dots run remains available as historical evidence.
- Stage 5 is pending. TRL 5 has not been established.
- Original academic PDFs and tutor feedback unavailable in this checkout.
- No credentials used, global changes, publication, commits or remote writes.

See [validation report](validation-report.md), [runbook](RUNBOOK.md) and
[historical validation](evidence/stage2/historical-validation.json). The preserved
[Stage1 fixture run](evidence/stage1-fixture-run.json) is test evidence only. Screenshots are captured
from the running application, not design mockups. The E2E offline-state case
uses explicitly injected HTTP502 responses; successful-run tests use real API.
Normal runtime exposes only historical sources/results; fixtures are enabled
only inside automated harnesses. Old fixture records are hidden, not deleted.

Historical snapshot SHA256:
`bfc0b8e79e60e0c5dfaff18c52af7a113734a4c2be7fd4c849949deec3d4ebd0`.
Train1763 / validation501 / final_test252 sessions. Validation benchmarks use
500 intervals from2022-01-03 to2023-12-29. Two identical replays per strategy;
Gym/SB3 checks plus1741 training-only environment steps pass. 2024 is ingested
and quality-checked, not evaluated or used for parameter selection.

Known limits: retrospective vendor adjustments and current-universe selection;
corporate actions not independently reconciled; stylized adjusted-close fills
and proportional fees, no market-impact model. Docker daemon unavailable.
Node24.22.2 now runs locally from a verified ZIP; global Node25 was not changed.
Remote CI has not run. Third-party httpx/pandas deprecation warnings remain.
SQLite persists jobs for a single API instance. Bounded backtests use one
thread and CPU training uses a separate supervisor with one child at a time.

The 2024 holdout remains locked. Its evaluation requires approval of the final
protocol. The original academic PDFs and tutor feedback remain external
dependencies for academic delivery.

Stage 3 evidence: [study](evidence/stage3/historical-study.json),
[repeatability](evidence/stage3/reproducibility.json) and
[API checkpoint resume](evidence/stage3/api-checkpoints.json).

Stage 4 evidence: [public provider check](evidence/stage4/provider-catalog.json),
[four historical runs](evidence/stage4/historical-agent-runs.json) and
[browser records](evidence/stage4/browser-runs.json) and
[authenticated NVIDIA](evidence/stage4/authenticated-nvidia-lightning.json).
The current Python suite passed 499 tests.
