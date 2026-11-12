"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Activity, ArrowDownRight, ArrowRight, ArrowUpRight, Braces, CheckCircle2, ChevronRight, CircleHelp, Database, FlaskConical, Layers3, LoaderCircle, Moon, Play, RefreshCw, ShieldCheck, Sun, TerminalSquare, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { TrainingLab } from "@/components/training-lab";
import { AgentDesk } from "@/components/agent-desk";
import { EquityChart } from "@/components/equity-chart";
import { apiRequest } from "@/lib/api";
import type { Dataset, Experiment, ExperimentConfig, Result, ModelInfo } from "@/lib/contracts";

const strategyNames = { equal_weight: "Equal weight", markowitz: "Markowitz", ppo: "PPO", ddpg: "DDPG" };
const money = (value: number) => new Intl.NumberFormat("es-CO", { style: "currency", currency: "USD", currencyDisplay: "code", maximumFractionDigits: 2 }).format(value);
const percent = (value: number) => new Intl.NumberFormat("es-CO", { style: "percent", minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value);
const decimal = (value: number) => new Intl.NumberFormat("es-CO", { maximumFractionDigits: 3 }).format(value);
const dateTime = (value: string) => new Intl.DateTimeFormat("es-CO", { dateStyle: "short", timeStyle: "short", timeZone: "America/Bogota" }).format(new Date(value));
const statusLabels = { queued: "En cola", running: "En ejecución", completed: "Completado", failed: "Fallido" } as const;
const isActive = (experiment: Experiment) => experiment.status === "queued" || experiment.status === "running";

function RunBadge({ status }: { status: Experiment["status"] }) {
  return <Badge variant={status === "failed" ? "destructive" : status === "completed" ? "default" : "warning"}>
    {status === "completed" ? <CheckCircle2 size={12} aria-hidden="true" /> : status === "queued" || status === "running" ? <LoaderCircle size={12} className="spinner" aria-hidden="true" /> : <TriangleAlert size={12} aria-hidden="true" />}
    {statusLabels[status]}
  </Badge>;
}

export function Dashboard() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [datasetId, setDatasetId] = useState("");
  const [strategy, setStrategy] = useState<ExperimentConfig["strategy"]>("equal_weight");
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [modelId, setModelId] = useState("");
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [health, setHealth] = useState<"loading" | "online" | "offline">("loading");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const selected = experiments.find((experiment) => experiment.id === selectedId);
  const dataset = datasets.find((item) => item.id === datasetId);
  const historical = dataset?.kind === "HISTORICAL";
  const isRL = strategy === "ppo" || strategy === "ddpg";
  const compatibleModels = models.filter(model => model.dataset_id === datasetId && model.algorithm === strategy);
  const chosenModel = compatibleModels.find(model => model.id === modelId) ?? compatibleModels[0];
  const active = experiments.some(isActive);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [live, ready, datasetList, history, modelList] = await Promise.all([
        apiRequest<{ status: string; mode: string }>("health"),
        apiRequest<{ status: string; mode: string }>("ready"),
        apiRequest<{ items: Dataset[] }>("api/v1/datasets"),
        apiRequest<{ items: Experiment[] }>("api/v1/experiments"),
        apiRequest<{ items: ModelInfo[] }>("api/v1/models"),
      ]);
      if (live.status !== "ok" || live.mode !== "PAPER" || ready.status !== "ready" || ready.mode !== "PAPER") {
        throw new Error("El servicio no confirmó un entorno PAPER preparado.");
      }
      setModels(modelList.items);
      setDatasets(datasetList.items);
      setDatasetId((current) => datasetList.items.some((item) => item.id === current) ? current : datasetList.items[0]?.id ?? "");
      setExperiments(history.items);
      setSelectedId((current) => history.items.some((item) => item.id === current) ? current : history.items[0]?.id ?? "");
      setHealth("online");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No fue posible cargar el laboratorio.");
      setHealth("offline");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      try {
        const savedTheme = localStorage.getItem("pal-theme");
        if (savedTheme === "light") {
          document.documentElement.dataset.theme = "light";
          setTheme("light");
        }
      } catch { /* Theme still works if browser storage is disabled. */ }
      void refresh();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    let inFlight = false;
    const timer = window.setInterval(async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const history = await apiRequest<{ items: Experiment[] }>("api/v1/experiments");
        if (!cancelled) setExperiments(history.items);
      } catch (cause) {
        if (!cancelled) setError(cause instanceof Error ? cause.message : "No se pudo actualizar la ejecución.");
      } finally { inFlight = false; }
    }, 1000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [active]);

  function toggleTheme() {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    document.documentElement.dataset.theme = nextTheme;
    try { localStorage.setItem("pal-theme", nextTheme); } catch { /* Optional persistence. */ }
  }

  async function refreshModels() {
    try { setModels((await apiRequest<{ items: ModelInfo[] }>("api/v1/models")).items); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo actualizar el registro de modelos."); }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting || active || !dataset || health !== "online" || (isRL && !chosenModel)) return;
    const fields = new FormData(event.currentTarget);
    const config: ExperimentConfig = {
      name: String(fields.get("name")).trim(), strategy, dataset_id: datasetId,
      initial_capital: isRL ? chosenModel.initial_capital : Number(fields.get("capital")), transaction_cost_bps: isRL ? chosenModel.transaction_cost_bps : Number(fields.get("costs")),
      risk_free_rate: isRL ? chosenModel.risk_free_rate : Number(fields.get("risk_free_rate")), seed: Number(fields.get("seed")),
      split: historical && !isRL ? String(fields.get("split")) as "train" | "validation" : "validation",
      lookback: isRL ? chosenModel.lookback : historical ? Number(fields.get("lookback")) : 60,
      ...(isRL ? { model_id: chosenModel.id } : {}),
      risk_aversion: historical && !isRL ? Number(fields.get("risk_aversion")) : 5,
    };
    setSubmitting(true);
    setError("");
    try {
      const experiment = await apiRequest<Experiment>("api/v1/experiments", { method: "POST", body: JSON.stringify(config) });
      setExperiments((current) => [experiment, ...current.filter((item) => item.id !== experiment.id)]);
      setSelectedId(experiment.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No fue posible crear el experimento.");
    } finally { setSubmitting(false); }
  }

  return <div className="app-shell">
    <a href="#main-content" className="skip-link">Saltar al contenido</a>
    <aside className="sidebar" aria-label="Navegación del laboratorio">
      <a href="#main-content" className="brand" aria-label="Portfolio AI Lab, inicio"><span className="brand-mark"><Layers3 aria-hidden="true" size={22} /></span><span>Portfolio <strong>AI Lab</strong><small>RESEARCH WORKSPACE</small></span></a>
      <div className="sidebar-label">ESPACIO DE INVESTIGACIÓN</div>
      <nav className="main-nav"><a href="#main-content" aria-current="page"><FlaskConical aria-hidden="true" />Laboratorio<span className="nav-dot" /></a><a href="#experiments"><Layers3 aria-hidden="true" />Experimentos</a><a href="#dataset"><Database aria-hidden="true" />Datos y fuentes</a><a href="#provenance"><Braces aria-hidden="true" />Trazabilidad</a><a href="#training"><Activity aria-hidden="true" />AI Research Lab</a><a href="#agent-desk"><ShieldCheck aria-hidden="true" />AI Agent Desk</a></nav>
      <div className="sidebar-note"><ShieldCheck aria-hidden="true" size={20} /><strong>Investigación, con límites.</strong><p>Entorno local. Sin conexión a brokers ni ejecución con dinero real.</p><Badge variant="secondary">PAPER ONLY</Badge></div>
      <div className="sidebar-footer"><span className="version-dot" />Prototipo · Etapa 4</div>
    </aside>

    <div className="workspace">
      <header className="context-bar"><div className="breadcrumb"><span>Workspace</span><ChevronRight size={14} aria-hidden="true" /><strong>Laboratorio</strong></div><div className="context-actions"><span className={`connection ${health}`}><span />{health === "loading" ? "Verificando API" : health === "online" ? "API preparada" : "API no disponible"}</span><span className="header-separator" /><Button variant="ghost" size="icon" onClick={toggleTheme} aria-label={`Activar tema ${theme === "dark" ? "claro" : "oscuro"}`} title="Cambiar tema">{theme === "dark" ? <Sun /> : <Moon />}</Button></div></header>
      <main id="main-content" className="main-content">
        <div className="page-heading"><div><div className="eyebrow"><span />PORTFOLIO AI LAB</div><h1>Una hipótesis. Un experimento.</h1><p>Explora estrategias, verifica supuestos y conserva la evidencia.</p></div><Button variant="outline" onClick={() => void refresh()} disabled={loading} aria-label="Actualizar laboratorio"><RefreshCw className={loading ? "spinner" : ""} />Actualizar</Button></div>

        <div className="disclosure"><div className="disclosure-icon"><FlaskConical size={20} aria-hidden="true" /></div><div><strong>{historical ? "Datos históricos reales · simulación PAPER" : dataset?.kind === "FIXTURE" ? "Fixture determinista · datos sintéticos de prueba" : "Datos históricos · fuente pendiente"}</strong><p>{historical ? "Precios ajustados del proveedor, con procedencia y control de calidad. La simulación usa señales rezagadas y costos; 2024 permanece reservado como prueba final." : dataset?.kind === "FIXTURE" ? "Modo de pruebas automatizadas. La fixture valida el software y no representa rendimientos históricos." : "Importa un snapshot histórico verificado para comenzar. No se fabrican precios ni se sustituyen descargas fallidas."}</p></div><Badge variant="warning">PAPER ONLY</Badge></div>

        {error && <div className="error-banner" role="alert"><TriangleAlert size={20} aria-hidden="true" /><div><strong>No pudimos completar la solicitud</strong><p>{error}</p></div><Button variant="outline" size="sm" onClick={() => void refresh()} disabled={loading}>Reintentar</Button></div>}

        <div className="research-layout">
          <section id="configure" aria-labelledby="configure-title">
            <Card className="configuration-card"><CardHeader><div className="section-kicker">01 / CONFIGURAR</div><CardTitle id="configure-title">Nuevo experimento</CardTitle><CardDescription>Una base simple para verificar el motor.</CardDescription></CardHeader><CardContent>
              <div className="strategy-selected"><span className="strategy-icon"><Layers3 size={20} aria-hidden="true" /></span><div><strong>{strategyNames[strategy]}</strong><span>{strategy === "markowitz" ? "Media-varianza · ventana móvil" : "Pesos iguales · rebalanceo diario"}</span></div><CheckCircle2 size={18} className="text-primary" aria-hidden="true" /></div>
              <form onSubmit={submit} className="experiment-form">
                <div className="field"><label htmlFor="dataset-choice">Origen de datos</label><select id="dataset-choice" value={datasetId} onChange={(event) => { setDatasetId(event.target.value); if (event.target.value === "fixture-v1") setStrategy("equal_weight"); }} disabled={loading || active || submitting}>{datasets.map((item) => <option key={item.id} value={item.id}>{item.kind === "FIXTURE" ? "FIXTURE · prueba sintética" : `HISTÓRICO · ${item.start_date.slice(0, 4)}–${item.end_date.slice(0, 4)} · ${item.sha256.slice(0, 8)}`}</option>)}</select></div>
                <div className="field"><label htmlFor="strategy-choice">Estrategia</label><select id="strategy-choice" value={strategy} onChange={(event) => setStrategy(event.target.value as ExperimentConfig["strategy"])} disabled={active || submitting}><option value="equal_weight">Equal weight</option><option value="markowitz" disabled={!historical}>Markowitz · histórico requerido</option><option value="ppo" disabled={!historical || !models.some(model => model.algorithm === "ppo" && model.dataset_id === datasetId)}>PPO · modelo entrenado</option><option value="ddpg" disabled={!historical || !models.some(model => model.algorithm === "ddpg" && model.dataset_id === datasetId)}>DDPG · modelo entrenado</option></select></div>
                {isRL && <div className="field"><label htmlFor="trained-model">Modelo entrenado</label><select id="trained-model" value={chosenModel?.id ?? ""} onChange={event => setModelId(event.target.value)}>{compatibleModels.map(model => <option value={model.id} key={model.id}>{model.algorithm.toUpperCase()} · seed {model.seed} · {model.timesteps} pasos · hasta {model.training_end}</option>)}</select><small>Capital, costos y ventana se mantienen según el modelo. Consulta su configuración en Research Lab.</small></div>}
                {historical ? <div className="historical-config"><div className="field"><label htmlFor="split">Partición de evaluación</label><select key={strategy} name="split" id="split" defaultValue="validation" disabled={isRL}><option value="train">Entrenamiento · 2015–2021</option><option value="validation">Validación · 2022–2023</option></select><small>Prueba final 2024 bloqueada. No se usa para elegir parámetros.</small></div><div className="field-row"><div className="field"><label htmlFor="lookback">Ventana histórica</label><Input key={`lookback-${chosenModel?.id ?? "custom"}`} disabled={isRL} name="lookback" id="lookback" type="number" min="2" max="252" step="1" defaultValue={isRL ? chosenModel?.lookback ?? 60 : 60} required /></div><div className="field"><label htmlFor="risk-aversion">Aversión al riesgo</label><Input disabled={isRL} name="risk_aversion" id="risk-aversion" type="number" min="0.001" max="10000" step="0.001" defaultValue="5" required /></div></div><small>Ventana común a ambas estrategias; señal hasta t−1, rebalanceo en t.</small></div> : dataset?.kind === "FIXTURE" ? <p className="form-footnote">Modo de pruebas automatizadas: datos sintéticos separados de la investigación.</p> : null}
                {!datasets.some((item) => item.kind === "HISTORICAL") && !loading && <p className="form-footnote">No hay snapshots históricos verificados. Ejecuta el pipeline documentado en el RUNBOOK; no se sustituyen descargas fallidas.</p>}
                <div className="field"><label htmlFor="experiment-name">Nombre del experimento</label><Input id="experiment-name" name="name" defaultValue="Prueba equal-weight" required minLength={1} maxLength={80} placeholder="Ej. Verificación de costos" /></div>
                <div className="field"><label htmlFor="capital">Capital inicial <span>USD simulados</span></label><Input key={`capital-${chosenModel?.id ?? "custom"}`} disabled={isRL} id="capital" name="capital" type="number" min="0.01" max="1000000000" step="0.01" defaultValue={isRL ? chosenModel?.initial_capital ?? 10000 : 10000} required /></div>
                <div className="field-row"><div className="field"><label htmlFor="costs">Costos de transacción</label><div className="unit-input"><Input key={`costs-${chosenModel?.id ?? "custom"}`} disabled={isRL} id="costs" name="costs" type="number" min="0" max="100" step="0.01" defaultValue={isRL ? chosenModel?.transaction_cost_bps ?? 10 : 10} required /><span>bps</span></div></div><div className="field"><label htmlFor="seed">Semilla aleatoria</label><Input id="seed" name="seed" type="number" min="0" max="2147483647" step="1" defaultValue="42" required /></div></div>
                <div className="field"><label htmlFor="risk-free">Tasa libre de riesgo <span>Anual efectiva</span></label><Input key={`rf-${chosenModel?.id ?? "custom"}`} disabled={isRL} id="risk-free" name="risk_free_rate" type="number" min="-0.99" max="1" step="0.001" defaultValue={isRL ? chosenModel?.risk_free_rate ?? 0 : 0} required aria-describedby="risk-free-help" /><small id="risk-free-help">Fracción anual: 0,05 equivale a 5 %. 1 bp = 0,01 %.</small></div>
                <div className="config-note"><ShieldCheck size={15} aria-hidden="true" /><span>Long-only · sin apalancamiento · costos incluidos</span></div>
                <Button type="submit" className="w-full" disabled={loading || submitting || active || !dataset || health !== "online" || (isRL && !chosenModel)}>{submitting || active ? <LoaderCircle className="spinner" /> : <Play />} {submitting ? "Creando experimento…" : active ? "Ejecución en curso…" : "Ejecutar prueba"}{!submitting && !active && <ArrowRight className="ml-auto" />}</Button>
                <p className="form-footnote">Se guardan la configuración, los resultados y el manifiesto de cada ejecución.</p>
              </form>
            </CardContent></Card>
            <DatasetCard dataset={dataset} loading={loading} />
          </section>

          <section id="results" aria-labelledby="results-title" className="results-column">
            <div className="section-heading"><div><div className="section-kicker">02 / OBSERVAR</div><h2 id="results-title">Resultados del experimento</h2></div>{selected && <div data-testid="run-status"><RunBadge status={selected.status} /></div>}</div>
            <div className="run-selector"><label htmlFor="run-select">Ejecución guardada</label><select id="run-select" value={selectedId} onChange={(event) => setSelectedId(event.target.value)} disabled={!experiments.length}><option value="" disabled>{loading ? "Cargando ejecuciones…" : "Sin ejecuciones guardadas"}</option>{experiments.map((experiment) => <option value={experiment.id} key={experiment.id}>{experiment.name} · {statusLabels[experiment.status]} · {experiment.id.slice(0, 8)}</option>)}</select></div>
            <div aria-live="polite" className="sr-only">{submitting ? "Creando experimento" : selected ? `${selected.name}: ${statusLabels[selected.status]}` : loading ? "Cargando laboratorio" : "Sin experimentos seleccionados"}</div>
            {loading && !selected ? <Card className="empty-state"><LoaderCircle className="spinner" size={28} aria-hidden="true" /><h3>Conectando con el laboratorio</h3><p>Consultando datasets y ejecuciones persistidas.</p></Card> : selected?.result ? <RunResults result={selected.result} experiment={selected} /> : selected?.status === "failed" ? <Card className="empty-state"><TriangleAlert size={28} className="text-destructive" aria-hidden="true" /><h3>El experimento no se completó</h3><p>{selected.error ?? "Consulta el servicio local para revisar el error."}</p><p>Esta ejecución permanece guardada para mantener la trazabilidad.</p></Card> : selected && isActive(selected) ? <Card className="empty-state"><LoaderCircle className="spinner text-primary" size={28} aria-hidden="true" /><h3>{selected.status === "queued" ? "Experimento en cola" : "Calculando el experimento"}</h3><p>El worker está procesando la configuración. Los resultados aparecerán al finalizar.</p><code>{selected.id}</code></Card> : <Card className="empty-state"><div className="empty-illustration" aria-hidden="true"><Activity size={36} /></div><Badge variant="secondary">TU PRIMER PUNTO DE PARTIDA</Badge><h3>La evidencia comienza con una prueba.</h3><p>Configura un experimento y ejecuta la estrategia equal-weight. Aquí verás el capital, el riesgo y los costos calculados por el motor.</p><div className="empty-steps"><span><CheckCircle2 size={15} />Configura</span><ArrowRight size={14} /><span><Play size={15} />Ejecuta</span><ArrowRight size={14} /><span><Activity size={15} />Verifica</span></div></Card>}
            {!selected?.result && <div id="provenance" className="traceability-note"><Braces size={17} aria-hidden="true" /><p>El manifiesto, la configuración y los eventos del motor estarán disponibles aquí al completar una ejecución.</p></div>}
          </section>
        </div>

        <section id="experiments" className="history-section" aria-labelledby="history-title"><div className="section-heading"><div><div className="section-kicker">REGISTRO LOCAL</div><h2 id="history-title">Experimentos guardados</h2></div><span className="muted text-sm">{experiments.length} {experiments.length === 1 ? "ejecución" : "ejecuciones"}</span></div><Card>{experiments.length ? <div className="table-scroll" role="region" aria-label="Historial de experimentos" tabIndex={0}><table><thead><tr><th>Experimento</th><th>Creado · Bogotá</th><th>Estado</th><th className="numeric">Capital final</th><th><span className="sr-only">Acciones</span></th></tr></thead><tbody>{experiments.map((experiment) => <tr key={experiment.id}><td><strong>{experiment.name}</strong><small className="history-source">{experiment.dataset.kind} · {strategyNames[experiment.config.strategy]}</small><small className="run-id">{experiment.id.slice(0, 12)}</small></td><td>{dateTime(experiment.created_at)}</td><td><RunBadge status={experiment.status} /></td><td className="numeric">{experiment.result ? money(experiment.result.metrics.final_equity) : "—"}</td><td><Button variant="ghost" size="sm" onClick={() => { setSelectedId(experiment.id); document.getElementById("results")?.scrollIntoView({ block: "start" }); }} aria-label={`Ver ${experiment.name}`}>Ver<ArrowUpRight /></Button></td></tr>)}</tbody></table></div> : <div className="history-empty"><TerminalSquare size={22} aria-hidden="true" /><p>{loading ? "Cargando registro local…" : "Tus experimentos aparecerán aquí cuando ejecutes la primera prueba."}</p></div>}</Card></section>
        <TrainingLab datasets={datasets} onModelsChanged={() => void refreshModels()} />
        <AgentDesk datasets={datasets} models={models} />
        <footer className="page-footer"><span>Portfolio AI Lab <span className="footer-dot">/</span> Investigación reproducible</span><span><CircleHelp size={14} aria-hidden="true" />Etapa 4 · Simulación sin ejecución real</span></footer>
      </main>
    </div>
  </div>;
}

function DatasetCard({ dataset, loading }: { dataset?: Dataset; loading: boolean }) {
  return <Card className="dataset-card" id="dataset"><CardHeader><div className="dataset-title"><Database size={17} aria-hidden="true" /><CardTitle>Datos y procedencia</CardTitle><Badge variant="warning">{dataset?.kind ?? "PENDIENTE"}</Badge></div></CardHeader><CardContent>{dataset ? <><div className="dataset-summary"><strong>{dataset.observations}</strong><span>observaciones · {dataset.assets.length} {dataset.kind === "FIXTURE" ? "activos ficticios" : "instrumentos"}</span></div><p className="dataset-period">{dataset.start_date} <ArrowRight size={12} aria-hidden="true" /> {dataset.end_date}</p><div className="asset-chips">{dataset.assets.map((asset) => <span key={asset}>{asset}</span>)}</div><p className="dataset-source">{dataset.source}</p><details><summary>Ver huella SHA-256</summary><code className="hash">{dataset.sha256}</code></details>{dataset.kind === "HISTORICAL" && <details><summary>Calidad, particiones y limitaciones</summary><pre className="quality-json">{JSON.stringify({ quality: dataset.quality_report, splits: dataset.splits, provenance: dataset.provenance }, null, 2)}</pre></details>}</> : <p className="muted text-sm">{loading ? "Consultando datos disponibles…" : "Datos no disponibles. Comprueba la conexión con la API."}</p>}</CardContent></Card>;
}

function RunResults({ result, experiment }: { result: Result; experiment: Experiment }) {
  const metrics = result.metrics;
  const assetNames = experiment.dataset.assets;
  return <>
    <div className="result-provenance" data-testid="result-provenance"><Badge variant="warning" data-testid="run-data-kind">{experiment.dataset.kind}</Badge><span>{strategyNames[experiment.config.strategy]} · {experiment.dataset.kind === "HISTORICAL" ? `${experiment.config.split ?? "validation"} · datos históricos reales` : "datos sintéticos de prueba"}</span><small>{experiment.dataset.source}</small></div>
    <div className="metrics-grid">
      <Metric label="Retorno acumulado" value={percent(metrics.cumulative_return)} hint="Neto de costos" direction={metrics.cumulative_return >= 0 ? "up" : "down"} />
      <Metric label="Volatilidad anual" value={metrics.annualized_volatility === null ? "No definido" : percent(metrics.annualized_volatility)} hint="252 días · muestra ddof = 1" />
      <Metric label="Ratio de Sharpe" value={metrics.sharpe_ratio === null ? "No definido" : decimal(metrics.sharpe_ratio)} hint="Tasa libre de riesgo configurada" />
      <Metric label="Máximo drawdown" value={percent(metrics.max_drawdown)} hint="Magnitud de la caída desde el pico" direction="down" />
    </div>
    <Card className="chart-card"><CardHeader><div className="chart-heading"><div><CardTitle>Curva de capital</CardTitle><CardDescription>Capital simulado en USD · neto de costos</CardDescription></div><Badge variant="secondary"><span className="legend-dot" />{strategyNames[experiment.config.strategy]}</Badge></div><div className="capital-summary"><strong data-testid="metric-final-equity" data-value={metrics.final_equity}>{money(metrics.final_equity)}</strong><span>Costos totales <b>{money(metrics.total_costs)}</b></span></div></CardHeader><CardContent><EquityChart points={result.equity} /><details className="data-details"><summary>Ver datos de la curva</summary><div className="table-scroll" role="region" aria-label="Valores de la curva de capital" tabIndex={0}><table><thead><tr><th>Fecha</th><th className="numeric">Capital · USD</th><th className="numeric">Retorno neto</th></tr></thead><tbody>{result.equity.map((point) => <tr key={point.date}><td>{point.date}</td><td className="numeric">{money(point.equity)}</td><td className="numeric">{percent(point.net_return)}</td></tr>)}</tbody></table></div></details></CardContent></Card>
    <Card><CardHeader><CardTitle>Asignaciones y costos</CardTitle><CardDescription>Pesos objetivo y rotación de cada rebalanceo.</CardDescription></CardHeader><CardContent><div className="table-scroll" role="region" aria-label="Asignaciones del experimento" tabIndex={0}><table><thead><tr><th>Fecha</th>{assetNames.map((asset) => <th className="numeric" key={asset}>{asset}</th>)}<th className="numeric">Rotación L1</th><th className="numeric">Costo · USD</th></tr></thead><tbody>{result.allocations.map((allocation) => <tr key={allocation.date}><td>{allocation.date}</td>{assetNames.map((asset) => <td className="numeric" key={asset}>{allocation.weights[asset] === undefined ? "—" : percent(allocation.weights[asset])}</td>)}<td className="numeric">{percent(allocation.turnover)}</td><td className="numeric">{money(allocation.cost)}</td></tr>)}</tbody></table></div></CardContent></Card>
    <Card id="provenance"><CardHeader><div className="section-kicker">03 / VERIFICAR</div><CardTitle>Trazabilidad de la ejecución</CardTitle><CardDescription>Eventos del motor y manifiesto reproducible, sin valores generados por la interfaz.</CardDescription></CardHeader><CardContent><div className="audit-list">{result.audit.map((event, i) => <div className="audit-event" key={`${event.date}-${i}`}><span className="audit-dot" /><div><div><code>{event.event}</code><time>{event.date}</time></div><p>{event.detail}</p></div></div>)}</div><details className="manifest"><summary><Braces size={16} aria-hidden="true" />Ver manifiesto y configuración</summary><p className="manifest-id">Run ID: {experiment.id}</p><pre>{JSON.stringify({ config: experiment.config, dataset: experiment.dataset, manifest: result.manifest }, null, 2)}</pre></details></CardContent></Card>
  </>;
}

function Metric({ label, value, hint, direction }: { label: string; value: string; hint: string; direction?: "up" | "down" }) {
  return <Card className="metric-card"><div className="metric-label">{label}</div><div className={`metric-value ${direction === "up" ? "positive" : direction === "down" ? "negative" : ""}`}>{value}{direction === "up" ? <ArrowUpRight size={18} aria-hidden="true" /> : direction === "down" ? <ArrowDownRight size={18} aria-hidden="true" /> : null}</div><p>{hint}</p></Card>;
}
