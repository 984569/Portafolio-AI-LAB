# Historical data and temporal protocol — Stage 2

Ten instruments: AAPL/MSFT/JPM/JNJ/XOM/PG/KO/WMT/SPY/GLD. Source: public Yahoo
Finance chart HTTPS. Exact JSON, parameters, HTTP status, UTC fetch times and
SHA256 are retained locally. No credentials, paid feed, endpoint rotation on429
or synthetic fallback. yfinance was researched and installed, but this snapshot's
actual adapter is direct chart HTTP.

The real snapshot contains2516 aligned XNYS sessions,2015-01-02 to2024-12-31:

| Partition | Dates | Observations | Use |
|---|---|---|---|
| train | 2015-01-02–2021-12-31 | 1763 | development; environment compatibility rollout |
| validation | 2022-01-03–2023-12-29 | 501 | benchmark evaluation |
| final_test | 2024-01-02–2024-12-31 | 252 | ingestion/quality only; evaluation locked |

Reject missing/extra/duplicate/unsorted sessions, incomplete symbols/columns,
nonfinite/nonpositive prices, invalid OHLC, negative volume/actions, malformed
splits and adjustment factors. No imputation, forward fill or dropping sessions.
Explicit XNYS calendar bounds include holidays; this is a common-calendar proxy
for Nasdaq too. Holiday starts are sliced against actual sessions.

prices.parquet contains aligned adjusted close. provider-bars.parquet retains
provider OHLC/Close/AdjClose/volume/dividends/splits. raw/ holds exact JSON.
quality-report.json and manifest.json bind all hashes, source and package versions.
Dataset ID is historical-<Parquet SHA256>. Existing snapshots are verified, never
overwritten. A resumed pipeline reuses verified original responses; choose a new
local root to refresh revised provider history without replacing evidence.

Corporate actions: use adjusted-price ratios; do not add dividends/splits again.
Provider Close may already be split-adjusted. Numeric/action/factor consistency
is checked, but action completeness is not independently reconciled. Missing
event entries represent the provider's reported lack of events, not independent
verification of corporate history.

Retrospective adjusted prices are research units, not executable quotes or a
point-in-time vintage feed. Vendor revisions and the fixed current universe
create disclosed point-in-time and survivorship limitations. Downloaded data
stay ignored by Git; public availability does not grant redistribution rights.
See [provider documentation](https://ranaroussi.github.io/yfinance/) and its
linked Yahoo terms before external data redistribution.

Temporal rule: at execution close t estimate on W returns ending at t-1;
never use P[t] for target selection. Apply exact fees, then P[t+1]/P[t]. EW and
Markowitz share warmup/evaluation dates. Validation starts with cash at the first
2022 close:501 closes produce500 intervals. Earlier history is warmup only.
Final2024 is excluded from equity, decisions and parameter selection.

Gym observations use lagged log returns and target weights known at t-1;
current drift stays internal. No scaler is fit on full history. Future-price
perturbation cannot change earlier or same-execution targets. Tests establish
algorithmic index causality, not historical availability of the vendor's exact
retrospectively adjusted data vintage.

The synthetic fixture remains a separate software/test mode with fictional
symbols. It is not historical data and cannot establish profitability.
