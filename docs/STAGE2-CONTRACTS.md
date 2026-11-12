# Stage 2 shared contract and ownership

2026-11-10. Native agents: stage2_data, stage2_quant, stage2_simulation.
No worktree base commit exists. Preserve Stage1 files/tests; exclusive writes:

| Owner | Files |
|---|---|
| Data | packages/market_data/**, tests/data/** |
| Quant | packages/portfolio_research/**, tests/research/** |
| Simulation | packages/portfolio_env/**, tests/environment/** |
| Root | portfolio_core, root configs/dependencies, docs/scripts, API/web/contracts/E2E |

Agents may read all project files. Only root installs/updates shared locks.
Data runtime outputs are allowed only in .runtime/data-probes; root executes
the final ingestion into .runtime/datasets. Never commit downloaded data.

## Shared Python API (portfolio_core)

`PricePanel(dates:tuple[str,...], assets:tuple[str,...], prices:NDArray[float64],
metadata:dict[str,Any])` validates and copies a positive finite rectangular
adjusted-close matrix, sorted unique dates, unique assets; copied prices read-only.
Metadata uses existing Dataset fields, kind HISTORICAL, stable dataset ID/hash.

`rebalance_step(value:float, drift_weights:NDArray|None, target:NDArray,
price_relatives:NDArray, transaction_cost_bps:float)->StepResult`.
StepResult fields: equity, net_return, cost, turnover, traded_notional, weights.
weights = next-close drift; None initially means cash. Exact fee solves
F=c*sum(abs(target*(value-F)-value*drift)); initial F=c*V/(1+c).
No terminal liquidation. Fee is charged once; turnover=traded_notional/value.
`validate_weights(weights,count)->NDArray[float64]`.
`project_simplex(action)->NDArray[float64]` (Euclidean simplex projection).
`financial_metrics(values,annual_rf=0,total_costs=0)->dict[str,float|None]`.
Sample std ddof1, factor252, annual effective rf conversion, positive drawdown.

## Data interface

`market_data.UNIVERSE` = tuple of the ten academic tickers in master order.
`download_snapshot(root:Path)->dict` downloads2015-01-01 through2024-12-31
(provider end exclusive2025-01-01), validates XNYS coverage and writes immutable
Parquet, original provider payload and manifest/quality report. No fabrication,
fill or silent dropping. Source limitations explicit; downloaded data ignored.
`list_snapshots(root:Path)->list[dict]` returns Dataset metadata, stable IDs
matching `historical-[a-f0-9]{12,64}`. `load_snapshot(root:Path,id:str)->PricePanel`
verifies file/hash/provenance and rejects paths outside root or malformed IDs.
Metadata existing fields plus optional provenance, quality_report, splits.
Dataset sha256 is canonical Parquet content hash; manifest also hashes raw files.
Close and adjusted close/actions are retained. Dividends/splits not double-added
to adjusted returns; report that vendor adjusted history is retrospectively
revised, not point-in-time vintage data. XNYS train2015-21/validation2022-23/
final_test2024 partitions nonempty/disjoint. Original PDFs absent not blocking.
CLI `python -m market_data --root ...` produces JSON summary or explicit failure.

## Quant interface

`run_historical_backtest(panel:PricePanel, config:dict)->Result dict` with
existing result keys/metrics/equity/allocations/audit/manifest. strategy
equal_weight|markowitz; config old request fields plus split=train|validation,
lookback:int(default60), risk_aversion:float(default5). max_weight1 (no added
concentration assumption); rolling daily estimates, covariance regularized.
Markowitz minimizes annualized variance penalty minus annualized mean;
simplex long-only constraints, numerical checks and audited EW fallback.

At execution close t use prices only through t-1: last W returns end t-1;
warmup requires t>=W+1. Fee then P[t+1]/P[t]. This deliberately lags signals.
Equal-weight uses identical start/warmup/evaluation interval and exact fees.
Evaluation range is chosen by split (train2015-21, validation2022-23). History
before validation is warmup only. No evaluation or parameter tuning on2024.
Manifest records execution/information dates, solver options/fallback counts,
dataset hash, full config, evaluation dates and metric conventions.

## Simulation interface

`PortfolioEnv(panel, lookback=20, initial_capital=10000,
transaction_cost_bps=10,reward_mode='log_return'|'simple_return',
risk_penalty=0.0,max_episode_steps=None)` extends Gymnasium Env.
Box action[-1,1]^N, Euclidean projection to nonnegative sum1. Invalid shape,
nonfinite or out-of-bounds action rejected (not clipped silently).
Obs flattened last lookback log returns through t-1 plus portfolio weights
known at t-1 (lagged post-trade target, initially zeros for cash). Actual drift
at execution t stays internal: exposing it would reveal P[t]. Reward net return
or log net growth minus configured lagged variance penalty, never fees twice.
reset deterministic; correct terminated/truncated; post-terminal step rejects.
Validate compatibility with actual Gymnasium and SB3 check_env; no training yet.

## Root integration and holdout

API extends Dataset.kind to FIXTURE|HISTORICAL and request strategy to
equal_weight|markowitz. Defaults and old persisted fixture jobs remain readable.
New fields have defaults; legacy fixture dispatch strips historical-only fields.
Dataset registry contains only real ingested snapshots; synthetic test doubles
stay in temp test roots. API/UI do not offer final_test2024, to preserve holdout.
UI labels data kind, source, hash, dates/splits and accounting version explicitly.
Original fixture engine remains unchanged to preserve Stage1 reproducibility.
Normal application runtime exposes only HISTORICAL data/results. The dedicated
ENABLE_TEST_FIXTURES flag defaults false and is enabled only by automated test
harnesses; old fixture unit tests and stored evidence remain preserved.
