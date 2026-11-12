# PORTFOLIO AI LAB
## Master Context, Autonomous Development Charter, Multi-Agent Swarm Playbook and Product Specification

> **START HERE, CODEX.** This is the canonical bootstrap document for the existing local folder `Portafolio-AI-LAB`.
>
> **Owner request:** Build a serious, beautiful, technically rigorous quantitative portfolio research platform, using Codex as an agentic software engineering system with multiple subagents in parallel wherever the environment supports it. The project is an applied Software Engineering graduation project at UNAD, with a fixed academic core and optional advanced AI features. Start by configuring the environment and breaking down the work; implement in verifiable stages instead of creating a vast untested codebase in one pass.
>
> **Language:** Communicate with the human in **Spanish**. Code, identifiers, comments where appropriate, and technical architecture documents may be in **English** for consistency. Do not assume an unverified environment or claim work was completed when it was not.
>
> **As-of date:** 2026-11-09. Academic phase-4 submission deadline from guide: **2026-11-22**. Prioritize shippable, reproducible academic functionality.

---

# 0. BOOTSTRAP: WHAT TO DO ON FIRST READ

You are the **Orchestrator / Principal Engineer**. Read this entire specification, inspect the actual local repository, identify tool and permission support, and execute the following sequence:

1. Confirm that the active workspace is the user-created folder `Portafolio-AI-LAB`; NEVER silently initialize another folder elsewhere.
2. Inspect filesystem, OS, available dependencies, versions, existing Git state, branch, uncommitted work, permissions, available Codex tools, skills, plugins, browser/Playwright access, and multi-agent capabilities. Never invent capabilities.
3. **Enable supported native subagent orchestration in the Codex application/session if available** and use bounded parallel tasks. If the app does not expose it, use isolated Codex app threads/worktrees for independent tasks where supported. Do **not** claim that an instruction in this Markdown automatically activates a platform feature, and do not fabricate configuration keys.
4. Assign independent subagents to `environment/repository audit`, `academic requirements/quant methodology audit`, `architecture/security audit`, and `visual/design research audit`, ideally simultaneously, with **read-only work for the first wave**. Root integrates findings.
5. Produce a concise architecture decision record, dependency audit and phased execution plan, then create foundational project docs and safe scaffolding when authorized by current agent tool permissions.
6. Create a concise root `AGENTS.md` that references this document. Do not paste the entire master document into multiple nested `AGENTS.md` files: unnecessary duplication harms context. Put detailed specialized instructions in `docs/` or skills and load on demand.
7. Make the **first vertical slice** executable end-to-end with REAL or explicitly labeled FIXTURE data: API healthcheck, sample backtest job, persistence, and web dashboard showing actual resulting metrics. Use an equal-weight baseline first, then add Markowitz, PPO and DDPG.
8. Track work with durable files, e.g. `docs/PLAN.md`, `docs/STATUS.md`, `docs/DECISIONS.md`, `docs/TEST-MATRIX.md`, and scoped issues. Never assume progress based only on a previous chat.
9. The owner wants **real engineering progress, not endless approvals**. Carry out safe local, reversible actions; request confirmation for material risks (installing global dependencies, extra paid services, live-trading switches, deleting files, destructive Git, external publication, changing original research scope).
10. For every completed stage: run checks, show evidence, explain limitations, update status, create a clean commit if appropriate/approved, and propose the next stage.

**First response in Codex:** In Spanish, briefly show inspection findings, actual multi-agent availability, named agent assignments, proposed initial architecture, and the exact first implementation batch. Do not fabricate installation results or test passes. The user specifically wants aggressive and efficient agentic parallelism, but not uncontrolled filesystem conflicts.

---

# 1. VISION, IDENTITY AND NON-NEGOTIABLE PRINCIPLES

**Product name:** Portfolio AI Lab (repository/folder `Portafolio-AI-LAB`).

**Positioning:** Premium, research-grade AI-powered portfolio optimization laboratory that combines classical quantitative strategies, deep reinforcement learning, risk controls, realistic backtesting and explainable LLM-assisted research, with a polished modern trading-terminal-like web application.

**Academic mission (must deliver):** Build and validate an integrated functional prototype of dynamic allocation over 10 liquid instruments using PPO and DDPG, compared against equal-weight and Markowitz portfolios, with walk-forward methods and risk-adjusted evaluation. Document and demonstrate as a UNAD Phase 4 project.

**Product extension:** A separately isolated **AI Agent Desk**, inspired by multiagent analysis/trading architectures. Agents can interpret market context and propose allocations, but **cannot bypass the deterministic risk engine**. Real-money trading, perps, shorting, leverage and memecoin sniping are NOT in the Phase-4 scope and should NOT be enabled.

**Engineering principles:**
- Research reproducibility over flashy unverifiable claims.
- No fabricated market data, backtest numbers, performance reports, model files, API responses, trade executions or screenshots.
- Honest distinction: research proposal vs implemented feature vs validated outcome.
- Temporal correctness: no training/evaluation leakage and no future information available to historical decisions.
- Data provenance, run manifests, versioned datasets/configurations, calibrated metrics.
- Modular architecture, typed contracts, deterministic risk checks, strong testing.
- Distinct permissions: observation → proposal → approval/rejection → PAPER simulation; no autonomous real execution.
- Faults are fail-closed for trade proposals, never fail-open.
- Transparency: record rejected candidate actions as well as accepted ones.
- Professional quality, distinctive design and accessibility; visual polish never substitutes for functional truth.
- Do not introduce unnecessary distributed infrastructure, microservices, crypto execution or paid dependencies to satisfy an academic prototype.

---

# 2. PRIMARY ACADEMIC SOURCES AND EXACT REQUIREMENTS

**Grounded in user-supplied documents:**
1. `Guía de aprendizaje para el desarrollo del componente práctico - Fase 4 - Componente práctico - Práctica Simulada.pdf` (UNAD, project grade 202016907, six pages).
2. `Fase 3 - Formulación del proceso metodológico investigativo.pdf` (submitted academic master, 40 pages).
3. `Guía de aprendizaje - Fase 3 - Formulación del proceso metodológico investigativo(1).pdf` (previous phase).
4. `F-7-9-1 Presentación Propuesta Proyecto Aplicado(1).pdf` (original applied-project proposal).

**Important:** These source files were supplied to the assistant, but Codex might NOT have them mounted in the local user repository. Treat the requirements below as a faithful transcription/summary, not as permission to claim the original PDFs exist locally. If they are available in the workspace, compare before editing academic content. If not, proceed based on this detailed spec and list any source verification gaps.

## 2.1 Phase 4 from guide, exact logistics
- Course: Proyecto de grado, code 202016907.
- Phase referred to by user as Task 5; in the practical guide it is **Activity 4 / Phase 4: Desarrollo de la propuesta ingenieril del proyecto**.
- Collaborative simulated practical activity.
- 150 points.
- Activity dates: October 25, 2026 to **November 22, 2026**.
- Learning target: functional software prototype with **TRL 5 minimum**, development of agile methodology.
- Adjust previously delivered master report based on the tutor's Phase-3 feedback (feedback not yet supplied: do not invent).
- Document all agile development lifecycle stages; strengthen requirements analysis and integrated design.
- Implement a functioning prototype using the stated methodology and technologies.
- Upload source code to **GitHub**, grant/read-enable the tutor as appropriate.
- Make a **video of at most 10 minutes**, demonstrating handling and operation; all project members must have their webcam enabled and be visible throughout the socialization.
- Deliver **one revised master document** per project, with annexes including GitHub and video links.
- Share project document and constructively participate in the forum.
- No fabricated demonstration, synthetic grading evidence or false TRL claim.

