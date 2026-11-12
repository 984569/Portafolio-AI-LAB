# Architecture decision record

- ADR-001: native collaboration tools verified by three actual read-only agent
  starts. Four total slots = root + three specialists. No global Codex setting
  changed. Specialists run GPT-6.1 Sol High as requested in the master context.
- ADR-002: reuse existing initialized checkout. No commits yet, so a worktree
  cannot branch from HEAD; avoid an unsolicited bootstrap commit. Use exclusive
  directory ownership in this wave; reconsider managed worktrees after a clean
  accepted baseline. Existing origin preserved; no push/fetch required.
- ADR-003: Python 3.11 explicitly; launcher defaults to 3.14. Node 25.2.1 is
  installed (not LTS); verify compatibility locally and pin Node 24 LTS in CI.
- ADR-004: SQLite fallback because Docker daemon unavailable. No global Docker
  startup or settings changes. DELETE journal avoids unverified WAL assumptions.
- ADR-005: synthetic data is an engineering fixture, never financial evidence.
  No external data downloads, provider credentials or paid calls in Stage 1.
- ADR-006: fixed exogenous equal-weight policy allows the documented close-to-
  close fixture model. Signal-based strategies require a separately frozen lag.
- ADR-007: typed OpenAPI contract generated for frontend; no canonical PnL
  computed in JavaScript. Local proxy reduces browser CORS configuration.
- ADR-008: one native worker thread is sufficient only for the tiny bounded
  fixture. CPU-heavy training must use a separate process/worker in Stage 3.
- ADR-009: local Host/Origin is validated rather than comparing Next's normalized
  nextUrl origin. Browser127.0.0.1 and localhost proxy tests both pass.
- ADR-010: keep Next16's short generated apps/web/AGENTS.md guidance; it points
  future agents to bundled framework docs and does not duplicate the master.
  Root rules remain the project authority. No Codex/global config is changed.

- ADR-011 (Stage2): share exact self-financing proportional-fee accounting
  between historical benchmarks and Gym; preserve legacy fixture results/version.
- ADR-012: historical decisions use closes through t-1; execution at adjusted
  close t is a declared stylized convention. Final2024 is ingestion/quality only.
- ADR-013: Yahoo direct chart JSON used after a legitimate public request worked;
  original payloads retained, no throttling bypass or synthetic substitution.
- ADR-014: Node24.22.2 ZIP+official SHA256 installed inside ignored .runtime;
  process-local wrapper avoids changing the global Node25 installation/PATH.
- ADR-015: normal application mode is historical-only. Fixtures are opt-in
  automated test inputs; old records are preserved without production exposure.
- ADR-016: bounded historical jobs may exceed5seconds; full join on shutdown
  prevents a stale writer from overwriting subsequent database recovery.
# Stage 3 decisions

- The initial study fixes two pre-2022 development folds, two rates per
  algorithm and three final seeds. Selection uses fold Sharpe. Scoring in
  2022–2023 preserves all seeds. See the [protocol](../experiments/stage3-protocol.json).
- Static train-partition observation statistics are persisted with each model.
  Validation uses deterministic inference and the Stage 2 execution and
  accounting conventions. The holdout remains locked.
- A single local supervisor runs one CPU training child at a time. Cancellation
  updates are transactional. Resource monitoring accounts for the Windows
  launcher and its descendants.
- Study continuation reuses completed jobs by exact configuration, dataset and
  artifact hashes. Policy resume restores checkpoint state and restarts the
  episode and random stream.

## Stage 4 decisions

- Agent Desk is an exploratory historical scenario, separate from Stage 3
  performance results and any contemporary paper portfolio. It studies one
  allocation from cash with a dated close and records no fills or returns.
- For historical prompts, use the verified numeric facts from the as-of window.
  Restrict model responses to labels and evidence identifiers. The application
  explains them through fixed templates. No confidence score is produced.
- The desk's initial exploratory limits are 35% per asset and 30% annualized
  volatility from the trailing return window, with long-only full investment,
  turnover of one from cash and a 10 bps fee assumption.
- Pin a free route per backend configuration and preflight its advertised
  capabilities. A fixed route and temperature zero make runs traceable.
  Hosted model output may vary. Mocks enter only through test dependency injection.
