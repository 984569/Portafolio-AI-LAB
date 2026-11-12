# Stage3 research contract — 2026-11-10

Four responsibilities with four total slots: PPO, DDPG, Evaluation subagents
concurrent with Root/MLOps; a fourth named QA subagent follows when a slot frees.
No HEAD commit/worktree base; exclusive ownership instead:

| Owner | Exclusive writes |
|---|---|
| PPO | packages/portfolio_rl/ppo.py, tests/rl/test_ppo.py |
| DDPG | packages/portfolio_rl/ddpg.py, tests/rl/test_ddpg.py |
| Evaluation | packages/portfolio_evaluation/**, tests/evaluation/** |
| Root | portfolio_rl/config.py/common.py/__init__.py, API/web/jobs, scripts/docs/locks |

Existing Env/core/baselines remain unchanged unless a demonstrated regression
requires a scoped reviewed repair. No2024 fitting/evaluation/selection, no LLM,
no live trading. Model files are ignored local artifacts, never uploaded/published.

## Root shared training interfaces

portfolio_rl.config exports TrainingConfig, PPOSettings, DDPGSettings (Pydantic).
TrainingConfig: name, algorithm=ppo|ddpg, dataset_id, seed42,
total_timesteps1024, lookback60, initial_capital10000, transaction_cost_bps10,
risk_free_rate0, reward_mode=log_return|simple_return, risk_penalty0,
normalize_observations=True, net_arch=[64,64], checkpoint_frequency1024,
max_seconds600, max_memory_mb2048, training_end='2021-12-31',
ppo:PPOSettings, ddpg:DDPGSettings. No training_end after2021. CPU/threads1.

PPOSettings: learning_rate3e-4,n_steps256,batch_size64,n_epochs5,gamma.99,
gae_lambda.95,clip_range.2,ent_coef0,vf_coef.5,max_grad_norm.5.
DDPGSettings: learning_rate1e-3,buffer_size20000,batch_size64,gamma.99,
tau.005,train_freq1,gradient_steps1,learning_starts256,noise_sigma.1.
PPO budgets must be divisible by n_steps, batch divides rollout. Replay memory
estimate checked against cap. These are initial assumptions, never called optimal.

portfolio_rl.common:
- prepare_training(panel,config,output_dir,resume_from=None)->(gym.Env,Normalizer).
  Validates panel dates through config.training_end<=2021, dataset match, seeds,
  CPU1. Static normalizer fits per-asset log-return moments on TRAIN ONLY; weights
  use identity transform. No reward normalization; transformed obs clipped ±10.
  Persisted normalizer is frozen for evaluation and resume. No full-series stats.
- fit_and_save(model,panel,config,output_dir,normalizer,*,progress=None,
  cancelled=None,save_replay=False,resume=False)->dict. progress receives JSON
  telemetry dict, cancelled is zero-arg bool. Callback writes checkpoints and
  final model.zip/normalizer.json/manifest.json; DDPG also replay_buffer.pkl.
  Returns manifest including status completed|cancelled, actual_timesteps,
  duration_seconds, learning_metrics, hashes/config/dependencies/data provenance.
- load_bundle(artifact_dir)->PolicyBundle with predict(raw_observation,
  deterministic=True)->NDArray[float32]. Bundle verifies file hashes before load,
  uses frozen normalizer and exposes manifest. Local trusted artifacts only.
- compatibility_signature(config) excludes name/budget/checkpoint/time/memory
  controls; resume requires all learning/economic/data settings unchanged.

Algorithm exports:
`train_ppo(panel,config,output_dir,*,progress=None,cancelled=None,resume_from=None)`
and identical train_ddpg. Both call prepare_training then construct SB3 model
with device='cpu',seed, policy_kwargs configurable net_arch. Resume uses class.load
with env, force_reset=True; DDPG loads verified replay_buffer.pkl explicitly.
fit_and_save(...,resume=resume_from is not None,save_replay=ddpg).

Resume restores optimizer/model/normalizer/replay but resets episode; not bitwise
equivalence to uninterrupted training. Checkpoint ZIP hashes are integrity checks,
not a reproducibility metric. Compare learned tensors/predictions/equity instead.

## Evaluation agent independent interfaces

`evaluation_window(panel,start,end,lookback)->PricePanel` includes exactly W+1
prior closes before the first execution; end before2024; requires enough history.
`evaluate_policy(panel,predictor,config,*,train_end,eval_start='2022-01-01',
eval_end='2023-12-31')->Result` predictor accepts raw obs, returns action; bundle
does normalization. Config economic fields/name/strategy/lookback; strategy ppo/ddpg.
Validate eval_start>train_end and train_end<=2021. Use PortfolioEnv unchanged.
`evaluate_baseline_window(panel,config,*,eval_start,eval_end)->Result` uses existing
research engine over the same warmup+evaluation window. Do not alter baselines.
Additional exports extra_metrics(result), seed_summary(results),
paired_block_bootstrap(result_a,result_b,seed=42), select_candidate(fold_reports),
WALK_FORWARD_FOLDS. Root adapts any small signature differences explicitly.
Keep existing Result.metrics keys; extra CAGR/turnover/weights statistics in
manifest['research_metrics'] to preserve schemas. All financial canonical values
come from shared accounting/core or persisted results, never frontend.

Walk-forward: train2015–2018→2019; train2015–2020→2021. Controlled candidate
learning rates from predeclared profiles, equal budgets, one fixed development
seed, select mean fold Sharpe with deterministic tie-break. Selection never uses
2022–2023. Final models train2015–2021; evaluate2022–2023 independently; publish
every seed. No choosing best checkpoint/seed on validation. End2024 remains locked.

## Jobs, API and artifacts (Root)

Persistent training_jobs SQLite table: pending→running→completed|failed|cancelled.
One subprocess at a time (separate from HTTP/backtest thread), queue cap4;
progress JSON atomic, events JSONL, cooperative cancel marker and bounded force
termination, CPU1/memory/wall limits. RSS and CPU sampling includes the process
tree. Crash recovery fails interrupted jobs.
POST /api/v1/training, GET list/detail, POST /{id}/cancel. POST /{id}/evaluate
replays validation. POST /{id}/compare compares matching evaluated models
and both baselines.
GET /api/v1/models returns completed usable checkpoints. No arbitrary artifact
path/upload accepted; IDs select verified files under the configured training root.
Existing experiments may use ppo/ddpg plus model_id for saved-model backtests;
model/dataset/economics/lookback must match. No2024 option. Shared OpenAPI generated.
