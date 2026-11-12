# Environment audit — 2026-11-09

Observed in the selected Windows workspace; no installations during audit.

| Tool/state | Observed |
|---|---|
| Git | 2.52.0; already initialized; master; no commits |
| Original work | only master context untracked; preserved |
| Origin | existing GitHub remote; no writes made |
| Node/npm | 25.2.1 / 11.7.0 |
| pnpm | 10.28.2 |
| Python PATH | 3.11.9 |
| Python launcher | defaults to 3.14; 3.11 also installed |
| uv | 0.11.7 |
| Docker/Compose | 29.4.0 / 5.1.2; daemon unavailable |
| Native agents | three actual read-only specialists started |
| Managed worktree tool | exposed; no attached artifacts; HEAD absent |
| Browser | CUA tool exposed; browser runtime verification pending |
| Academic PDFs | absent in repository |

Dependency strategy: repository-local .venv and node_modules, Python 3.11,
uv.lock/pnpm-lock.yaml; no global installs, no runtime secrets.
Current framework guidance checked against official Next.js, Tailwind,
shadcn and FastAPI documentation; links in README. Exact resolved versions
will be recorded after dependency installation, not guessed in this audit.

Resolved local versions: FastAPI0.162.2, Pydantic2.14.3, uvicorn0.54.0,
pytest9.2.0, Ruff0.17.4; Next16.4.6, React19.3.1, Tailwind4.3.5,
TypeScript5.9.3, Playwright1.65.0 and openapi-typescript7.13.0. Exact
transitive versions are in uv.lock and pnpm-lock.yaml. SQLite3.45.1 uses DELETE
journaling. Chromium downloaded to ignored repository-local .runtime/browsers.

Plugin/tool inventory: native collaboration, managed-worktree and preview
tools are exposed. GitHub/connected-app tools are exposed but no account access
or credentials were exercised; tool presence is not connection verification.
Sites skill was applied only through its local-only route, without registration
or publishing. No new plugins installed. Native agents are verified by actual
starts/reports; browser runtime verified by successful Chromium E2E.
