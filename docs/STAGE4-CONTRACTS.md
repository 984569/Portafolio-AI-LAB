# Stage 4 Agent Desk contracts and ownership

| Owner | Exclusive writes |
|---|---|
| LLM Infrastructure | packages/agent_desk/provider.py, tests/agent_desk/test_provider.py, docs/evidence/stage4/provider-catalog.json |
| Financial Agents | packages/agent_desk/workflow.py, tests/agent_desk/test_workflow.py |
| Safety and Audit | packages/agent_desk/risk.py, tests/agent_desk/test_risk.py |
| Root | packages/agent_desk/contracts.py, API, web, integration/E2E, shared settings, documentation |

The desk is a distinct PAPER research workflow, with no order interface.
Requests identify a registered historical snapshot, an XNYS decision close in
2022–2023 and a strategy. PPO/DDPG require a completed verified local model
whose training and frozen normalization end before the decision. Quant emits
one hypothetical allocation from cash using the last lookback+1 closes
through the decision close. RL observations mirror the Gym first allocation
(lagged log-return window and zero known weights). No future price is required.
This is a point-in-time scenario, separate from Stage 3 performance backtests.
Contemporary paper tracking is a separate scope and is not represented as an
available mode. 2024 is rejected. No news, tools, search, free-form external
text, user prompts or external links enter inference. Providers receive only
schema-validated numeric facts and closed identifiers. Model outputs are
closed labels and citations to supplied fact IDs, with explanations assembled
from local templates. Historical source adjustments are retrospective.

Interfaces in `agent_desk.contracts`:

- `DeskRequest(dataset_id, decision_date, strategy, model_id=None)`.
- `Dossier`: dataset_id, dataset_sha256, decision_date, information_date,
  assets, observations, lookback, market_return, market_volatility.
- `Candidate`: strategy, model_id, weights, annualized_volatility,
  turnover, fee_bps, optimizer_fallback.
- `Analysis`: trend (up/down/mixed), regime (low/moderate/high), evidence
  (closed set market_return/market_volatility). `Judgment`: verdict
  (approve/watch/reject), reason (aligned/concentration/volatility/caution),
  evidence (closed set market_return/market_volatility/weights/turnover/
  portfolio_volatility). No confidence or model-generated text.
- `Provider.complete(stage: str, payload: dict[str, Any], schema: type[T])
  -> tuple[T, ProviderTrace]`. Validate response with Pydantic strict models.
  Fail with `ProviderError(code, trace=None)`. Real adapter exposes
  `provider_from_env() -> Provider | None` (None when disabled/unconfigured)
  and `MockProvider` for explicit test dependency injection, never fallback.
  Nemotron Lightning uses one named function response envelope as data. Its
  arguments pass the same schema validation and the function is never executed.
  `ProviderTrace` is public metadata without keys, raw text or response bodies.
- `risk.evaluate_risk(dossier, candidate, *, provider_ok: bool) -> RiskReport`.
  Validate snapshot identity shape, dates, universe, coverage and numeric
  integrity, full-investment long-only simplex, max position 35%, ex ante
  volatility 30%, turnover from cash 1, fee 10 bps. No repair/renormalization
  of invalid proposals. Explicit codes, observed, threshold and decision
  date in gate events. These are exploratory policy thresholds.
- `workflow.run_workflow(request, panel, provider, emit, *, bundle=None)`
  where bundle is a verified `PolicyBundle` supplied by root, emit takes
  one `DeskEvent`, and result is `DeskOutcome`. Chronological state phases
  data → analyst → strategist → judge → risk → final. Emit and persist
  milestones including provider trace and failure codes. Provider errors and
  any failed gate block the proposal. Judge approve and risk pass are both
  required to label approved; approval is research-only.

Root owns SQLite append-only event storage and lifecycle, API exposure,
provider injection in integration tests, and UI. Do not edit another owner's
files. Test against the current verified snapshot without unlocking 2024.
