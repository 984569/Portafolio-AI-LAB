"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { RefreshCw, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiRequest } from "@/lib/api";
import type { Dataset, DeskAvailability, DeskRequest, DeskRun, ModelInfo } from "@/lib/contracts";

const route = "api/v1/agent-desk";
const names = { equal_weight: "Equal-weight", markowitz: "Markowitz", ppo: "PPO", ddpg: "DDPG" };
const stages = {
  data: "Datos", analyst: "Market Analyst", strategist: "Quant Strategist",
  judge: "Portfolio Judge", risk: "Motor de riesgos", final: "Chief Orchestrator",
} as const;
const decisions = { approved: "Aprobada para investigación", watch: "En observación", rejected: "Rechazada", blocked: "Bloqueada" };
const statusLabels = { queued: "En cola", running: "En análisis", completed: "Finalizada", blocked: "Bloqueada" };
const verdicts = { approve: "Aprobar", watch: "Observar", reject: "Rechazar" };
const reasons = {
  aligned: "El Judge consideró que la propuesta es coherente con el dossier.",
  concentration: "El Judge señaló la concentración de los pesos.",
  volatility: "El Judge señaló la volatilidad del escenario.",
  caution: "El Judge pidió cautela con la información disponible.",
};
const evidenceNames = {
  market_return: "Retorno de la ventana", market_volatility: "Volatilidad del universo",
  weights: "Pesos propuestos", turnover: "Rotación", portfolio_volatility: "Volatilidad del portafolio",
};
const trends = { up: "Alcista", down: "Bajista", mixed: "Mixta" };
const regimes = { low: "Baja", moderate: "Moderada", high: "Alta" };
const gateLabels: Record<string, string> = {
  snapshot: "Identidad del snapshot", chronology: "Fecha y calendario",
  dossier_universe: "Universo del dossier", coverage: "Cobertura histórica",
  market_return: "Retorno del universo", market_volatility: "Volatilidad del universo",
  provider: "Respuesta del proveedor", strategy: "Procedencia de la estrategia",
  proposal_universe: "Universo de la propuesta", long_only: "Posiciones largas",
  full_investment: "Suma de pesos", position_limit: "Peso máximo por activo",
  portfolio_volatility: "Volatilidad de la propuesta", cash_turnover: "Rotación desde efectivo",
  fee_assumption: "Costo supuesto", dossier: "Dossier", candidate: "Propuesta",
};
const gateLimits: Record<string, string> = {
  "Same XNYS close in 2022–2023": "Mismo cierre XNYS de 2022–2023",
  "lookback + 1 closes; 2–120 returns": "Ventana + 1 cierres, 2–120 retornos",
  "finite and greater than −1": "Finito y mayor que −100 %",
  "finite and nonnegative": "Finita y no negativa",
  "Each weight in [0, 1]": "Cada peso entre 0 y 100 %",
};
const fractionalGates = new Set([
  "market_return", "market_volatility", "full_investment", "position_limit",
  "portfolio_volatility", "cash_turnover",
]);
const percent = (value: number) => new Intl.NumberFormat("es-CO", {
  style: "percent", maximumFractionDigits: 2,
}).format(value);
function gateValue(name: string, value: string | number | null | undefined) {
  if (typeof value === "number") {
    if (fractionalGates.has(name)) return percent(value);
    return name === "fee_assumption" ? `${value} bps` : value;
  }
  return value == null ? "—" : gateLimits[value] ?? value;
}
const active = (run?: DeskRun) => run?.status === "queued" || run?.status === "running";
const errorMessage = (cause: unknown) => cause instanceof Error ? cause.message : "No se pudo consultar el escritorio.";