## 2.2 Project proposal and participants
- Spanish research title: **Optimización dinámica de portafolios financieros mediante aprendizaje por refuerzo profundo aplicado a activos líquidos**.
- Main researcher: **Martín Castrillón Vásquez**, product lead and research lead.
- Coinvestigators: **Eduardo Jesús Daza Cañizares** and **Eliana Marcela Monsalve López**.
- Institution: Universidad Nacional Abierta y a Distancia (UNAD), Ingeniería de Sistemas, CEAD Medellín, ECBTI.
- The university master project timeline is **SIX MONTHS**, not twelve months. Approx. **12 two-week Scrum sprints** within six calendar months. This is distinct from the near-term Phase-4 deliverable date.
- Research method: applied quantitative, experimental evaluation; CDIO (Conceive, Design, Implement, Operate) engineering approach + agile Scrum for development.
- Original target in Phase 3 was TRL 4; Phase-4 guide requires TRL 5. Do not change an unvalidated experiment's status simply by editing a label. Explain precisely which relevant-environment integration tests support any TRL-5 assertion.

## 2.3 Portfolio universe and data partitions
Proposed **10 tickers**, subject to checking actual coverage and adjusted history:

| Ticker | Instrument | Category |
|---|---|---|
| AAPL | Apple Inc. | Technology |
| MSFT | Microsoft Corp. | Technology |
| JPM | JPMorgan Chase & Co. | Financials |
| JNJ | Johnson & Johnson | Healthcare |
| XOM | Exxon Mobil Corp. | Energy |
| PG | Procter & Gamble | Consumer staples |
| KO | Coca-Cola | Consumer staples |
| WMT | Walmart | Retail |
| SPY | SPDR S&P 500 ETF | Broad equities |
| GLD | SPDR Gold Shares | Gold exposure |

Period: **January 2015 through December 2024**. Split chronologically:
- Train: **2015–2021**.
- Validation: **2022–2023**.
- Final holdout test: **2024**.
- **Walk-forward** over development history 2015–2023; 2024 remains untouched for final hyperparameter-locked evaluation. Rigorously define rolling/expanding windows, retraining cadence and embargo if appropriate.
- Include consistent handling of splits/dividends/adjusted close, timestamp alignment, holidays, missing values, symbol historical availability and survivorship bias. Verify the selection and report limitations, not hide them.
- Daily rebalance is the proposal; use market data available at decision time, apply weights to subsequent returns, and document order fill timing.
- Initial design: **long-only, no leverage, no derivatives, no short selling, no high frequency**, no exchange-connected live trading. No consumer-facing trading platform or real investment advice.

## 2.4 The 12 functional requirements from the Phase-3 submission
Maintain IDs and traceability without silently rewriting them:
- **RF1** Download and store daily historical price series of the 10 selected assets.
- **RF2** Clean data and calculate returns and technical indicators.
- **RF3** Chronologically divide data into train, validation and test.
- **RF4** Simulate the market as an MDP with transaction costs.
- **RF5** Train PPO and DDPG agents on the same environment.
- **RF6** Execute walk-forward validation over development data (2015–2023).
- **RF7** Execute final backtest on 2024 without modifying hyperparameters using the test data.
- **RF8** Calculate Sharpe ratio, cumulative return, annualized volatility and maximum drawdown.
- **RF9** Build equal-weight and Markowitz baselines using only information historically available at each decision time.
- **RF10** Compare models with the same assets, capital, rebalance cadence and transaction-cost assumptions.
- **RF11** Allow configuration of transaction costs, risk-free rate, hyperparameters and random seed via configuration files.
- **RF12** Generate comparative tables and charts.

## 2.5 The 5 non-functional requirements from Phase 3
- **RNF1:** reproducibility: fixed seeds, versioned dependencies, version-controlled code.
- **RNF2:** prevent any temporal lookahead / leakage.
- **RNF3:** modularity: separate data, environment, agent, evaluation.
- **RNF4:** readable commented code and comprehensible execution notebook.
- **RNF5:** feasible training in Google Colab with available resources.

Additional engineering requirements (proposed, NOT claimed as official UNAD requirements): security, accessibility, robust API error handling, CI, reproducible deployment, auditability, clear simulated mode, test coverage and useful logging.

## 2.6 Six-month project schedule, not twelve months
| Month | Focus | Deliverable |
|---|---|---|
| 1 | Literature, universe confirmation, data ingestion | Initial datasets and requirements |
| 2 | Cleaning, features, MDP design | Processed dataset and environment design |
| 3 | Implement Gymnasium environment and PPO | Functional simulator and PPO baseline |
| 4 | DDPG, training and hyperparameter validation | PPO/DDPG trained artifacts |
| 5 | Backtesting, walk-forward and 4-strategy comparisons | Experiment results |
| 6 | Analyze, document, validate, present | Documented prototype and academic report |

This is an overall research plan. The immediate **Phase 4 deadline is 2026-11-22**, requiring a focused executable deliverable, not a fictitious completion of six months of work.

## 2.7 Team academic ownership vs autonomous coding agents
- Martín: research leadership, experimental methodology, core design, technical integration, final validation.
- Eduardo: historical data, processing, classical benchmarks, financial calculations.
- Eliana: Scrum records, QA, requirements traceability, technical documentation, reporting/visual output and presentation coordination.
- Codex subagents are **coding collaborators**, NOT replacements for actual human participation. Never falsely attribute Codex-produced artifacts to a human participant who did not contribute.

---

# 3. PRODUCT FUNCTIONAL SCOPE AND PRIORITIES

## 3.1 Must-have academic MVP (P0)
- Robust market-data ingestion and local cache / provenance.
- Frozen training/validation/test splits.
- Typed experiment configuration and meaningful validation.
- Equal-weight strategy with correct accounting and transaction costs.
- Markowitz (optimization with stable constraints and safe fallback).
- Gymnasium-compatible long-only portfolio environment.
- PPO and DDPG on the same environment; training artifacts and metadata.
- Walk-forward over development data with independent 2024 evaluation.
- Return, volatility, Sharpe, max drawdown, equity curves and allocation histories.
- Deterministic risk gates and logged veto reasons.
- API backend that serves real persisted runs and results.
- Attractive dashboard to create/inspect experiments, compare strategies, view trades, allocations, equity curves and run statuses.
- Test suite, documented setup and runnable validation demonstration.
- GitHub repository, report artifacts, and <=10-minute live recorded demo with all three participants on camera.

## 3.2 Product-quality capabilities (P1)
- Agent Desk with OpenRouter analyst and structured decisions, but no independent execution.
- Judge with constrained allowed choices and independent rule gate.
- Detailed audit trail and shadow evaluation of rejected proposals.
- Configurable experiment profiles, saved configurations and model registry.
- Job progress via polling or WebSocket, concurrency caps and cancellation.
- Professional onboarding, empty states, responsive layouts, UX polish.

