"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { BrainCircuit, Play, RefreshCw, Square, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { EquityChart } from "@/components/equity-chart";
import { apiRequest } from "@/lib/api";
import type { ComparisonReport, Dataset, Result, TrainingJob, TrainingRequest } from "@/lib/contracts";

const statusText = { pending: "Pendiente", running: "Entrenando", completed: "Completado", failed: "Fallido", cancelled: "Cancelado" };
const pct = (value: number) => `${(value * 100).toFixed(2)} %`;
const number = (value: number | null | undefined, digits = 4) => value === null || value === undefined ? "No definido" : value.toFixed(digits);
const active = (job: TrainingJob) => job.status === "pending" || job.status === "running";

export function TrainingLab({ datasets, onModelsChanged }: { datasets: Dataset[]; onModelsChanged: () => void }) {
  const [jobs, setJobs] = useState<TrainingJob[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [algorithm, setAlgorithm] = useState<"ppo" | "ddpg">("ppo");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [comparison, setComparison] = useState<ComparisonReport | null>(null);
  const dataset = datasets.find(item => item.kind === "HISTORICAL");
  const selected = jobs.find(job => job.id === selectedId);
  const hasActive = jobs.some(active);
  const refresh = useCallback(async () => {
    try {
      const data = await apiRequest<{ items: TrainingJob[] }>("api/v1/training");
      setJobs(data.items);
      setSelectedId(current => data.items.some(job => job.id === current) ? current : data.items[0]?.id ?? "");
      setError("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo consultar Research Lab."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => {
    const timer = window.setTimeout(() => { void refresh(); }, 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);
  useEffect(() => {
    if (!hasActive) return;
    const timer = window.setInterval(() => { void refresh(); }, 1500);
    return () => window.clearInterval(timer);
  }, [hasActive, refresh]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!dataset) return;
    const form = new FormData(event.currentTarget);
    const width = Number(form.get("width"));
    const steps = Number(form.get("timesteps"));
    const rate = Number(form.get("learning_rate"));
    const request: TrainingRequest = {
      name: String(form.get("training_name")).trim(), algorithm, dataset_id: dataset.id,
      seed: Number(form.get("training_seed")), total_timesteps: steps,
      lookback: 60, initial_capital: 10000, transaction_cost_bps: 10, risk_free_rate: 0,
      training_end: "2021-12-31", reward_mode: "log_return", risk_penalty: 0,
      normalize_observations: true, net_arch: [width, width],
      checkpoint_frequency: Math.max(256, Math.ceil(steps / 4 / 256) * 256),
      max_seconds: 600, max_memory_mb: 2048,
      ppo: { learning_rate: rate, n_steps: 256, batch_size: 64, n_epochs: 5, gamma: 0.99,
        gae_lambda: 0.95, clip_range: 0.2, ent_coef: 0, vf_coef: 0.5, max_grad_norm: 0.5 },
      ddpg: { learning_rate: rate, buffer_size: 20000, batch_size: 64, gamma: 0.99,
        tau: 0.005, train_freq: 1, gradient_steps: 1, learning_starts: 32, noise_sigma: 0.1 },
    };
    setBusy(true); setError(""); setComparison(null);
    try {
      const job = await apiRequest<TrainingJob>("api/v1/training", { method: "POST", body: JSON.stringify(request) });
      setJobs(current => [job, ...current]); setSelectedId(job.id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo iniciar el entrenamiento."); }
    finally { setBusy(false); }
  }

  async function action(kind: "cancel" | "evaluate" | "compare" | "resume") {
    if (!selected) return;
    setBusy(true); setError("");
    try {
      if (kind === "resume") {
        const request = { ...selected.config, name: `Resume ${selected.id.slice(0, 8)}`,
          resume_from_job_id: selected.id };
        const job = await apiRequest<TrainingJob>("api/v1/training", { method: "POST", body: JSON.stringify(request) });
        setSelectedId(job.id);
      } else {
        const response = await apiRequest<Result | ComparisonReport | TrainingJob>(`api/v1/training/${selected.id}/${kind}`, {
          method: "POST", body: "{}", signal: AbortSignal.timeout(90_000),
        });
        if (kind === "compare") setComparison(response as ComparisonReport);
      }
      await refresh(); onModelsChanged();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "La operación no se completó."); }
    finally { setBusy(false); }
  }

  const progress = selected?.progress ?? {};
  const fraction = typeof progress.progress === "number" ? progress.progress : selected?.status === "completed" ? 1 : 0;
  const losses = (progress.learning_metrics ?? selected?.manifest?.learning_metrics ?? {}) as Record<string, number>;
  const evaluation = selected?.evaluation as Result | null | undefined;
  return <section id="training" className="training-lab" aria-labelledby="training-title">
    <div className="section-heading"><div><div className="section-kicker">APRENDIZAJE POR REFUERZO</div><h2 id="training-title"><BrainCircuit size={20} aria-hidden="true" />AI Research Lab</h2></div><Button variant="outline" onClick={() => { void refresh(); onModelsChanged(); }} aria-label="Actualizar entrenamientos"><RefreshCw />Actualizar</Button></div>
    <div className="training-disclosure"><ShieldCheck size={18} aria-hidden="true" /><p>PPO / DDPG con PyTorch y SB3 en CPU. Entrenamiento 2015–2021; validación independiente 2022–2023. <strong>2024 bloqueado.</strong> Los valores iniciales son supuestos de investigación, no parámetros óptimos.</p></div>
    {error && <div className="error-banner" role="alert"><p>Research Lab: {error}</p><Button variant="outline" onClick={() => void refresh()}>Reintentar Research Lab</Button></div>}
    <div className="training-grid">
      <Card><CardHeader><CardTitle>Configurar entrenamiento</CardTitle></CardHeader><CardContent><form className="experiment-form" onSubmit={submit}>
        <div className="field"><label htmlFor="training-algorithm">Algoritmo de entrenamiento</label><select id="training-algorithm" value={algorithm} onChange={event => setAlgorithm(event.target.value as "ppo" | "ddpg")}><option value="ppo">PPO · política proximal</option><option value="ddpg">DDPG · actor y crítico</option></select></div>
        <div className="field"><label htmlFor="training-name">Nombre del entrenamiento</label><Input id="training-name" name="training_name" defaultValue="Investigación inicial" required maxLength={80} /></div>
        <div className="field-row"><div className="field"><label htmlFor="training-timesteps">Pasos de entrenamiento</label><Input id="training-timesteps" name="timesteps" type="number" min="256" max="65536" step="256" defaultValue="1024" required /></div><div className="field"><label htmlFor="training-seed">Semilla del entrenamiento</label><Input id="training-seed" name="training_seed" type="number" min="0" max="2147483647" step="1" defaultValue="42" required /></div></div>
        <div className="field"><label htmlFor="training-rate">Learning rate</label><Input key={algorithm} id="training-rate" name="learning_rate" type="number" min="0.000001" max="0.01" step="0.000001" defaultValue={algorithm === "ppo" ? "0.0003" : "0.001"} required /></div>
        <div className="field"><label htmlFor="training-width">Arquitectura · dos capas</label><select id="training-width" name="width" defaultValue="64"><option value="32">32 + 32</option><option value="64">64 + 64</option><option value="128">128 + 128</option></select></div>
        <p className="form-footnote">Ventana 60 · capital 10.000 USD · costos 10 bps · normalización ajustada solo en entrenamiento. Un proceso a la vez, máximo 600 s y 2 GiB por trabajo.</p>
        <p className="form-footnote">{dataset ? `Snapshot ${dataset.sha256.slice(0, 12)} · ${dataset.observations} sesiones verificadas.` : "Importa históricos reales para habilitar el entrenamiento."}</p>
        <Button type="submit" disabled={!dataset || busy}><Play />Entrenar modelo</Button>
      </form></CardContent></Card>
      <Card><CardHeader><CardTitle>Seguimiento del experimento</CardTitle></CardHeader><CardContent>
        <div className="field"><label htmlFor="training-select">Entrenamiento guardado</label><select id="training-select" value={selectedId} onChange={event => { setSelectedId(event.target.value); setComparison(null); }} disabled={!jobs.length}><option value="" disabled>{loading ? "Cargando…" : "Sin entrenamientos"}</option>{jobs.map(job => <option key={job.id} value={job.id}>{job.config.name} · {job.config.algorithm.toUpperCase()} · {statusText[job.status]}</option>)}</select></div>
        {selected ? <div className="training-details"><div className="section-heading"><strong>{selected.config.name}</strong><Badge data-testid="training-status" variant={selected.status === "failed" ? "destructive" : "default"}>{statusText[selected.status]}</Badge></div><progress aria-label="Progreso del entrenamiento" value={fraction} max={1} /><p aria-live="polite">{Math.round(fraction * 100)} % · {String(progress.timesteps ?? selected.manifest?.actual_timesteps ?? 0)} pasos</p><p className="muted text-sm">Tiempo {number(typeof progress.elapsed_seconds === "number" ? progress.elapsed_seconds : null, 1)} s · pico RSS {number(typeof progress.peak_rss_mb === "number" ? progress.peak_rss_mb : null, 1)} MiB</p>
          {selected.error && <p role="alert" className="text-destructive">{selected.error}</p>}
          {Object.keys(losses).length > 0 && <div className="learning-metrics">{Object.entries(losses).slice(0, 6).map(([key, value]) => <div key={key}><span>{key}</span><strong>{number(value)}</strong></div>)}</div>}
          <div className="training-actions"><Button variant="outline" onClick={() => void action("cancel")} disabled={busy || !active(selected)}><Square />Cancelar entrenamiento</Button><Button onClick={() => void action("evaluate")} disabled={busy || selected.status !== "completed"}>Evaluar validación</Button><Button variant="outline" onClick={() => void action("compare")} disabled={busy || selected.status !== "completed"}>Comparar estrategias</Button><Button variant="outline" onClick={() => void action("resume")} disabled={busy || active(selected)}>Reanudar checkpoint</Button></div>
          {evaluation && <div className="training-evaluation" data-testid="training-evaluation"><h3>Validación 2022–2023</h3><div className="metrics-grid"><div><span>Retorno neto</span><strong>{pct(evaluation.metrics.cumulative_return)}</strong></div><div><span>Sharpe</span><strong>{number(evaluation.metrics.sharpe_ratio)}</strong></div><div><span>Volatilidad</span><strong>{evaluation.metrics.annualized_volatility === null ? "No definido" : pct(evaluation.metrics.annualized_volatility)}</strong></div><div><span>Drawdown máximo</span><strong>{pct(evaluation.metrics.max_drawdown)}</strong></div></div><EquityChart points={evaluation.equity} /><details><summary>Asignaciones y métricas adicionales</summary><pre className="quality-json">{JSON.stringify({ research: evaluation.manifest.research_metrics, last_allocations: evaluation.allocations.slice(-10) }, null, 2)}</pre></details></div>}
          <details><summary>Configuración, checkpoints y manifiesto</summary><pre className="quality-json">{JSON.stringify({ id: selected.id, config: selected.config, manifest: selected.manifest }, null, 2)}</pre></details>
        </div> : <div className="history-empty"><p>Los modelos, pérdidas y checkpoints aparecerán después de ejecutar un entrenamiento real.</p></div>}
      </CardContent></Card>
    </div>
    {comparison && <Card className="comparison-card"><CardHeader><CardTitle>Comparación de estrategias · validación</CardTitle><p className="muted text-sm">{comparison.methodology}</p></CardHeader><CardContent><div className="table-scroll" role="region" aria-label="Comparación de estrategias entrenadas" tabIndex={0}><table><thead><tr><th>Estrategia</th><th>Semilla</th><th>Pasos</th><th>Retorno neto</th><th>Sharpe</th><th>Volatilidad</th><th>Drawdown</th><th>Costos USD</th></tr></thead><tbody>{comparison.items.map((item, index) => <tr key={item.model_id ?? `${item.algorithm}-${index}`}><td>{item.algorithm.toUpperCase()}</td><td>{item.seed ?? "—"}</td><td>{item.timesteps ?? "—"}</td><td>{pct(item.metrics.cumulative_return)}</td><td>{number(item.metrics.sharpe_ratio)}</td><td>{item.metrics.annualized_volatility === null ? "No definido" : pct(item.metrics.annualized_volatility)}</td><td>{pct(item.metrics.max_drawdown)}</td><td>{item.metrics.total_costs.toFixed(2)}</td></tr>)}</tbody></table></div></CardContent></Card>}
    <div className="training-history"><h3>Registro de entrenamientos · {jobs.length}</h3><div className="table-scroll" tabIndex={0} role="region" aria-label="Historial de entrenamientos"><table><thead><tr><th>Experimento</th><th>Algoritmo</th><th>Semilla</th><th>Estado</th><th>Entrena hasta</th><th>Acción</th></tr></thead><tbody>{jobs.map(job => <tr key={job.id}><td>{job.config.name}</td><td>{job.config.algorithm.toUpperCase()}</td><td>{job.config.seed}</td><td>{statusText[job.status]}</td><td>{job.config.training_end}</td><td><Button variant="ghost" onClick={() => setSelectedId(job.id)} aria-label={`Abrir entrenamiento ${job.config.name}`}>Abrir</Button></td></tr>)}</tbody></table></div></div>
  </section>;
}
