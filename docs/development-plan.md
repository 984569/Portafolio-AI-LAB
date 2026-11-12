# Development plan

As-of: 2026-11-11 (America/Bogota). Academic deadline from supplied context:
2026-11-22. Six-month research schedule remains separate.

| Stage | Dependencies | Acceptance |
|---|---|---|
| 0: bootstrap | existing folder, local tools | audit, permanent rules, design, architecture, ownership, setup, test harness |
| 1: vertical slice | approved contracts, Stage 0 | browser→API→worker→quant→SQLite→browser; fixture label; tests, typecheck, lint, build |
| 2: research data/core | verified provider terms and data | RF1–4, Markowitz, exact accounting, quality report, split/lag checks |
| 3: RL/evaluation | stable MDP/data protocol | PPO/DDPG artifacts, pre-2022 walk-forward selection, 2022–2023 validation, four-strategy comparison, API/dashboard, 2024 locked |
| 4: Agent Desk | deterministic gates and audit | fixed free OpenRouter endpoint verified by authenticated smoke, mock coverage, constrained decisions and auditable PAPER dashboard |
| 5: academic delivery | representative integrated validation | traceability, actual report/video evidence, human participation, reviewed publication |

See [verified status](STATUS.md) and the [validation report](validation-report.md)
for executed checks and acceptance evidence. Stage 3 uses the verified Stage 2
snapshot, benchmarks, exact accounting and Gym environment.

Stage 1 implementation batches: independent quant arithmetic/fixture, API
models/persistence/worker, and web shell/form/result presentation. Root installs
dependencies, generates shared contracts, integrates and verifies each branch
of behavior. Do not install the entire ML stack before the baseline works.

The final 2024 evaluation requires approval of its protocol. The original
academic PDFs and tutor feedback remain external dependencies for academic
delivery. Never backfill Scrum or contributor evidence.