## 3.3 Deferred explorations (P2, not required for academic submission)
- Paper trading with non-historical live feeds.
- A broader agent roster: analyst, scout, market regime, counterargument, portfolio judge, reporting chief.
- Crypto market-adapter for new pools, wallet distribution, contract safety, liquidity.
- Simulated short, margin and perpetuals with correct funding, liquidation, fees and market-specific risk rules.
- Broker/exchange execution integrations. **Explicitly out of current project scope: do not implement or enable with real funds without a new user authorization and security review.**

## 3.4 Main user journeys
1. Open dashboard → see real project state, strategies, current simulation mode and recent experiments.
2. Configure dataset/universe, dates, transaction costs and seeds → validate settings and submit backtest.
3. Watch job status and see diagnostic errors clearly.
4. View equity curve, comparative metrics, allocation evolution, run metadata and per-strategy trades.
5. Inspect PPO/DDPG artifacts and compare against Markowitz/equal weight on the same split.
6. Open Agent Desk → request constrained analysis of a known, dated dataset → receive explanation, gated proposal and audit trail.
7. Open risk audit → see which proposals failed and why.
8. Export CSV/JSON and chart images or report-ready tables (only for actual computed data).

---

# 4. TECHNICAL STACK, REPOSITORY AND SERVICE BOUNDARIES

**Preferred stack, adjust to environment after inspection:**
- Frontend: Next.js (App Router), TypeScript strict, Tailwind CSS, shadcn/ui, Lucide icons.
- Charts: TradingView Lightweight Charts for market/price visualizations; Recharts/Plotly for comparative performance; choose based on licensing/performance.
- Animation: Motion/Framer Motion, minimal and `prefers-reduced-motion` friendly.
- Backend: FastAPI, Pydantic v2, modern Python 3.11/3.12.
- Quant: NumPy, pandas, SciPy, PyTorch, Gymnasium, Stable-Baselines3; use algorithms correctly.
- Optimization: SciPy or cvxpy as justified, with documented constraints and numerical checks.
- Data: provider adapter with `yfinance` first, Alpha Vantage optional (verify licenses/actual API). Keep raw and processed files with provenance.
- Persistence: PostgreSQL for runs and structured events, Parquet for price tables/results; SQLite allowed as a local demo fallback if Docker unavailable.
- Worker: background queue for CPU/GPU training; prefer a simple safe process/task worker first, then RQ/Redis if necessary. No training inside HTTP handlers.
- Package management: uv for Python; pnpm for TS if available; lock files.
- Local containers: Docker Compose if available; do not require Docker to run unit tests.
- Tests: pytest, pytest-asyncio/HTTP client, domain invariants, Playwright E2E, TypeScript typecheck, lint and build.
- GitHub Actions CI on main and PR for fast checks. Longer training under manual workflow or separately.
- Model inference provider: OpenRouter via backend-only HTTPS; use model ID/config in environment, NEVER client-side API keys.

**Monorepo blueprint, simplify as needed for the first vertical slice:**
```text
Portafolio-AI-LAB/
├── AGENTS.md
├── PORTFOLIO_AI_LAB_CODEX_MASTER_CONTEXT.md
├── DESIGN.md
├── README.md
├── .gitignore
├── .env.example
├── docker-compose.yml
├── .github/workflows/ci.yml
├── apps/
│   ├── web/                          # Next.js, app routes, UI, charts
│   └── api/                          # FastAPI, schemas, routes, auth/config
├── packages/
│   ├── market_data/                  # providers, normalization, splits
│   ├── portfolio_env/               # Gymnasium, accounting, constraints
│   ├── strategies/                  # equal, Markowitz, PPO, DDPG
│   ├── backtesting/                 # replay, walk-forward, metrics
│   ├── risk_engine/                 # deterministic fail-closed gates
│   ├── ai_agents/                   # OpenRouter, analyst/judge, JSON schemas
│   └── contracts/                   # shared API schema/types where helpful
├── workers/                          # training/backtesting jobs
├── experiments/                      # configurations/manifests; generated outputs ignored
├── tests/                            # unit/integration/regression fixtures
├── docs/
│   ├── PLAN.md
│   ├── STATUS.md
│   ├── DECISIONS.md
│   ├── ARCHITECTURE.md
│   ├── DATA-PROTOCOL.md
│   ├── EXPERIMENT-PROTOCOL.md
│   ├── TEST-MATRIX.md
│   ├── AGENT-SWARM.md
│   ├── UX-SPEC.md
│   ├── SECURITY.md
│   ├── RUNBOOK.md
│   └── UNAD-PHASE4-EVIDENCE.md
└── scripts/                           # reproducible dev/test/demo tasks
```

Avoid publishing bulky raw datasets or model weights to Git. Use artifact storage or Git LFS when actually justified. Never commit `.env`, private keys, tokens, API responses containing secrets or proprietary datasets.

## 4.1 Contract-first boundaries
- UI only uses typed HTTP/WebSocket APIs, never calculates canonical PnL itself.
- Backend validates requests and config; worker handles long operations.
- Quant package runs independent of web/API and can be verified by CLI and notebooks.
- Risk engine returns typed allow/reject decisions, never silently adjusts weights unless explicit projection policy is configured and logged.
- LLM agent has access to **read-only** market/experiment tools and can propose, explain or request re-evaluation; it cannot call an execution broker or bypass hard limits.
- Paper simulator alone converts validated target weights into virtual trades.
- Every strategy produces a uniform `TargetAllocation` (instrument identifiers, as-of timestamp, weights, strategy/version, run ID, evidence references).
- Version JSON APIs and generate OpenAPI/TypeScript clients or checked schemas where useful.

## 4.2 Core entities (initial schema proposal)
`Asset`, `MarketBar`, `DatasetSnapshot`, `DataQualityReport`, `ExperimentConfig`, `ExperimentRun`, `StrategyRun`, `ModelArtifact`, `TargetAllocation`, `RiskGateResult`, `DecisionRecord`, `SimulatedOrder`, `SimulatedFill`, `PortfolioPosition`, `PortfolioSnapshot`, `BacktestMetric`, `AgentDossier`, `LLMVerdict`, `AuditEvent`, `JobStatus`.

All events should include an immutable ID, observation/as-of time, creation time, run ID, model/strategy version, source and status. Never confuse event ingestion timestamp with information availability timestamp.

## 4.3 Minimum API draft (validate/iterate)
- `GET /health`, `GET /ready`.
- `GET /api/v1/assets`, `GET /api/v1/datasets`.
- `POST /api/v1/experiments`, `GET /api/v1/experiments`, `GET /api/v1/experiments/{id}`.
- `POST /api/v1/experiments/{id}/run`, `GET /api/v1/jobs/{id}`.
- `GET /api/v1/experiments/{id}/metrics`, `/equity`, `/allocations`, `/orders`.
- `GET /api/v1/experiments/{id}/audit`.
- `POST /api/v1/agents/analyze` (read-only context with date gates).
- `GET /api/v1/model-providers/status` (no secret values).
- No live-order endpoint.

