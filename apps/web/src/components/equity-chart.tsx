"use client";

import { useEffect, useRef, useState } from "react";
import type { Result } from "@/lib/contracts";

const money = (n: number) => new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 }).format(n);
export function EquityChart({ points }: { points: Result["equity"] }) {
  const frame = useRef<HTMLDivElement>(null);
  const [frameWidth, setFrameWidth] = useState(860);
  useEffect(() => {
    if (!frame.current) return;
    const observer = new ResizeObserver(([entry]) => {
      if (entry.contentRect.width > 0) setFrameWidth(Math.floor(entry.contentRect.width));
    });
    observer.observe(frame.current);
    return () => observer.disconnect();
  }, []);
  if (!points.length) return <p className="empty-copy">Este resultado no tiene puntos de capital.</p>;
  const width = Math.max(frameWidth, 240), height = width < 500 ? 240 : 300;
  const left = width < 500 ? 64 : 80, right = 20, top = 24, bottom = 44;
  const values = points.map((point) => point.equity);
  const rawMin = Math.min(...values), rawMax = Math.max(...values);
  const margin = Math.max((rawMax - rawMin) * 0.18, rawMax * 0.003, 1);
  const min = rawMin - margin, max = rawMax + margin;
  const x = (i: number) => left + i / Math.max(points.length - 1, 1) * (width - left - right);
  const y = (value: number) => top + (max - value) / (max - min) * (height - top - bottom);
  const line = points.map((point, i) => `${x(i)},${y(point.equity)}`).join(" ");
  const area = `${left},${height - bottom} ${line} ${x(points.length - 1)},${height - bottom}`;
  const dateIndices = [...new Set(width < 500 ? [0, points.length - 1] : [0, Math.floor((points.length - 1) / 2), points.length - 1])];
  return <div ref={frame} className="equity-chart-frame"><svg data-testid="equity-chart" style={{ height }} viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby="equity-title equity-description" className="equity-chart">
    <title id="equity-title">Evolución del capital simulado en USD</title>
    <desc id="equity-description">{points.length} observaciones, del {points[0].date} al {points[points.length - 1].date}. Capital inicial {money(points[0].equity)}, final {money(points[points.length - 1].equity)} USD. Datos completos en la tabla siguiente.</desc>
    <defs><linearGradient id="equity-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--primary)" stopOpacity="0.17" /><stop offset="100%" stopColor="var(--primary)" stopOpacity="0" /></linearGradient></defs>
    {[0, 1, 2, 3].map((tick) => {
      const value = min + (max - min) * tick / 3;
      return <g key={tick}><line x1={left} x2={width - right} y1={y(value)} y2={y(value)} stroke="var(--border)" strokeDasharray="3 5" /><text x={left - 12} y={y(value) + 4} textAnchor="end" fill="var(--muted-foreground)" fontSize="12">{money(value)}</text></g>;
    })}
    <polygon points={area} fill="url(#equity-fill)" />
    <polyline points={line} fill="none" stroke="var(--primary)" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
    {points.map((point, i) => points.length <= 60 || i === points.length - 1 ? <circle key={point.date} cx={x(i)} cy={y(point.equity)} r="3" fill="var(--card)" stroke="var(--primary)" strokeWidth="2"><title>{point.date}: {money(point.equity)} USD</title></circle> : null)}
    {dateIndices.map((i) => <text key={i} x={x(i)} y={height - 14} textAnchor={i === 0 ? "start" : i === points.length - 1 ? "end" : "middle"} fill="var(--muted-foreground)" fontSize="12">{points[i].date}</text>)}
  </svg></div>;
}
