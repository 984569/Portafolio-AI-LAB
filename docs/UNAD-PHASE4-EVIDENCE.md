# UNAD Phase 4 evidence registry

Source: supplied master context, §§2/12. Original PDFs absent; transcription
not independently compared. No human contribution or TRL5 claim is inferred.

| requirement | artifact or command | test/log/screenshot | owner | status | source | verified-at |
|---|---|---|---|---|---|---|
| RF1 | market_data + real Parquet snapshot | evidence/stage2/pipeline-progress.json | Codex Data | verified10/10,2516sessions; vendor limitations disclosed | master §2 | 2026-11-10 |
| RF2 | validation, simple/log returns | tests/data, research, environment | Codex agents | partial; additional technical indicators pending | master §2 | 2026-11-10 |
| RF3 | disjoint chronological partitions | data-quality.json + splits + API holdout tests | Codex Data/Root | verified train1763/validation501/final252 | master §2 | 2026-11-10 |
| RF4 | Gymnasium + exact proportional costs | environment36tests;1741 real-data steps | Codex Simulation/Root | environment implemented and compatible; no training claim | master §2 | 2026-11-10 |
| RF5 | PPO/DDPG training | evidence/stage3/historical-study.json | Codex PPO/DDPG/Root | verified historical models and usable checkpoints | master §2 | 2026-11-11 |
| RF6 | walk-forward | experiments/stage3-protocol.json and historical-study.json | Codex Evaluation/Root | two pre-2022 folds per candidate and independent 2022–2023 validation | master §2 | 2026-11-11 |
| RF7 | locked final holdout | API and evaluation temporal tests | Codex agents | protected; final evaluation awaits protocol approval | master §2 | 2026-11-11 |
| RF8 | historical net metrics | core tests + historical-validation.json | Codex Quant/Root | verified on real validation data | master §2 | 2026-11-10 |
| RF9 | EW + rolling Markowitz | research53tests; real repeated replays | Codex Quant/Root | both verified; lagged long-only, negative result retained | master §2 | 2026-11-10 |
| RF10 | four-strategy common protocol | evidence/stage3/historical-study.json | Codex Evaluation/Root | verified on 2022–2023 under common execution assumptions | master §2 | 2026-11-11 |
| RF11 | typed requests, saved configs and versioned profiles | stage2-baseline.json, stage3-protocol.json and training manifests | Codex Root | baseline and RL configurations verified | master §2 | 2026-11-11 |
| RF12 | actual historical curves, metrics, allocations and comparisons | stage2 and stage3 browser evidence | Codex Root/Evaluation | historical dashboard and four-strategy comparison verified | master §2 | 2026-11-11 |
| RNF1 | locks, manifests and repeatable models | evidence/stage3/reproducibility.json | Codex Root/DDPG | two exact historical smoke reruns on the same CPU environment; no commit yet | master §2 | 2026-11-11 |
| RNF2 | strict t-1 estimates, lagged state,2024 isolation | research/env future perturbation tests | Codex Quant/Simulation | algorithmic causality verified; retrospective vendor-vintage limitation | master §2 | 2026-11-10 |
| RNF3 | quant/API/web separation | integration/E2E | Codex agents | partial foundation implemented | master §2 | 2026-11-09 |
| RNF4 | code/docs/CLI | RUNBOOK.md | Codex agents | partial; execution notebook pending | master §2 | 2026-11-09 |
| RNF5 | Colab feasibility | none | unassigned | not verified | master §2 | 2026-11-09 |
| GitHub/video/report/TRL5 | real team integration evidence | none | human team | not started | master §§2/12 | 2026-11-09 |