## 4.4 Suggested first vertical slice
- Deterministic small fixture of price data with exact known expected values; label fixture explicitly.
- CLI and API create an equal-weight backtest over it.
- Persist run, metrics, equity and allocations.
- Web UI lists run and draws actual curve.
- Unit tests assert hand-calculated PnL, fee treatment and no lookahead.
- Integration/E2E test proves browser → API → calculation → DB → browser.
- Replace demo fixture with sourced, versioned historical data as soon as ingestion is ready.

---

# 5. QUANTITATIVE ENGINEERING AND EXPERIMENTAL SCIENCE

## 5.1 Experiment formalization
Let `P[t, i]` be valid adjusted prices for asset i at close t. Define `r[t+1, i] = P[t+1,i]/P[t,i] - 1`. If the policy uses information up to close t, `w[t]` impacts t→t+1 returns, with carefully specified next-bar execution, turnover and slippage. Avoid same-bar lookahead.

Portfolio constraints, initial academic mode:
- 10 selected assets (unless missing-asset policy explicitly documented).
- Long-only: each weight 0..1; sum weights = 1 within numerical tolerance (cash may require a specifically documented alternative, not silently introduced).
- No leverage, shorts, derivatives or real orders.
- Maximum per-asset weight as a configurable **research assumption**, not as a fact from the submitted source; choose and document if used.
- No borrow/funding, but include costs of rebalancing, with configurable bps and optional slippage model.
- Apply fractional holdings/cash and accounting rules consistently, if implemented.

**IMPORTANT:** Action transformation must be algorithm-compatible: PPO and DDPG both may emit continuous vectors; simplex mapping/projection and its behavior must be documented, validated and tested. A naive action normalization can distort optimization. Consider softmax action transformation or explicit projection on the simplex, with reproducible benchmark comparability.

## 5.2 MDP
- **State:** lagged returns/indicators, current weights, optional available cash, time-safe risk features; each feature computed with data available up to t only.
- **Action:** continuous vector mapped to admissible target weights.
- **Transition:** market moves, assets revalued, orders simulated, fee/slippage accounting, state updated.
- **Reward:** risk-aware, well-defined, e.g. `log(V[t+1]/V[t]) - lambda * cost - gamma * risk_penalty`; ensure no double-counting fees, use known risk lookback windows only, document coefficients before holdout.
- **Termination:** end of chronological episode or defined failure; no synthetic reset that leaks future observations.
- **Observation spaces:** stable, finite, numeric and compatible with Gymnasium/SB3, with invariant validation.
- **Training:** distinct seeds, run manifests, reasonable caps on expensive runs; provide fast smoke training and separate full evaluation.

## 5.3 PPO vs DDPG
- Both on same assets, state/feature definitions, train/validation/test windows, initial capital, fees, rebalance frequency and environment.
- Use Stable-Baselines3 default baselines initially; log hyperparameter differences and reasons.
- DDPG requires action noise/exploration handling; PPO may require reward normalization; do not blindly use identical hyperparameters.
- Persist model, config, train dataset fingerprint, dependency versions, Git commit and seed.
- Repeated seeds as compute permits; avoid interpreting a single lucky training as superiority.

## 5.4 Benchmarks
- Equal-weight: define daily rebalancing vs periodic buy-and-hold clearly, with matching costs. If using daily rebalance because academic protocol says so, account for turnover.
- Markowitz: estimate parameters only from past rolling window as-of t; constrain long-only weights, regularize covariance if necessary, safe infeasible optimization fallback with logged event. Specify objective (max Sharpe/min variance/target return), estimation window and rebalancing.
- No benchmark may consume full-series realized moments including the test period.

## 5.5 Metrics
- Daily net returns and equity curve.
- Cumulative return: `V_end / V_start - 1`.
- Annualized volatility: std(daily return) * sqrt(252), with explicit ddof convention.
- Annualized Sharpe: mean(daily excess return) / std(daily excess return) * sqrt(252), or mathematically equivalent with consistently converted annual risk-free rate. Handle zero variance explicitly.
- Max drawdown: max of `(running_peak - equity) / running_peak`, preferably present drawdown as a negative percentage or positive magnitude consistently.
- Optional: CAGR, Calmar, Sortino, turnover, win rate only when appropriate, fee burden, exposure, run-to-run variance.
- Distinguish gross vs net returns; use consistent timezone, settlement and daily calendar.

## 5.6 Validation protocol
- 2015–2021 initial train; 2022–2023 for validation and rolling/expanding walk-forward development.
- 2024 **strict final holdout**: do not tune model or select strategy using its results.
- If retraining within 2024 is permitted by the finalized protocol, it must use only prior 2024 information and the rules must have been fixed in advance; otherwise run frozen model. Document exactly which.
- Freeze dataset snapshot, universe, timestamps, config and commit; block any experiment that violates temporal constraints.
- Compare four strategies under identical economic assumptions.
- Keep an experiment registry with reproducibility manifest.
- Avoid survivorship bias, reporting bias and multiple testing without disclosure.
- No claim of profitability without validated real output.

## 5.7 Validation for TRL 5
The academic guide demands TRL5, but that status must be substantiated by evidence: integrated components executing on representative historical financial data, market constraints, deterministic risk checks, reproducible experiment outputs, recorded integration and acceptance tests, failure-mode tests and operator walkthrough. Document relevance of the test environment vs real operating environment and remaining limitations. Do not call an isolated notebook training session sufficient proof on its own.

---

# 6. AGENTIC RUNTIME INSIDE THE PRODUCT (DISTINCT FROM CODEX SWARM)

**Do not confuse** (A) Codex's coding subagents developing the repository with (B) LLM agents that the resulting app may run through OpenRouter.

## 6.1 In-app agent roles
- `MarketAnalyst`: uses read-only datasets, technical indicators and available news where time-safe; supplies structured observations with evidence.
- `PortfolioStrategist`: exposes trained PPO/DDPG target allocations and classical baselines, not necessarily a conversational LLM.
- `Judge`: closed-set `approve/watch/reject`, confidence if meaningful, rationale/evidence, independent of sizing/execution.
- `RiskEngine`: deterministic hard limits, final arbiter; NOT an LLM.
- `SimulationExecutor`: paper-only orders, cost/slippage and timestamps; no real exchange connector.
- `ChiefReporter`: generates faithful summaries from database events, never invents values or acts as broker.

### Research inspiration: three user-provided posts
These are descriptions supplied by the user, **not audited/verified financial returns**:
1. Seven-seat memecoin desk: SEARCH → RISK → WHALE → JUDGE (Jev constrained classifier) → SNIPER (stages only, human approval) → EXIT → HEAD. The author claimed $500→$11,101.5 in five days. Keep the separation-of-duties, factual dossier, constrained questions, rejection audit and calibration checks. **Do not accept financial claims uncritically.**
2. Seven independent pre-flight risk gates for token authority, sell simulation, liquidity, concentration, creator history, price impact and freshness. Generalize the **fail-closed, cheapest-check-first, no missing-as-zero, final freshness check, reject audit** principles to traditional assets.
3. Four-bot Grok desk with Chief/Scanner/Analyst/Executor/Risk plus Copier, detailed prompts and theoretical SOL memecoin simulations. The post expressly states **"illustrative build, numbers simulated"**. Never present its $359→$20,589 claim as real verified gains. Learn from event logs, role boundaries, PAPER mode, telemetry, explicit manual enablement and adversarial failure testing.

