import { expect, test, type APIRequestContext } from "@playwright/test";
import type { components } from "../../packages/contracts/schema";

type Experiment = components["schemas"]["Experiment"];
const api = "http://127.0.0.1:8000";
const money = (value: number) => new Intl.NumberFormat("es-CO", {
  style: "currency", currency: "USD", currencyDisplay: "code", maximumFractionDigits: 2,
}).format(value);

async function completed(request: APIRequestContext, id: string): Promise<Experiment> {
  let experiment: Experiment | undefined;
  await expect.poll(async () => {
    const response = await request.get(`${api}/api/v1/experiments/${id}`);
    expect(response.ok()).toBeTruthy();
    experiment = await response.json() as Experiment;
    return experiment.status;
  }).toBe("completed");
  return experiment!;
}

async function seedRun(request: APIRequestContext): Promise<Experiment> {
  const response = await request.post(`${api}/api/v1/experiments`, {
    data: { name: "Browser visual fixture", initial_capital: 10000, transaction_cost_bps: 10 },
  });
  expect(response.status()).toBe(202);
  return completed(request, (await response.json()).id);
}

test("browser submits a real fixture and renders persisted API values after reload", async ({ page, request }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/dashboard");
  await expect(page.getByText("API preparada", { exact: true })).toBeVisible();
  await expect(page.getByText("Fixture determinista · datos sintéticos de prueba")).toBeVisible();
  await expect(page.getByTestId("metric-final-equity")).toHaveCount(0);
  await page.screenshot({ path: "test-results/visual/dashboard-empty.png", fullPage: true });
  await page.getByLabel("Nombre del experimento", { exact: true }).fill("Recorrido E2E verificado");
  await page.getByLabel(/Capital inicial/).fill("25000");
  await page.getByLabel("Costos de transacción", { exact: true }).fill("25");
  const submission = page.waitForResponse(response =>
    response.url().endsWith("/api/backend/api/v1/experiments") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Ejecutar prueba", exact: true }).click();
  const response = await submission;
  expect(response.status()).toBe(202);
  const experiment = await completed(request, (await response.json()).id);
  expect(experiment.config.initial_capital).toBe(25000);
  expect(experiment.dataset.kind).toBe("FIXTURE");
  expect(experiment.result!.manifest.fixture_sha256).toBe(experiment.dataset.sha256);
  await expect(page.getByTestId("metric-final-equity")).toHaveText(money(experiment.result!.metrics.final_equity));
  await expect(page.getByTestId("equity-chart")).toBeVisible();
  await page.getByText("Ver datos de la curva", { exact: true }).click();
  const curve = page.getByRole("region", { name: "Valores de la curva de capital", exact: true });
  await expect(curve.getByRole("row")).toHaveCount(experiment.result!.equity.length + 1);
  await expect(curve.getByRole("row").last()).toContainText(experiment.result!.equity.at(-1)!.date);
  await expect(curve.getByRole("row").last()).toContainText(money(experiment.result!.metrics.final_equity));
  await page.reload();
  await expect(page.getByTestId("metric-final-equity")).toHaveText(money(experiment.result!.metrics.final_equity));
  expect(errors).toEqual([]);
});

test("proxy rejects unknown routes, cross-origin writes and oversized/non-JSON bodies", async ({ request }) => {
  expect((await request.get("/api/backend/not-an-api")).status()).toBe(404);
  const crossOrigin = await request.post("/api/backend/api/v1/experiments", {
    data: { name: "Forbidden" }, headers: { Origin: "https://untrusted.example" },
  });
  expect(crossOrigin.status()).toBe(403);
  const wrongType = await request.post("/api/backend/api/v1/experiments", {
    data: '{"name":"Wrong type"}', headers: { "Content-Type": "text/plain" },
  });
  expect(wrongType.status()).toBe(415);
  const oversized = await request.post("/api/backend/api/v1/experiments", {
    data: { name: "x".repeat(17000) },
  });
  expect(oversized.status()).toBe(413);
  const invalid = await request.post("/api/backend/api/v1/experiments", {
    data: { name: "Invalid", initial_capital: -100 },
  });
  expect(invalid.status()).toBe(422);
  expect((await request.post("/api/backend/api/v1/experiments", {
    data: Buffer.from("{"), headers: { "Content-Type": "application/json" },
  })).status()).toBe(400);
  const localAlias = await request.post("/api/backend/api/v1/experiments", {
    data: { name: "Localhost origin verification" },
    headers: { Host: "localhost:3000", Origin: "http://localhost:3000" },
  });
  expect(localAlias.status()).toBe(202);
});

test("offline UI shows a recoverable error without substituting fixture results", async ({ page }) => {
  await page.route("**/api/backend/**", route => route.fulfill({
    status: 502, contentType: "application/json", body: JSON.stringify({ detail: "API no disponible en prueba de fallo" }),
  }));
  await page.goto("/dashboard");
  await expect(page.getByRole("alert").filter({ hasText: "No pudimos completar" })).toContainText("API no disponible");
  await expect(page.getByRole("button", { name: "Ejecutar prueba", exact: true })).toBeDisabled();
  await expect(page.getByTestId("metric-final-equity")).toHaveCount(0);
  await page.unroute("**/api/backend/**");
  await page.getByRole("button", { name: "Reintentar", exact: true }).click();
  await expect(page.getByText("API preparada", { exact: true })).toBeVisible();
});

for (const width of [1440, 1280, 768, 390]) {
  test(`real results remain usable at ${width}px`, async ({ page, request }) => {
    const experiment = await seedRun(request);
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    await page.goto("/dashboard");
    await expect(page.getByTestId("metric-final-equity")).toHaveText(money(experiment.result!.metrics.final_equity));
    const dimensions = await page.evaluate(() => ({
      width: window.innerWidth,
      scrollWidth: document.documentElement.scrollWidth,
      containers: Array.from(document.querySelectorAll(".table-scroll,.main-nav,.main-content,.sidebar,.page-footer"))
        .map(element => ({ class: element.className, width: element.clientWidth, scroll: element.scrollWidth,
          right: element.getBoundingClientRect().right, overflow: getComputedStyle(element).overflowX })),
      overflowing: Array.from(document.querySelectorAll("body *"))
        .filter(element => element.getBoundingClientRect().right > window.innerWidth + 1)
        .slice(0, 12).map(element => ({ tag: element.tagName, class: element.className })),
    }));
    expect(dimensions.scrollWidth, JSON.stringify(dimensions)).toBeLessThanOrEqual(dimensions.width);
    await expect(page.getByRole("button", { name: "Ejecutar prueba", exact: true })).toBeEnabled();
    await expect(page.getByRole("img", { name: "Evolución del capital simulado en USD" })).toBeVisible();
    await page.screenshot({ path: `test-results/visual/dashboard-${width}.png`, fullPage: true });
    await page.screenshot({ path: `test-results/visual/dashboard-${width}-viewport.png` });
    await page.locator(".chart-card").screenshot({ path: `test-results/visual/chart-${width}.png` });
    if (width === 1440) {
      await page.getByRole("button", { name: "Activar tema claro", exact: true }).click();
      await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
      await page.screenshot({ path: "test-results/visual/dashboard-light.png", fullPage: true });
      await page.reload();
      await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
    }
  });
}

test("keyboard navigation reaches the labeled form with a visible focus state", async ({ page }) => {
  await page.goto("/dashboard");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Saltar al contenido" })).toBeFocused();
  await page.getByLabel("Nombre del experimento", { exact: true }).focus();
  const outline = await page.getByLabel("Nombre del experimento", { exact: true }).evaluate(element => {
    const style = getComputedStyle(element);
    return `${style.outlineStyle} ${style.outlineWidth} ${style.boxShadow}`;
  });
  expect(outline).not.toBe("none 0px none");
});
