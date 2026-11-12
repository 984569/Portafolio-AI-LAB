# Portfolio AI Lab

Plataforma local de investigación de portafolios. **PAPER ONLY · sin dinero real.**
La Etapa 2 incorpora históricos reales de los diez instrumentos académicos,
snapshots Parquet, equal-weight, Markowitz y un entorno Gymnasium compatible
con SB3. La fixture sintética se conserva separada para verificar software.
PPO y DDPG tienen entrenamiento y validación histórica reproducibles. AI Agent
Desk añade propuestas exploratorias con un analista, un Judge y controles
determinísticos. OpenRouter es opcional y se configura en el backend.

## Requisitos y puesta en marcha (PowerShell)

Python 3.11, uv, Node compatible con Next.js y pnpm 10.28.2.
El Node global auditado es 25.2.1. En Windows usamos Node24.22.2 local,
descargado de nodejs.org y verificado con SHA256, sin cambiar PATH global.

```powershell
uv sync --python 3.11 --frozen
./scripts/setup_node.ps1
./scripts/web.ps1 install --frozen-lockfile
uv run --python 3.11 python scripts/download_history.py
```

Dos terminales desde la raíz:

```powershell
uv run --python 3.11 python scripts/run_api.py
```

```powershell
./scripts/web.ps1 dev
```

Abre `http://localhost:3000/dashboard`; API en `http://127.0.0.1:8000`,
OpenAPI interactivo en `http://127.0.0.1:8000/docs`. El motor cuantitativo
funciona sin claves ni Docker. Para activar Agent Desk, copia `.env.example`
a `.env` si todavía no tienes uno, agrega una clave propia al archivo local y
arranca el backend con `uv run --python 3.11 --env-file .env python scripts/run_api.py`.
Consulta el [runbook](docs/RUNBOOK.md) para la configuración y la ruta verificada.

## Uso y arquitectura

1. En **Dashboard**, selecciona el snapshot histórico y ejecuta un backtest
   equiponderado o Markowitz en validación 2022–2023. La API encola el trabajo
   en SQLite y el tablero muestra el resultado guardado.
2. En **AI Research Lab**, consulta los trabajos y las evaluaciones de PPO y
   DDPG. Una copia nueva necesita entrenar sus propios modelos o recibir
   artefactos verificados. El [protocolo de entrenamiento](docs/RL-RESEARCH.md)
   explica el estudio y la reproducibilidad.
3. En **AI Agent Desk**, inspecciona la propuesta hipotética, el veredicto y los
   controles de riesgo. El escritorio es exploratorio y el modo PAPER se
   aplica en el backend. El sistema carece de un canal de órdenes.

Next.js sirve la interfaz y reenvía rutas permitidas a FastAPI. Los trabajadores
separan el entrenamiento, el backtesting y Agent Desk. El motor cuantitativo
comparte contabilidad entre Gymnasium y los benchmarks. SQLite conserva el
historial y los manifiestos identifican datasets y checkpoints.
[Arquitectura](docs/architecture.md)

Los históricos descargados, modelos, checkpoints, credenciales y bases locales
quedan fuera de Git. El comando de descarga reconstruye el snapshot desde la
fuente disponible. Para reproducir exactamente un resultado publicado, coteja
su hash con el del estudio y usa los artefactos correspondientes. Las tablas
de resultados y los registros de pruebas sí se versionan. El acceso a
artefactos de una ejecución debe gestionarse por separado.

## Verificación

```powershell
uv run pytest
uv run ruff check .
uv run mypy
uv run python scripts/validate_stage2.py
./scripts/web.ps1 contracts
./scripts/web.ps1 typecheck
./scripts/web.ps1 lint
./scripts/web.ps1 build
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) '.runtime/browsers'
./scripts/web.ps1 exec playwright install chromium
./scripts/web.ps1 test:e2e
./scripts/web.ps1 test:e2e:historical
./scripts/web.ps1 exec playwright test --config playwright.training.config.ts
./scripts/web.ps1 exec playwright test --config playwright.agent-desk.config.ts
```

Las pruebas E2E inician servicios locales de producción en puertos propios.
Las suites históricas requieren el snapshot real. Agent Desk inyecta un
proveedor de prueba explícito. Consulta [estado](docs/STATUS.md),
[arquitectura](docs/architecture.md), [plan](docs/development-plan.md),
[diseño](DESIGN.md) y [evidencias UNAD](docs/UNAD-PHASE4-EVIDENCE.md).

## Estructura

- `apps/web`: Next.js, Tailwind y componentes shadcn/ui.
- `apps/api`: FastAPI, validación, persistencia y worker local acotado.
- `packages/portfolio_quant`: fixture, contabilidad y métricas independientes.
- `packages/market_data`: descarga pública, validación, Parquet y trazabilidad.
- `packages/portfolio_core`: panel tipado y contabilidad autofinanciada exacta.
- `packages/portfolio_research`: benchmarks históricos sin acceso futuro.
- `packages/portfolio_env`: entorno Gymnasium probado con SB3.
- `packages/portfolio_rl` y `packages/portfolio_evaluation`: entrenamiento,
  checkpoints, inferencia y evaluación cronológica.
- `packages/agent_desk`: contratos, proveedor, agentes y controles de riesgo.
- `packages/contracts`: OpenAPI y tipos TypeScript generados.
- `tests`: pruebas cuantitativas, API y navegador.
- `docs`, `scripts`: decisiones, evidencia y comandos reproducibles.

Los históricos se descargaron realmente y los benchmarks se verificaron en
2022–2023. 2024 sigue bloqueado. Agent Desk se verificó con datos reales,
respuestas de prueba etiquetadas e inferencia autenticada de Analyst y Judge
mediante una ruta gratuita fija de OpenRouter. 

Si el proveedor falla, el pipeline termina con error y conserva el diagnóstico;
no crea históricos sintéticos. Los precios descargados permanecen en `.runtime/`
fuera de Git. Consulta [el runbook](docs/RUNBOOK.md) y el
[reporte de validación histórica](docs/evidence/stage2/historical-validation.json).

Referencias técnicas oficiales consultadas:
[Next.js](https://nextjs.org/docs/app/getting-started/installation),
[Tailwind](https://tailwindcss.com/docs/installation/framework-guides/nextjs),
[shadcn/ui](https://ui.shadcn.com/docs/installation/next),
[FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/).