These posts are **design research**, not an invitation to trade memecoins with real money or to copy financial thresholds tuned for unrelated markets.

## 6.2 OpenRouter adapter design
- Provider: **OpenRouter** (not OpenCode).
- API base: `https://openrouter.ai/api/v1`.
- Use server-side key `OPENROUTER_API_KEY` in gitignored `.env`; never share or log secrets.
- Model initially proposed: `nvidia/nemotron-3-ultra-550b-a55b:free`, **verify live availability, context and structured output support** before locking; fallback `openrouter/free` only for development smoke tests, not reproducible final research unless resolved model identity is captured.
- Model registry stores capability flags (structured responses, tool calling, context, rate availability), source and last check timestamp.
- Use JSON schema or Pydantic validation with bounded retries, timeouts and explicit error categories. A malformed or missing answer is rejection/no-action, not an approval.
- Rate limits for free variants as of Nov 2026, per OpenRouter's published page: 20 RPM and 50/day for unfunded free usage; terms can change. Failed calls can count, so use local mocks, caching and manual action triggering. See `https://openrouter.ai/collections/free-models` and `https://openrouter.ai/docs/api/reference/limits`.
- Log provider, exact model actually used, prompt template version, cost/token usage where reported, timestamp, decision and output validation errors, while protecting secrets/PII.
- Minimize market information forwarded to third-party LLMs; document service/privacy implications and avoid attaching private user accounts.
- Explicit environmental safety controls: `APP_TRADING_MODE=PAPER`, `ENABLE_LIVE_TRADING=false`. In Phase 4, do not implement a live-mode toggle.

Suggested `.env.example` values (NO real keys):
```dotenv
APP_ENV=development
APP_TRADING_MODE=PAPER
ENABLE_LIVE_TRADING=false
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
DATABASE_URL=postgresql+psycopg://portfolio:portfolio@localhost:5432/portfolio_ai_lab
LOG_LEVEL=INFO
```
Actual variables should match chosen libraries; do not ship insecure default passwords into production.

## 6.3 Data-only dossier example
```json
{
  "as_of": "2024-06-14T20:00:00Z",
  "data_status": "valid",
  "source_snapshot_id": "sha256:...",
  "portfolio_id": "research-universe-v1",
  "strategy": "PPO",
  "target_weights": {"AAPL":0.20,"MSFT":0.20,"JPM":0.10,"JNJ":0.10,"XOM":0.05,"PG":0.05,"KO":0.05,"WMT":0.05,"SPY":0.10,"GLD":0.10},
  "provenance": "date-filtered historical dataset",
  "missing_fields": []
}
```
All numbers above are merely illustrative; do not treat them as predicted/actual allocations. Required fields missing => `missing`, not guessed.

## 6.4 Independent risk gates for academic long-only portfolio
1. Data completeness and numeric integrity.
2. As-of freshness/temporal eligibility and provenance.
3. Expected asset universe and valid weight simplex.
4. Position concentration limit if configured.
5. Liquidity/volume capacity if modeled.
6. Expected turnover, slippage and transaction costs.
7. Portfolio-level volatility/drawdown/exposure bounds if configured.

Each gate emits `{name, pass, reason_code, observed, threshold, dataset_timestamp}`. **Missing critical input => fail closed.** Hard rules are in code, not prompt text. Validate again at simulated execution time; never trust a stale prior gate. Gate limits are research configuration choices, not automatically the memecoin thresholds from social media.

## 6.5 Agent verdict evaluation
- Fixed questions and permitted outcomes.
- `approve/watch/reject` state and evidence/probability where defensible.
- LLM confidence is NOT automatically calibrated probability; verify with prospective logs, Brier score / calibration if a well-defined event label exists, and sufficient samples.
- Confidence alone must not increase position size.
- Record rejected proposals, their later hypothetical outcomes under precommitted rules, and explicit reasons.
- Never ask the same model repeated identical questions just to obtain favorable output.

---

# 7. DESIGN SYSTEM: PREMIUM QUANT TERMINAL, NOT A GENERIC AI DASHBOARD

**User's eight inspiration sources (research their current contents if browser available; do not blindly copy or assume a license):**
1. https://www.fontinlogo.com/ — logotype/typography inspiration.
2. https://recent.design/?ref=godly — curated visual and product references.
3. https://motionsites.ai/ — motion-oriented interactive web references.
4. https://www.scrolltide.co/ — scroll effects / motion patterns, mainly marketing pages.
5. https://www.navbar.gallery/ — navigation and sidebar patterns.
6. https://styles.refero.design/ — DESIGN.md-driven visual style references.
7. https://iconly.design/ — icon identity inspiration.
8. https://scrollshaders.com/ — subtle shader/gradient effects, only where appropriate and licensed.

**Design direction:** Dark-first premium financial research terminal. Support accessible light theme. Deliberate, calm, data-first, advanced but not overwhelming. Avoid excessive glassmorphism, glowing AI clichés, pseudo-3D coin objects, rainbow gradients, oversized hero headings, janky animated charts, tables that cannot be read or fake financial numbers.

## 7.1 Brand tokens (proposed starting point; implement and refine)
- Display name `Portfolio AI Lab`, short logo `PAL` or geometric mark inspired by branching allocations and data. Create original logo/icon, do not borrow a trademark.
- Primary dark canvas `#0B1220` / `#101722`.
- Elevated surfaces `#152133` / `#1B2838`.
- Border `#2B3B50`.
- Primary text `#EDF4FA`; secondary `#A7B5C6`.
- Accent mint `#6BD9B0`; blue `#7EA9FF` for informational emphasis; amber `#E9BD74` for caution; red `#F17B82` for losses.
- Light mode near-white `#F4F6F9`, white cards, ink `#182435` and accessible corresponding accents.
- Type: Geist or Inter for UI, JetBrains Mono for codes, prices and tabular stats; verify licensing and font loading. Use font-family fallbacks.
- Grid 8px, responsive 12-column desktop, consistent spacing 4/8/12/16/24/32.
- Radii 8–14px for cards, restrained shadows and subtle 1px borders.
- Visible focus state, semantic labels, skeleton loading, empty state, error state, success state, responsive sidebar.
- Charts use exact numeric values and readable axes/legends; don't paint arbitrary visuals as real results.
- `prefers-reduced-motion` must disable nonessential animation.
- Performance: no heavy WebGL shader behind data tables. Scroll animations reserved for landing/onboarding and must degrade gracefully.

## 7.2 Key pages
- `/dashboard`: overview, experiment status, real equity & KPI cards.
- `/strategies`: strategy library, PPO, DDPG, Markowitz, equal-weight; compare settings and research notes.
- `/backtests`: create/select experiment, run status, equity curve, risk metrics, allocations, transactions and run manifest.
- `/agents`: Analyst/Judge desk, fact dossier, actions and verdicts, hard risk passes/fails.
- `/risk`: controls, rejected proposals, data integrity, risk thresholds and audit log.
- `/experiments`: reproducibility registry, models, datasets, seeds, configs and exports.
- `/settings`: provider health, privacy, local runtime options, about/simulation banner.

Navigation: compact left sidebar, top context bar, clear environment badge **SIMULATION / PAPER ONLY**, keyboard shortcuts where discoverable, mobile drawer without hiding critical controls.

