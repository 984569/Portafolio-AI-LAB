import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import type { components } from "../../packages/contracts/schema";

type Dataset = components["schemas"]["Dataset"];
type TrainingJob = components["schemas"]["TrainingJob"];
type Result = components["schemas"]["Result"];
type ComparisonReport = components["schemas"]["ComparisonReport"];
type Experiment = components["schemas"]["Experiment"];
type Algorithm = TrainingJob["config"]["algorithm"];

const api = "http://127.0.0.1:8123/api/v1";
const hash = /^[a-f0-9]{64}$/;
const comparisonName = "Comparación de estrategias entrenadas";

async function get<T>(request: APIRequestContext, resource: string): Promise<T> {
  const response = await request.get(`${api}/${resource}`);
  expect(response.ok()).toBe(true);
  return await response.json() as T;
}

async function postFromUI<T>(page: Page, endpoint: string, button: string, status: number): Promise<T> {
  const responsePending = page.waitForResponse(response =>
    response.request().method() === "POST" && response.url().endsWith(`/api/backend/api/v1/${endpoint}`),
  { timeout: 90_000 });
  await page.getByRole("button", { name: button, exact: true }).click();
  const response = await responsePending;
  expect(response.status(), response.status() === status ? endpoint : await response.text()).toBe(status);
  return await response.json() as T;
}

async function submitTraining(page: Page, algorithm: Algorithm, name: string, steps: number) {
  await page.getByLabel("Algoritmo de entrenamiento").selectOption(algorithm);
  await page.getByLabel("Nombre del entrenamiento").fill(name);
  await page.getByLabel("Pasos de entrenamiento").fill(String(steps));
  await page.getByLabel("Arquitectura · dos capas").selectOption("32");
  return postFromUI<TrainingJob>(page, "training", "Entrenar modelo", 202);
}

async function terminalJob(request: APIRequestContext, id: string, timeout: number): Promise<TrainingJob> {
  let job: TrainingJob | undefined;
  await expect.poll(async () => {
    job = await get<TrainingJob>(request, `training/${id}`);
    return job.status;
  }, { timeout, intervals: [500, 1000, 2000] }).toMatch(/^(completed|failed|cancelled)$/);
  return job!;
}

function checkEvaluation(result: Result, snapshot: Dataset) {
  expect(result.manifest).toMatchObject({
    dataset_sha256: snapshot.sha256,
    data_mode: "HISTORICAL",
    mode: "PAPER",
    training_end: "2021-12-31",
    requested_evaluation: { start: "2022-01-01", end: "2023-12-31" },
    evaluation: { split: "validation", intervals: 500, holdout_evaluated: false },
  });
  expect(result.equity[0].date).toBe("2022-01-03");
  expect(result.equity.at(-1)?.date).toBe("2023-12-29");
  expect(result.metrics.total_costs).toBeGreaterThan(0);
}

