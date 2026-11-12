import { expect, test } from "@playwright/test";
import type { components } from "../../packages/contracts/schema";

type Dataset = components["schemas"]["Dataset"];
type Experiment = components["schemas"]["Experiment"];
const money = (value: number) => new Intl.NumberFormat("es-CO", {
  style: "currency", currency: "USD", currencyDisplay: "code", maximumFractionDigits: 2,
}).format(value);

for (const [strategy, width] of [["markowitz", 1440], ["equal_weight", 390]] as const) {
  test(`real historical ${strategy} from browser to persistence at ${width}px`, async ({ page, request }) => {
    const response = await request.get("http://127.0.0.1:8000/api/v1/datasets");
    expect(response.ok()).toBeTruthy();
    const datasets = (await response.json()).items as Dataset[];
    const historical = datasets.find(dataset => dataset.kind === "HISTORICAL");
    expect(historical, "Run the REAL download_history.py pipeline before this suite; no synthetic substitute is allowed.").toBeDefined();
    expect(historical!.assets).toEqual(["AAPL", "MSFT", "JPM", "JNJ", "XOM", "PG", "KO", "WMT", "SPY", "GLD"]);
    expect(historical!.observations).toBe(2516);
    expect(historical!.source).toContain("Yahoo");
    const pageErrors: string[] = [];
    page.on("pageerror", error => pageErrors.push(error.message));
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/dashboard");
    await expect(page.getByText("API preparada", { exact: true })).toBeVisible();
    await page.getByLabel("Origen de datos", { exact: true }).selectOption(historical!.id);
    await expect(page.getByText("Datos históricos reales · simulación PAPER", { exact: true })).toBeVisible();
    await page.getByLabel("Estrategia", { exact: true }).selectOption(strategy);
    await page.getByLabel("Nombre del experimento", { exact: true }).fill(`Histórico verificable · ${strategy}`);
    await page.getByLabel("Partición de evaluación", { exact: true }).selectOption("validation");
    expect(await page.getByLabel("Partición de evaluación", { exact: true }).locator("option").allTextContents())
      .toEqual(["Entrenamiento · 2015–2021", "Validación · 2022–2023"]);
    const submitted = page.waitForResponse(result =>
      result.request().method() === "POST" && result.url().endsWith("/api/backend/api/v1/experiments"));
    await page.getByRole("button", { name: "Ejecutar prueba", exact: true }).click();
    const submission = await submitted;
    expect(submission.status()).toBe(202);
    const id = (await submission.json()).id as string;
    let finished: Experiment | undefined;
    await expect.poll(async () => {
      finished = await (await request.get(`http://127.0.0.1:8000/api/v1/experiments/${id}`)).json() as Experiment;
      return finished.status;
    }, { timeout: 60_000 }).toBe("completed");
    expect(finished!.config.strategy).toBe(strategy);
    expect(finished!.dataset.kind).toBe("HISTORICAL");
    expect(finished!.result!.manifest.dataset_sha256).toBe(historical!.sha256);
    expect(finished!.result!.equity.at(-1)!.date).toBe("2023-12-29");
    await expect(page.getByTestId("run-data-kind")).toHaveText("HISTORICAL");
    await expect(page.getByTestId("metric-final-equity")).toHaveText(money(finished!.result!.metrics.final_equity), { timeout: 30_000 });
    await expect(page.getByTestId("result-provenance")).toContainText("datos históricos reales");
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
    await page.screenshot({ path: `test-results/historical/dashboard-${strategy}-${width}.png` });
    await page.locator(".chart-card").screenshot({ path: `test-results/historical/chart-${strategy}-${width}.png` });
    await page.reload();
    await expect(page.getByTestId("metric-final-equity")).toHaveText(money(finished!.result!.metrics.final_equity));
    expect(pageErrors).toEqual([]);
  });
}