## 7.3 Visual proof protocol
- Create `DESIGN.md` with exact tokens/component rules.
- Inspect and test at desktop and mobile widths, including 1440x900, 1280x800, 768 and 390px.
- Use actual browser/Playwright screenshots for visual QA if available; never say "looks perfect" without inspection.
- Contrast and readability of red/green status must not rely on color alone; include text sign, icon, label.
- Accessibility: semantic headings, alt text, keyboard navigation, focus order, color contrast, WCAG 2.2 AA target where feasible.
- Avoid copying specific site logos/screens; references are inspiration, not assets.

---

# 8. CODEX MULTI-AGENT SWARM: DEVELOPMENT ORCHESTRATION

## 8.1 Reality check: enable it where supported
There are multiple product surfaces (Codex app/CLI, Agents API, Responses API) with different control planes. This Markdown is **not** an API call and cannot by itself enable multiagent execution. Inspect what is actually available in this user's installed Codex app. For example, OpenAI's Agents API supports `multi_agent.enabled` and `max_concurrent_subagents` when creating sessions; the beta Responses API supports `multi_agent: {enabled: true, max_concurrent_subagents: 3}`. These are examples for those APIs, NOT verified entries for a local Codex `config.toml`.

Official multi-agent references:
- https://developers.openai.com/api/docs/guides/agents-api/multi-agent
- https://developers.openai.com/api/docs/guides/responses-multi-agent
- https://developers.openai.com/api/docs/guides/agents-api/configuration
- https://developers.openai.com/blog/run-long-horizon-tasks-with-codex
- https://developers.openai.com/cookbook/examples/codex/iterating-development-workflows-with-codex

**Default operational preference:** 3 concurrent specialized subagents + 1 orchestrator. Scale to 4–6 ONLY if supported and the tasks/files/dependencies are sufficiently independent. More agents is not automatically better; shared-file races, context overhead and integration failures rise with concurrency.

### Preferred operating modes (best first)
1. True native Codex delegated subagents when exposed by active UI/harness. Name each role, spawn with bounded prompts and read/write ownership, gather results, review merge.
2. If no native delegation: separate Codex tasks or threads each on **distinct Git worktrees/branches**, with orchestration by main thread and explicit integration reviews. Distinct environments may be required.
3. If neither is supported: sequential specialist-task mode, honestly describe the limitation; don't pretend there was a swarm.

## 8.2 Core engineering subagent roster
| Agent | Responsibility | Initial filesystem ownership | Acceptance |
|---|---|---|---|
| **ORCHESTRATOR / TL** | Plan, dependency graph, delegation, interfaces, integration, final tests | root orchestration docs, PR merging | all gates pass |
| **ENV/DEVOPS** | Tool versions, Git, CI, docker, lint, env templates | `.github/`, `scripts/`, infra files | setup from clean clone |
| **QUANT/DATA** | Provider, ingestion, cleaning, splits, provenance | `packages/market_data/` | data contracts and leakage tests |
| **RL/ENV** | Gymnasium MDP, PPO/DDPG trainers | `packages/portfolio_env/`, `packages/strategies/rl/` | deterministic environment tests, smoke training |
| **BACKTEST/RESEARCH** | Benchmarks, economics, metrics, walk-forward | `packages/backtesting/`, `packages/strategies/classical/` | hand-checkable results |
| **BACKEND** | FastAPI, DB, job orchestration | `apps/api/`, `workers/` | integration/API tests |
| **FRONTEND/DESIGN** | Next.js, UX/design, browser QA | `apps/web/`, `DESIGN.md` | responsive tested flows |
| **AI/AGENTS** | OpenRouter, analysis, JSON schema, provider mocks | `packages/ai_agents/` | deterministic/no-live tests |
| **SECURITY/QA REVIEWER** | Adversarial review, test coverage, injection/data leakage/secret scan | primarily read-only, targeted `tests/` by ownership | issue report + verification |
| **ACADEMIC/DOCS** | Requirements traceability, TRL evidence, runbook, demo storyboard | `docs/UNAD-*`, reports | every claim evidence-backed |

Roles are **logical** and can be reused across waves. Not all should run simultaneously.

## 8.3 Waves and concurrency
**Wave 0, read-only in parallel (3 agents):** Environment + tooling, quant/academic audit, UX/architecture/security review. Root synthesizes and sets ownership.

**Wave 1, independent scaffolding:**
- Agent A: quant fixture and equal-weight engine (isolated package).
- Agent B: frontend design-system primitives + static/fixture-aware shell (isolated `apps/web`).
- Agent C: backend route contracts + persistence wiring (isolated `apps/api`).
- Root: validates shared JSON/schema contract and orchestrates integration. No agents edit root lockfiles concurrently.

**Wave 2:** market data + benchmarks + quant environment with dependency sequence; independent packages may proceed in parallel only after shared contracts are frozen.

**Wave 3:** PPO training, DDPG trainer, backtesting/metrics verification with separate ownership. Train serially if compute limited.

**Wave 4:** LLM provider and Agent Desk, E2E/browser QA, academic report evidence in parallel.

**Wave 5:** hardening, security and regression reviews independently; root fixes and integrates.

## 8.4 Strict delegation protocol
Every subagent receives:
```text
Agent name:
Goal / bounded deliverable:
Inputs and dependencies:
Files/directories exclusively owned:
Files explicitly read-only:
Shared API/schema contract:
Tests to run:
Definition of done:
Expected report (changes, commands, evidence, risks):
Do not edit outside ownership. Do not merge yourself. No real trading.
```

Before any concurrent WRITE tasks, main agent publishes interface types and file ownership in `docs/AGENT-SWARM.md`. Agents must not modify shared root config, migration folders, API schema, generated clients, environment template or global lockfile concurrently. If conflicts are likely, root serializes the dependent steps.

**Git discipline:**
- Branch/worktree per independent implementation where supported (`feat/data-ingestion`, `feat/dashboard-shell`, `feat/api-foundation`, etc.).
- Never use `git reset --hard`, force-push, destructive clean or delete user changes without explicit human permission.
- Review diffs, dependencies and test evidence before merging.
- Define a stable shared contract then generate/validate clients, not parallel hand-written divergent JSON shapes.
- Subagent reports are not acceptance: orchestrator independently verifies build/tests.

## 8.5 Quality gates, required for every feature
1. Scope and contract accepted.
2. Typed code and migration where needed.
3. Unit test for main behavior and failure case.
4. Lint/typecheck pass.
5. API integration or E2E test if behavior crosses boundaries.
6. Source data/time leakage checks if financial.
7. Security check for keys, authorization and untrusted LLM output.
8. Browser screenshot / accessibility review if visual.
9. Docs/status updated, no unsupported claims.
10. Merge/commit only after review.

## 8.6 Agent conflict and failure policy
- If agent cannot access tool/service, report blocker and run a valid mock/unit path; never fabricate results.
- If same file modified in two branches, root reviews and reconciles. Do not auto-overwrite.
- If external data provider unavailable, use labeled historical fixture and prove algorithm correctness; don't claim live price results.
- If test fails, fix/revert scoped change, don't disable the test merely to pass CI.
- If an agent hallucinates an API, verify vendor docs or actual returned schema before writing adapters.
- Don't ask more agents to resolve every small bug; parallelization must reduce dependencies, not multiply them.

---

