# Test matrix

| Scope | Required evidence | Current |
|---|---|---|
| Legacy fixture | hand calculation, costs, finite data, prefixes, metrics | 51 pytest cases pass, preserved |
| API | validation, jobs, historical dispatch, persistence, restart, shutdown | 50 pytest cases pass |
| Shared accounting | exact fee/holdings identity, metrics, immutable panel | 15 pytest cases pass |
| Data | calendar/coverage, corporate fields, Parquet, hashes, failures | 41 pytest cases pass |
| Historical research | Markowitz/EW, fallback, window/holdout causality | 53 pytest cases pass |
| Gym environment | finance, reward, seeds, termination, Gym/SB3 checkers | 36 pytest cases pass |
| Contract | exported OpenAPI, generated TS, typecheck | generated + checked |
| Web | lint, typecheck, production build | all pass |
| E2E baseline | fixture, persistence, error recovery, viewports | 8 Chromium cases pass |
| E2E historical | actual Markowitz desktop + EW mobile, persisted values | 2 Chromium cases pass; real dataset required |
| Visual | desktop/tablet/mobile, dark/light, overflow/focus | screenshots reviewed; viewport/keyboard tests pass |
| Actual data | real pipeline, two reproducible baselines, training-only Gym | passed; evidence/stage2/ |
| RL trainers | PPO/DDPG learning, checkpoint and resume, resource guards | 16 pytest cases including shared RL tests |
| RL evaluation | temporal isolation, accounting, aligned metrics and selection | 70 pytest cases |
| Training API | queue, startup failure, cancellation, restart and input boundaries | 28 pytest cases |
| E2E training | historical PPO/DDPG, comparison, saved-model replay, active cancellation | 2 Chromium cases passed at desktop and mobile widths |
| API artifact resume | same verified checkpoint on a new job, restored optimizer and replay buffer | both historical smoke jobs resumed from 256 to 512 steps |
| RL historical study | four-strategy comparison, trained walk-forward and 3 seeds per algorithm | 14 completed study jobs, 2 initial smoke jobs |
| Historical reproducibility | independent reruns with same parameters and seed | tensors, normalizer, actions, equity and metrics matched for both smoke jobs |
| Agent Desk provider | exact route, strict JSON, zero-price preflight, quota and timeout | public capability check and authenticated Analyst/Judge inference passed on the fixed free Dots route |
| Agent Desk workflow and risk | dated facts, four strategies, closed Judge verdict and deterministic veto | 72 cases passed; four real-history API runs with labeled mock inference |
| Agent Desk API | queue/restart, append-only audit, provider errors and 2024 rejection | 13 cases passed |
| Agent Desk E2E | approvals, risk veto and reload at desktop/tablet/mobile | one Chromium case passed across three widths using real history and explicit mock |

Commands and limitations: [validation-report.md](validation-report.md).
CI workflow is configured but has not run on GitHub; local success is not a
claim of Linux/Node24 execution. Accessibility checks are targeted, not a full
WCAG audit. Offline UI test injects502; other E2E results come from the real API.
