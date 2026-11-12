import { expect, test } from "@playwright/test";
import type { components } from "../../packages/contracts/schema";

type Run = components["schemas"]["DeskRun"];
const api = "http://127.0.0.1:8124/api/v1";

test("Agent Desk uses real historical facts with explicit mock inference, persists approval and veto", async ({ page, request }, info) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/dashboard#agent-desk");
  const desk = page.getByRole("region", { name: "AI Agent Desk", exact: true });
  await expect(desk.getByTestId("desk-provider")).toContainText("Proveedor simulado · pruebas");
  await expect(desk.getByText("Sin análisis guardados", { exact: true })).toBeAttached();
  const date = desk.getByLabel("Fecha de decisión al cierre");
  await expect(date).toHaveAttribute("max", "2023-12-29");
  const submit = desk.getByRole("button", { name: "Analizar propuesta" });
  await expect(submit, "Agent Desk E2E requires the verified real historical snapshot").toBeEnabled();

  async function run(strategy: string): Promise<Run> {
    await desk.getByLabel("Estrategia de la propuesta").selectOption(strategy);
    const response = page.waitForResponse(item => item.request().method() === "POST" &&
      item.url().endsWith("/api/backend/api/v1/agent-desk/runs"));
    await submit.click();
    const submitted = await response;
    expect(submitted.status()).toBe(202);
    const { id } = await submitted.json() as Run;
    let latest!: Run;
    await expect.poll(async () => {
      latest = await (await request.get(`${api}/agent-desk/runs/${id}`)).json() as Run;
      return latest.outcome?.decision ?? latest.status;
    }, { timeout: 30_000 }).toBe(strategy === "equal_weight" ? "approved" : "blocked");
    expect(latest.provider.provider).toBe("mock");
    expect(latest.mode).toBe("PAPER");
    expect(latest.scope).toBe("llm_exploratory_historical");
    expect(latest.outcome?.dossier?.information_date).toBe("2023-12-29");
    expect(latest.outcome?.dossier?.assets).toHaveLength(10);
    expect(latest.events?.map(event => event.event.stage))
      .toEqual(["data", "analyst", "strategist", "judge", "risk", "final"]);
    expect(latest.outcome?.judgment?.verdict).toBe("approve");
    return latest;
  }

  const approved = await run("equal_weight");
  expect(approved.outcome?.risk?.passed).toBe(true);
  await expect(desk.getByTestId("desk-decision")).toContainText("Aprobada para investigación");
  await expect(desk.getByRole("list", { name: "Pesos de la propuesta" }).getByRole("listitem")).toHaveCount(10);
  await expect(desk.getByText("Eventos y metadatos del proveedor")).toBeVisible();
  await desk.screenshot({ path: info.outputPath("agent-desk-1440.png") });

  await page.setViewportSize({ width: 768, height: 900 });
  const veto = await run("markowitz");
  expect(veto.outcome?.risk?.gates.some(gate => !gate.passed &&
    gate.reason_code === "position_limit_exceeded")).toBe(true);
  await expect(desk.getByTestId("desk-decision")).toContainText("Bloqueada");
  await expect(desk.getByRole("region", { name: "Controles de riesgo" })).toContainText("position_limit_exceeded");
  expect(await desk.locator(".desk-flow").evaluate(node => node.scrollWidth)).toBeLessThanOrEqual(
    await desk.locator(".desk-flow").evaluate(node => node.clientWidth),
  );
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(768);
  await desk.screenshot({ path: info.outputPath("agent-desk-768.png") });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await expect(desk.getByLabel("Historial de decisiones")).toHaveValue(veto.id);
  await desk.getByLabel("Historial de decisiones").selectOption(approved.id);
  await expect(desk.getByTestId("desk-decision")).toContainText("Aprobada para investigación");
  await expect(desk.getByText("Eventos y metadatos del proveedor")).toBeVisible();
  expect(await desk.locator(".desk-facts .run-id").evaluate(node => node.scrollWidth)).toBeLessThanOrEqual(
    await desk.locator(".desk-facts .run-id").evaluate(node => node.clientWidth),
  );
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await desk.screenshot({ path: info.outputPath("agent-desk-390.png") });
  expect((await (await request.get(`${api}/experiments`)).json()).items).toEqual([]);
  const locked = await request.post(`${api}/agent-desk/runs`, { data: {
    dataset_id: approved.request.dataset_id, decision_date: "2024-01-03", strategy: "equal_weight",
  } });
  expect(locked.status()).toBe(422);
  expect(errors).toEqual([]);
  await info.attach("run-ids", { body: JSON.stringify({ approved: approved.id, veto: veto.id }),
    contentType: "application/json" });
});