# 9. CODEX MODELS, TOOLS, PLUGINS AND WORKFLOW

## 9.1 Development model policy
- First choice: **GPT-6.1 Sol** in Codex if exposed in the user's interface; use High reasoning for architecture and quant correctness, Medium for bounded implementation and tests.
- Smaller/cheaper available model for low-risk edits and routine issues (e.g. GPT-6 Luna) if surfaced by the app.
- Do not claim that a specific model/effort tier is selectable without inspecting the Codex build/account.
- Multi-agent support differs between Codex app, Agents API and Responses API. Verify actual surface; don't paste unverified `config.toml` entries.
- OpenRouter API models are for runtime features INSIDE Portfolio AI Lab, not automatically the Codex development model.

## 9.2 Codex functions to make use of
- Repo-aware file editing and test execution.
- Planning/architecture tasks before changing cross-cutting code.
- Code review of diffs and security regressions.
- Separate Git worktrees and parallel tasks where available.
- Skills for frontend design/testing, Python test workflows, security review and technical docs.
- Browser/Playwright to inspect live UI and execute E2E.
- GitHub plugin for repository/issue/PR actions if connected and authorized.
- Optional Figma tooling if project later calls for editable Figma design assets.
- Scheduled automations only after core checks are reliable; do not create recurring jobs by default.

**Plugin policy:** Inspect installed tools and capability descriptions first. Do not claim an uninstalled plugin is active or install untrusted tools without owner approval. Prefer small, well-understood integrations.

## 9.3 Local environment audit (Windows)
Run and record output, no guesses:
```powershell
pwd
git --version
git status --short --branch
node --version
npm --version
pnpm --version
python --version
py -0p
uv --version
docker --version
docker compose version
```
Some commands may fail if tools aren't installed. Report each absence. Do not blindly run `git init` if already initialized. Node LTS, Python 3.11/3.12, pnpm, uv and Docker Compose are preferred; if WSL necessary for a specific component, justify it.

## 9.4 Repo hygiene
`.gitignore` should include `.env*` with explicit exception for `.env.example`, `.venv`, `node_modules`, `.next`, `__pycache__`, checkpoints/models, downloads, data caches, temporary reports and provider tokens. Keep `README` and reproducible sample configs committed.

## 9.5 Development-loop guideline
Follow: **Plan → Inspect → Implement → Run tests → Observe → Repair → Review → Update docs → Repeat.** Avoid giant one-shot prompts beyond the bootstrap, and avoid verbose redundant agent instructions in each file.

---

# 10. TESTING, PRIVACY, SECURITY AND OPERATIONAL RELIABILITY

## 10.1 Test layers
- **Unit tests:** input contracts, missing data, weights, simplex projection, portfolio arithmetic, returns/fees, exact known equity/drawdown/Sharpe cases, risk gates, provider schema.
- **Property-based tests:** invariants over random valid allocations and price paths; deterministic seeds for reproduction.
- **Integration:** ingestion→cache→dataset snapshot; API→job→quant→database→result; strategy→risk→simulated executor; provider mock→parse→audit log.
- **Walk-forward tests:** dataset splits don't overlap, preprocessing fit only on train, rolling windows only use past information, 2024 not used for tuning.
- **Failure-mode tests:** API timeout, empty book, missing data, non-finite weights, negative allocations, double fills, stale approvals, provider shape changes, zero volatility, optimizer failure.
- **E2E/browser:** launch run, visualize result, inspect rejected proposal, handle API error, responsive mobile, keyboard navigation.
- **Reproducibility:** fresh clone and seed/config pinned; exact run manifest can reproduce fixture results.

## 10.2 Security principles
- PAPER ONLY. No keys for exchanges/brokers in Phase-4 app.
- OpenRouter key stays on server only.
- Treat LLM outputs, user input, imported datasets and external APIs as untrusted.
- No arbitrary code evaluation from LLM output.
- Safe request validation, rate limiting, least-privilege filesystem and GitHub credentials.
- No SSRF from free-form user URLs, no direct shell tool access for in-app LLM analysts.
- Redact tokens/secrets from logs and UI.
- Clear `SIMULATED / NO REAL MONEY` disclaimer; no performance guarantees or trading advice claims.
- Model outputs cannot sign, send, approve or upsize financial orders. Risk gates always enforced in code.
- Optional sign-in only if truly needed by academic MVP; avoid collecting personal financial info.

## 10.3 Telemetry/audit
- Request IDs, run IDs, structured log events, durations, retry counts, error codes.
- Separate run status and agent verdict logs.
- Distinguish simulated fill and observed historical quote.
- Do not emit secret payloads or personal identifying data.
- Daily/weekly audit reports should be generated from records, never memory or model storytelling.

---

# 11. PHASED BUILD PLAN, DEFINITION OF DONE AND DELIVERY ORDER

Prioritize earliest meaningful proof in the face of the academic deadline.

## Stage 0 — Repo and swarm bootstrap (immediate)
**Outcome:** Diagnosed Windows environment, Git safe baseline, root `AGENTS.md`, master spec saved in repository, initial `DESIGN.md`, project README, docs/PLAN+STATUS+DECISIONS, `.gitignore`, `.env.example`, architecture ADR, initial testing harness, supported swarm mechanism verified.
**DoD:** Correct repo, tool outputs recorded, no leaked credentials, actual agent delegation mode known, no destructive actions, clear stage 1 tasks.

## Stage 1 — End-to-end minimal platform
- Next.js shell + sidebar + dark/light.
- FastAPI with health and experiment endpoints.
- DB/local persistence.
- Fixture/real-provenance equal-weight backtest.
- Actual computed equity and metrics in UI.
**DoD:** Browser demonstrates an entire valid run; unit/integration/E2E tests pass; UI not mocked as live data.

## Stage 2 — Source data and quant core
- Provider adapter, historical snapshot (2015–2024), data-quality report.
- MDP state, action, costs and accounting.
- Markowitz with rolling estimates, equal-weight comparable.
- Risk gates and detailed audit.
**DoD:** exact calculations tested, research data provenance documented, reproducible baseline.

## Stage 3 — PPO / DDPG and evaluation
- PPO and DDPG smoke-train and artifacts.
- Training/validation/test segregation and walk-forward.
- Metric comparisons and multiple seed support as possible.
- Final 2024 holdout report only after protocol frozen.
**DoD:** runnable models, actual reproducible evidence, realistic limitations disclosed.

## Stage 4 — Agent Desk on OpenRouter
- Provider with capability checks, JSON validation, error handling and mocks.
- Analyst/Judge UI, historical fact-only dossier, risk veto, event logs.
**DoD:** No dependence on a paid model; no uncontrolled calls; fail-closed and auditable.

## Stage 5 — Final frontend polish, QA and UNAD artifacts
- Visual walkthrough / responsive QA and accessible UI.
- Complete test matrix, clean setup/runbook, GitHub repo with tutor read access.
- Update Phase-3 master report using actual observations, documented Scrum and integrated design.
- TRL-5 evidence pack with relevant-environment demonstration.
- <=10-minute real video showing all three participants on camera (human team records it; Codex can prepare outline/storyboard and demo script).
**DoD:** all formal requirements linked to evidence, reproducible project, no unsupported claims.

