# Portfolio AI Lab — working rules

Read `PORTFOLIO_AI_LAB_CODEX_MASTER_CONTEXT.md` for the specification, then
`docs/STATUS.md`, `docs/architecture.md` and `docs/AGENT-SWARM.md` before work.

- Communicate with the owner in Spanish. Keep technical identifiers in English.
- PAPER ONLY. No broker connections, live-mode switch, credentials, paid calls,
  global configuration changes or publication without separate authorization.
- Preserve user files and uncommitted work. Never use destructive Git commands.
- Real evidence only: label synthetic fixtures everywhere; never invent returns,
  tests, training, academic participation, TRL status or screenshots.
- Preserve RF1–RF12 and RNF1–RNF5. Train 2015–2021, validate 2022–2023;
  2024 is a locked final holdout, never a tuning dataset.
- API owns validation; quant owns canonical accounting; UI renders persisted
  results. Future LLM outputs cannot bypass deterministic risk gates.
- Use bounded native subagents when useful. Record exclusive ownership and
  contracts before parallel writes. Root owns shared configuration/lockfiles.
- Install dependencies locally only. Use Python 3.11 explicitly and pnpm.
- Validate financial arithmetic, temporal eligibility and boundary failures.
  Run pytest, Ruff, TypeScript, lint, production build and relevant browser E2E.
- Update status, decisions and evidence with observed results and limitations.
  Do not claim the academic MVP is finished after the fixture vertical slice.