test("real browser training, validation, comparison and replay on desktop and mobile", async ({ page, request }, testInfo) => {
  const { items: datasets } = await get<{ items: Dataset[] }>(request, "datasets");
  expect(datasets.every(dataset => dataset.kind === "HISTORICAL")).toBe(true);
  const snapshot = datasets[0];
  expect(snapshot, "Run the real historical download before this suite.").toBeDefined();
  expect(snapshot.observations).toBe(2516);
  expect(snapshot.sha256).toMatch(hash);
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/dashboard");
  await expect(page.getByText("API preparada", { exact: true })).toBeVisible();
  const research = page.getByRole("region", { name: "AI Research Lab", exact: true });
  await expect(research.getByText(`Snapshot ${snapshot.sha256.slice(0, 12)}`, { exact: false })).toBeVisible();
  const models: { algorithm: Algorithm; id: string; evaluation: Result }[] = [];

  for (const [algorithm, width] of [["ppo", 1440], ["ddpg", 390]] as const) {
    await test.step(`Train and evaluate ${algorithm} at ${width}px`, async () => {
      await page.setViewportSize({ width, height: 900 });
      const job = await submitTraining(page, algorithm, `E2E histórico ${algorithm.toUpperCase()}`, 256);
      const completed = await terminalJob(request, job.id, 120_000);
      expect(completed.status, completed.error ?? "").toBe("completed");
      expect(completed.progress?.peak_rss_mb).toBeGreaterThan(100);
      expect(completed.dataset).toMatchObject({ kind: "HISTORICAL", sha256: snapshot.sha256 });
      expect(completed.config).toMatchObject({ algorithm, seed: 42, lookback: 60, transaction_cost_bps: 10 });
      expect(completed.manifest).toMatchObject({
        actual_timesteps: 256,
        training_end: "2021-12-31",
        normalization_fit_end: "2021-12-31",
        holdout_2024_used: false,
        validation_used_for_training: false,
        checkpoints: [{ path: "checkpoints/step-00000256", timesteps: 256 }],
        files: { "model.zip": expect.stringMatching(hash), "normalizer.json": expect.stringMatching(hash) },
      });
      expect(Object.keys(completed.manifest?.learning_metrics ?? {})).not.toHaveLength(0);
      await expect(research.getByTestId("training-status")).toHaveText("Completado");
      const evaluation = await postFromUI<Result>(page, `training/${job.id}/evaluate`, "Evaluar validación", 200);
      checkEvaluation(evaluation, snapshot);
      const evaluationView = research.getByTestId("training-evaluation");
      await expect(evaluationView.getByRole("heading", { name: "Validación 2022–2023" })).toBeVisible();
      await expect(evaluationView.getByText(`${(evaluation.metrics.cumulative_return * 100).toFixed(2)} %`, { exact: true })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
      await evaluationView.screenshot({ path: testInfo.outputPath(`training-${algorithm}-${width}.png`) });
      models.push({ algorithm, id: job.id, evaluation });
    });
  }

  await test.step("Compare all four strategies", async () => {
    await page.setViewportSize({ width: 1440, height: 900 });
    const report = await postFromUI<ComparisonReport>(page, `training/${models[1].id}/compare`, "Comparar estrategias", 200);
    expect(report.holdout_2024_evaluated).toBe(false);
    expect(report.items.map(item => item.algorithm).sort()).toEqual(["ddpg", "equal_weight", "markowitz", "ppo"]);
    const comparison = research.getByRole("region", { name: comparisonName });
    for (const { algorithm, id, evaluation } of models) {
      expect(report.items.find(item => item.model_id === id)).toMatchObject({ algorithm, metrics: evaluation.metrics });
    }
    for (const algorithm of ["PPO", "DDPG", "MARKOWITZ", "EQUAL_WEIGHT"]) {
      await expect(comparison.getByRole("cell", { name: algorithm, exact: true })).toBeVisible();
    }
    await comparison.locator("..").locator("..").screenshot({ path: testInfo.outputPath("training-comparison-1440.png") });
    await testInfo.attach("Real validation comparison", { body: JSON.stringify(report, null, 2), contentType: "application/json" });
  });

  for (const { algorithm, id, evaluation } of models) {
    await test.step(`Replay saved ${algorithm} model`, async () => {
      const width = algorithm === "ppo" ? 1440 : 390;
      await page.setViewportSize({ width, height: 900 });
      await page.getByLabel("Origen de datos", { exact: true }).selectOption(snapshot.id);
      await page.getByLabel("Estrategia", { exact: true }).selectOption(algorithm);
      await page.getByLabel("Modelo entrenado").selectOption(id);
      await expect(page.getByLabel("Partición de evaluación")).toBeDisabled();
      await expect(page.getByLabel("Partición de evaluación")).toHaveValue("validation");
      await expect(page.getByLabel("Aversión al riesgo")).toBeDisabled();
      await page.getByLabel("Nombre del experimento").fill(`E2E replay ${algorithm.toUpperCase()}`);
      const submitted = await postFromUI<Experiment>(page, "experiments", "Ejecutar prueba", 202);
      let experiment: Experiment | undefined;
      await expect.poll(async () => {
        experiment = await get<Experiment>(request, `experiments/${submitted.id}`);
        return experiment.status;
      }, { timeout: 60_000 }).toMatch(/^(completed|failed)$/);
      expect(experiment?.status, experiment?.error ?? "").toBe("completed");
      expect(experiment?.config).toMatchObject({ strategy: algorithm, model_id: id, split: "validation" });
      const replay = experiment!.result!;
      checkEvaluation(replay, snapshot);
      expect(replay.metrics).toEqual(evaluation.metrics);
      expect(replay.equity).toEqual(evaluation.equity);
      expect(replay.manifest).toMatchObject({ model_id: id, model_files: { "model.zip": expect.stringMatching(hash) } });
      const equity = page.getByTestId("metric-final-equity");
      await expect(equity).toHaveAttribute("data-value", String(replay.metrics.final_equity));
      await expect(page.getByTestId("result-provenance")).toContainText("datos históricos reales");
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
      await page.locator(".chart-card").screenshot({ path: testInfo.outputPath(`training-replay-${algorithm}-${width}.png`) });
      await page.reload();
      await expect(equity).toHaveAttribute("data-value", String(replay.metrics.final_equity));
    });
  }
  expect(errors).toEqual([]);
});

test("cancel a real training job from the browser", async ({ page, request }) => {
  await page.goto("/dashboard");
  await expect(page.getByText("API preparada", { exact: true })).toBeVisible();
  const job = await submitTraining(page, "ppo", "E2E cancelación histórica", 16_384);
  await expect.poll(async () => {
    const running = await get<TrainingJob>(request, `training/${job.id}`);
    return running.status === "running" && Number(running.progress?.peak_rss_mb) > 100;
  }, { timeout: 60_000 }).toBe(true);
  await postFromUI<TrainingJob>(page, `training/${job.id}/cancel`, "Cancelar entrenamiento", 200);
  const cancelled = await terminalJob(request, job.id, 30_000);
  expect(cancelled.status, cancelled.error ?? "").toBe("cancelled");
  expect(cancelled.dataset.kind).toBe("HISTORICAL");
  expect(cancelled.cancel_requested).toBe(true);
  expect(cancelled.progress?.peak_rss_mb).toBeGreaterThan(100);
  await expect(page.getByTestId("training-status")).toHaveText("Cancelado");
  await expect(page.getByRole("button", { name: "Evaluar validación", exact: true })).toBeDisabled();
  const models = await get<{ items: { id: string }[] }>(request, "models");
  expect(models.items.map(model => model.id)).not.toContain(job.id);
});