## Stage 6 — Post-deadline research extensions
- LLM hybrid strategies with rigorous isolation and date-safe evaluation.
- Paper trading data feed; paper-only crypto adapter and short simulator behind feature flags.
- Performance/profiling, advanced simulation and eventual independent audit.

### Academic 13-day tactical schedule (Nov 9–22)
- Nov 9–11: audit, scaffolding, data pipeline, environment, fixtures.
- Nov 12–15: baselines, PPO/DDPG, executable vertical slice.
- Nov 16–18: backtesting, tests, integrated validation evidence.
- Nov 19–20: final docs, UX QA, GitHub, video recording with real participants.
- Nov 21–22: dry run, link verification, forum and submission.
This is an aspirational accelerated plan; honestly report what actually gets built and do not fake TRL evidence if scope cannot be completed.

---

# 12. ACADEMIC REPORT / EVIDENCE COLLECTION

Extend the 40-page Phase-3 master rather than rewriting it from nothing. The structure includes cover, Spanish resumen and English abstract, table of contents, introduction, problem, objectives, rationale, delimitations, theoretical/conceptual/juridical/technological frameworks, research methodology (sample and population, measurement instrument/data collection, research analysis), technology development methodology, requirements, preliminary prototype design, six-month schedule, resources, expected outputs, references and collaborative annexes.

Phase-4 report should add:
- Tutor feedback received and **actual** corrections (feedback pending; request or mark unknown, do not invent).
- Final architecture and implementation decisions.
- Product backlog, sprint objective, deliverables, reviews and retrospectives, with real contributor evidence.
- Implementation by module, screenshots and code references.
- Test plan, test outcomes and failures addressed.
- Data provenance, experiment parameters, walk-forward evaluation, benchmark comparisons with actual outputs.
- TRL-5 integrated validation case and relevance justification.
- Risk/security control evidence.
- Results, limitations, conclusions and future research.
- Annex links to GitHub repository and demonstration video.
- Evidence all three members participated; never generate deceptive screenshots/messages or attribute work falsely.

Maintain `docs/UNAD-PHASE4-EVIDENCE.md` as traceability table with columns: `requirement`, `artifact or command`, `test/log/screenshot`, `owner`, `status`, `source`, `verified-at`. Use screenshots captured from actual application, not illustration.

Required GitHub link and <=10 minute video should be put into final master document. GitHub must have readable source and tutor access. Only one submission document per group.

---

# 13. FIRST SUBAGENT TASKS TO DELEGATE (READY TO USE)

### Agent A: System and permissions investigator (READ-ONLY)
> Examine Windows toolchain versions, installed commands, Git worktree state, Codex available capabilities, permissions and feasible testing/CI flow. Report installed/missing and recommended setup commands. Do not install, delete, initialize or edit anything. Owner: environment inspection only.

### Agent B: Quant + academic methodology investigator (READ-ONLY)
> Use this master document as the grounded source. Audit the proposed 10 tickers, 2015–2024 splits, PPO/DDPG/Markowitz comparability, MDP and lookahead hazards, 12 RF / 5 RNF, and Phase 4 TRL-5 evidence. Produce a quant architecture and verification checklist. Do not claim source PDFs exist locally unless verified.

### Agent C: UI/UX + architecture researcher (READ-ONLY)
> Inspect available visual references from the eight supplied websites if tools permit. Propose original brand tokens, information architecture and component system for a polished dark-first financial terminal. Also review backend/frontend separation and UI data contracts; report inaccessible references. Do not write code until interface ownership is agreed.

### Root orchestrator synthesis
> Consolidate the three independent reports, resolve disagreements with explicit tradeoffs, establish file ownership and make an ordered Stage-0+Stage-1 plan. Then delegate nonoverlapping WRITE tasks via native subagents/worktrees if actually supported; test/integrate every returned change. User wants maximal productive agentic development, not superficial agent personas.

---

# 14. OWNER'S INTENDED INITIAL CODING SESSION

**User instruction to Codex on uploading this MD:**

> Lee íntegramente `PORTFOLIO_AI_LAB_CODEX_MASTER_CONTEXT.md`. Trátalo como especificación principal del proyecto. Quiero un desarrollo auténticamente agéntico con subagentes paralelos cuando Codex lo permita, usando preferentemente GPT-6.1 Sol con esfuerzo High para arquitectura. Primero audita mi carpeta y entorno Windows, confirma de forma verificable cómo funcionarán los agentes concurrentes, crea `AGENTS.md`, `DESIGN.md` y los documentos de planificación, y arranca la primera etapa segura. Usa tareas independientes y worktrees para evitar conflictos, ejecuta pruebas y no inventes resultados. Respeta el alcance UNAD, la fecha de entrega y el modo PAPER ONLY. Quiero avances concretos demostrables, no solo explicaciones ni código sin probar.

**Don't block waiting for every trivial decision.** Choose sensible defaults, document them, and proceed with safe reversible actions according to tool permissions. Seek explicit authorization for new expenditures, real-money functions, privileged account actions, public uploads, global changes and destructive edits.

---

# 15. REFERENCES AND VERIFICATION LINKS

## Official engineering / agent platform docs
- Codex and iterative AGENTS.md workflows: https://developers.openai.com/cookbook/examples/codex/iterating-development-workflows-with-codex
- Codex long-horizon loop: https://developers.openai.com/blog/run-long-horizon-tasks-with-codex
- OpenAI Agents API multi-agent: https://developers.openai.com/api/docs/guides/agents-api/multi-agent
- OpenAI Responses multi-agent beta: https://developers.openai.com/api/docs/guides/responses-multi-agent
- OpenAI model selection: https://developers.openai.com/api/docs/guides/model-selection
- Agent Skills: https://developers.openai.com/api/docs/guides/tools-skills
- OpenRouter free-model directory: https://openrouter.ai/collections/free-models
- OpenRouter API: https://openrouter.ai/docs/quickstart

## Related research and open source
- FinRL: https://github.com/AI4Finance-Foundation/FinRL
- FinRL-Trading / FinRL-X: https://github.com/AI4Finance-Foundation/FinRL-Trading
- TradingAgents: https://github.com/TauricResearch/TradingAgents
- Gymnasium: https://gymnasium.farama.org/
- Stable-Baselines3: https://stable-baselines3.readthedocs.io/
- Lightweight Charts: https://tradingview.github.io/lightweight-charts/

## Design references (inspiration, review licenses)
- https://www.fontinlogo.com/
- https://recent.design/?ref=godly
- https://motionsites.ai/
- https://www.scrolltide.co/
- https://www.navbar.gallery/
- https://styles.refero.design/
- https://iconly.design/
- https://scrollshaders.com/

---

# FINAL EXECUTION CONTRACT

You are not just generating code: you are orchestrating a professional, evidence-driven software engineering team in a real working repository. Use the actual connected tools, delegate well-scoped independent investigations and implementation tasks, and integrate through explicit contracts and tests. Optimize for **functional delivery, correctness, security, visual polish and academic traceability**. Always distinguish complete, partial, blocked and not-started work. Never manufacture trading performance or claim that a subagent/model/tool ran unless it genuinely did.

**Immediate priority:** Verify multiagent capability, protect the local workspace, scaffold the system safely, then ship a passing end-to-end backtest visualization. Build the remainder incrementally and truthfully.