export function AgentDesk({ datasets, models }: { datasets: Dataset[]; models: ModelInfo[] }) {
  const historical = datasets.filter(dataset => dataset.kind === "HISTORICAL");
  const [availability, setAvailability] = useState<DeskAvailability>();
  const [runs, setRuns] = useState<DeskRun[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState<DeskRun>();
  const [source, setSource] = useState("");
  const [strategy, setStrategy] = useState<DeskRequest["strategy"]>("equal_weight");
  const [modelId, setModelId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshCount, setRefreshCount] = useState(0);
  const [error, setError] = useState("");
  const snapshot = historical.find(dataset => dataset.id === source) ?? historical[0];
  const isRL = strategy === "ppo" || strategy === "ddpg";
  const availableModels = models.filter(model =>
    model.dataset_id === snapshot?.id && model.algorithm === strategy && model.transaction_cost_bps === 10,
  );
  const model = availableModels.find(item => item.id === modelId) ?? availableModels[0];
  const selected = detail?.id === selectedId ? detail : runs.find(run => run.id === selectedId);
  const polling = active(selected);
  const result = selected?.outcome;

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [status, history] = await Promise.all([
        apiRequest<DeskAvailability>(`${route}/status`),
        apiRequest<{ items: DeskRun[] }>(`${route}/runs`),
      ]);
      setAvailability(status);
      setRuns(history.items);
      setSelectedId(id => history.items.some(run => run.id === id) ? id : history.items[0]?.id ?? "");
      setRefreshCount(current => current + 1);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setLoading(false);
    }
  }, [setSelectedId]);

  useEffect(() => {
    const timer = window.setTimeout(() => { void refresh(); }, 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  useEffect(() => {
    if (!selectedId) return;
    const controller = new AbortController();
    let timer: number | undefined;
    async function load() {
      try {
        const run = await apiRequest<DeskRun>(`${route}/runs/${selectedId}`, {
          signal: AbortSignal.any([controller.signal, AbortSignal.timeout(12_000)]),
        });
        if (controller.signal.aborted) return;
        setDetail(run);
        setRuns(current => current.map(item => item.id === run.id ? run : item));
        if (polling && active(run)) timer = window.setTimeout(() => void load(), 900);
      } catch (cause) {
        if (!controller.signal.aborted) setError(errorMessage(cause));
      }
    }
    void load();
    return () => {
      controller.abort();
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [selectedId, polling, refreshCount]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!snapshot || !availability?.enabled || (isRL && !model)) return;
    const form = new FormData(event.currentTarget);
    const config: DeskRequest = {
      dataset_id: snapshot.id, decision_date: String(form.get("decision_date")),
      strategy, model_id: isRL ? model.id : null,
    };
    setSubmitting(true);
    setError("");
    try {
      const run = await apiRequest<DeskRun>(`${route}/runs`, {
        method: "POST", body: JSON.stringify(config),
      });
      setRuns(current => [run, ...current]);
      setDetail(run);
      setSelectedId(run.id);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setSubmitting(false);
    }
  }

  return <section id="agent-desk" className="agent-desk" aria-labelledby="agent-desk-title">
    <div className="section-heading">
      <h2 id="agent-desk-title">AI Agent Desk</h2>
      <Button variant="outline" aria-label="Actualizar Agent Desk" onClick={() => {
        setDetail(undefined);
        void refresh();
      }} disabled={loading}><RefreshCw />Actualizar</Button>
    </div>
    <div className="training-disclosure">
      <ShieldCheck size={18} aria-hidden="true" />
      <p>Investigación histórica exploratoria · PAPER · Una asignación hipotética desde efectivo.
        <strong> 2024 bloqueado.</strong></p>
    </div>
    {error && <div className="error-banner" role="status"><p>Agent Desk: {error}</p></div>}
    <div className="training-grid">
      <Card>
        <CardHeader><CardTitle>Configurar análisis</CardTitle></CardHeader>
        <CardContent>
          <p className="desk-provider" data-testid="desk-provider">
            {availability?.enabled
              ? <><Badge variant={availability.provider === "mock" ? "warning" : "secondary"}>
                {availability.provider === "mock" ? "Proveedor simulado · pruebas" : "OpenRouter configurado"}
              </Badge><code>{availability.model}</code></>
              : loading ? "Consultando proveedor…" : "Proveedor no disponible. Consulta la configuración del backend."}
          </p>
          <form className="experiment-form" onSubmit={submit}>
            <div className="field">
              <label htmlFor="desk-snapshot">Snapshot del análisis</label>
              <select id="desk-snapshot" value={snapshot?.id ?? ""} onChange={event => setSource(event.target.value)}
                disabled={!historical.length}>
                {!historical.length && <option value="">Sin históricos verificados</option>}
                {historical.map(dataset => <option key={dataset.id} value={dataset.id}>
                  {dataset.start_date.slice(0, 4)}–{dataset.end_date.slice(0, 4)} · {dataset.sha256.slice(0, 12)}
                </option>)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="desk-date">Fecha de decisión al cierre</label>
              <Input id="desk-date" name="decision_date" type="date" min="2022-01-03" max="2023-12-29"
                defaultValue="2023-12-29" required />
              <small>Elige una sesión de mercado de 2022–2023.</small>
            </div>
            <div className="field">
              <label htmlFor="desk-strategy">Estrategia de la propuesta</label>
              <select id="desk-strategy" value={strategy}
                onChange={event => setStrategy(event.target.value as DeskRequest["strategy"])}>
                {Object.entries(names).map(([id, label]) => <option key={id} value={id}
                  disabled={(id === "ppo" || id === "ddpg") && !models.some(
                    item => item.dataset_id === snapshot?.id && item.algorithm === id && item.transaction_cost_bps === 10,
                  )}>{label}</option>)}
              </select>
            </div>
            {isRL && <div className="field">
              <label htmlFor="desk-model">Modelo guardado para el análisis</label>
              <select id="desk-model" value={model?.id ?? ""} onChange={event => setModelId(event.target.value)}>
                {availableModels.map(item =>
                  <option key={item.id} value={item.id}>{item.algorithm.toUpperCase()} · semilla {item.seed} · {item.timesteps} pasos</option>)}
              </select>
            </div>}
            <Button type="submit" disabled={submitting || !availability?.enabled || !snapshot || (isRL && !model)}>
              {submitting ? "Enviando…" : "Analizar propuesta"}
            </Button>
          </form>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Flujo y decisiones</CardTitle></CardHeader>
        <CardContent className="desk-flow">
          <div className="field">
            <label htmlFor="desk-run">Historial de decisiones</label>
            <select id="desk-run" value={selectedId} onChange={event => setSelectedId(event.target.value)} disabled={!runs.length}>
              <option value="" disabled>{loading ? "Cargando…" : "Sin análisis guardados"}</option>
              {runs.map(run => <option key={run.id} value={run.id}>
                {run.request.decision_date} · {names[run.request.strategy]} · {run.outcome ? decisions[run.outcome.decision] : statusLabels[run.status]} · {run.id.slice(0, 8)}
              </option>)}
            </select>
          </div>
          {selected ? <>
            <p className="desk-verdict" aria-live="polite" data-testid="desk-decision">
              <Badge variant={result?.decision === "approved" ? "default" : selected.status === "blocked" ? "destructive" : "secondary"}>
                {result ? decisions[result.decision] : statusLabels[selected.status]}
              </Badge>
              {selected.provider.provider === "mock" && <span>Inferencia de prueba</span>}
            </p>
            {result?.decision === "blocked" && <p role="status">
              El flujo se detuvo. Motivo registrado: <code>{result.code}</code>.
            </p>}
            <ol className="desk-stages" aria-label="Estado de los agentes">
              {Object.entries(stages).map(([stage, label]) => {
                const event = selected.events?.findLast(item => item.event.stage === stage)?.event;
                return <li key={stage}><strong>{label}</strong><span>{event
                  ? event.status === "blocked" ? "Bloqueado" : "Completado"
                  : active(selected) ? "Pendiente" : "Sin evento"}</span></li>;
              })}
            </ol>
            {result?.dossier && <div className="desk-facts">
              <h3>Dossier al cierre</h3>
              <p>{result.dossier.information_date} · {result.dossier.observations} cierres · {result.dossier.assets.length} activos</p>
              <p>Retorno de la ventana {percent(result.dossier.market_return)} · Volatilidad anualizada {percent(result.dossier.market_volatility)}</p>
              <small className="run-id">SHA-256 {result.dossier.dataset_sha256}</small>
            </div>}
            {result?.analysis && <div className="desk-facts">
              <h3>Market Analyst</h3>
              <p>Tendencia {trends[result.analysis.trend].toLowerCase()} · Volatilidad {regimes[result.analysis.regime].toLowerCase()}</p>
              <small>Evidencias citadas: {result.analysis.evidence.map(id => evidenceNames[id]).join(", ")}.</small>
            </div>}
            {result?.judgment && <div className="desk-facts">
              <h3>Portfolio Judge</h3>
              <p><strong>{verdicts[result.judgment.verdict]}.</strong> {reasons[result.judgment.reason]}</p>
              <small>Evidencias citadas: {result.judgment.evidence.map(id => evidenceNames[id]).join(", ")}.</small>
            </div>}
          </> : <div className="history-empty"><p>Las decisiones y los controles quedarán disponibles aquí al solicitar un análisis.</p></div>}
        </CardContent>
      </Card>
    </div>
    {result?.candidate && <Card className="desk-result-card">
      <CardHeader><CardTitle>Propuesta de asignación · {names[result.candidate.strategy]}</CardTitle></CardHeader>
      <CardContent>
        <p className="muted text-sm">Volatilidad estimada {percent(result.candidate.annualized_volatility)} ·
          Rotación L1 {percent(result.candidate.turnover)} · Costo supuesto {result.candidate.fee_bps} bps</p>
        {result.candidate.optimizer_fallback && <p>El optimizador devolvió su alternativa de pesos iguales.</p>}
        <ul className="desk-weights" aria-label="Pesos de la propuesta">
          {Object.entries(result.candidate.weights).map(([ticker, weight]) => <li key={ticker}>
            <strong>{ticker}</strong><progress value={weight} max={1} aria-label={`Peso de ${ticker}`} />
            <span>{percent(weight)}</span>
          </li>)}
        </ul>
      </CardContent>
    </Card>}
    {result?.risk && <Card className="desk-result-card">
      <CardHeader><CardTitle>Controles de riesgo · {result.risk.passed ? "Superados" : "Veto"}</CardTitle></CardHeader>
      <CardContent><div className="table-scroll" role="region" aria-label="Controles de riesgo" tabIndex={0}>
        <table><thead><tr><th>Control</th><th>Estado</th><th>Código</th><th>Observado</th><th>Límite</th></tr></thead>
          <tbody>{result.risk.gates.toSorted((a, b) => Number(a.passed) - Number(b.passed)).map(gate => <tr key={gate.name}>
            <td>{gateLabels[gate.name] ?? gate.name}</td><td>{gate.passed ? "Superado" : "Bloqueado"}</td>
            <td><code>{gate.reason_code}</code></td>
            <td>{gateValue(gate.name, gate.observed)}</td><td>{gateValue(gate.name, gate.threshold)}</td>
          </tr>)}</tbody>
        </table>
      </div></CardContent>
    </Card>}
    {selected && !!selected.events?.length && <Card className="desk-result-card">
      <CardHeader><CardTitle>Auditoría y procedencia</CardTitle></CardHeader>
      <CardContent>
        <p className="run-id">Ejecución {selected.id} · {selected.created_at}</p>
        <details><summary>Eventos y metadatos del proveedor</summary>
          <pre className="quality-json">{JSON.stringify(selected.events, null, 2)}</pre>
        </details>
      </CardContent>
    </Card>}
  </section>;
}
