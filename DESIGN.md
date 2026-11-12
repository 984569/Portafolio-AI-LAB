# Portfolio AI Lab — visual system v1

An original, calm research terminal: dense enough to compare experiments,
spacious enough to inspect assumptions. Spanish interface. Financial numbers
are computed API results; no decorative prices, fabricated KPIs or fake feeds.

## Color tokens

| Role | Dark | Light |
|---|---|---|
| Canvas | #0B1220 | #F4F6F9 |
| Surface | #101B2C | #FFFFFF |
| Elevated | #152133 | #EAF0F6 |
| Border | #2B3B50 | #CBD5E1 |
| Primary text | #EDF4FA | #182435 |
| Muted text | #A7B5C6 | #526176 |
| Primary action | #6BD9B0 | #116647 |
| Information | #7EA9FF | #284FA8 |
| Caution | #E9BD74 | #805100 |
| Loss/error | #F17B82 | #AD253C |

Tokens live in CSS variables and Tailwind theme bindings. Mint buttons use dark
ink in dark mode and white text in light mode. Status always includes a label.
Decorative borders must not be the only input boundary: interactive controls
use #71849A in dark mode, with the blue focus ring. The design audit calculated
4.22:1 for this boundary against #152133; actual rendered UI still needs QA.

## Type, spacing and shape

Use local system sans stack (Segoe UI, Arial) and a system monospace stack for
run IDs and tabular metrics. Avoid remote font dependencies in reproducible builds.
UI 14–16px, labels 12–13px, section headings 18–24px, page title max 32px.
Use tabular numerals and explicit units. Spacing 4/8/12/16/24/32/48px;
cards radius 12px, controls 8px, border 1px. Subtle shadows, no glass effects.

## Layout and components

Desktop: 232px sidebar, 64px context bar, max-width 1440px content, 24–32px
gutters. A visible PAPER badge and fixture disclosure persist above results.
Primary journey: inspect backend → configure fixture → submit → observe job →
inspect saved equity, allocations, metrics and provenance. Chart uses actual
dated values, readable axis labels and a textual/table alternative.

Use shadcn/ui Button, Card, Badge and Input primitives with consistent variants.
The initial navigation only links implemented sections. Future strategies are
clearly marked pending and never presented as active models. No dead controls.

Under 1024px collapse the sidebar into compact navigation. At 768px stack the
configuration and results; at 390px use one/two column metric cards and allow
horizontal scrolling only inside labeled tables. No page-level overflow.

## States and accessibility

Implement initial loading, no experiments, API offline with retry, submitting,
queued/running, successful result and failed experiment states. Null Sharpe is
shown as “No definido”, never 0. Retain a selected run while refreshing history.
Use semantic headings, form labels, live status announcements, keyboard access,
visible 2px focus ring and touch controls at least 44px. Respect reduced motion.
Theme toggle uses a semantic button and persists locally. Aim for WCAG 2.2 AA;
do not claim certification from automated tests.

## Verification

Capture actual browser views at 1440×900, 1280×800, 768px and 390px. Verify form
submission, result provenance, keyboard focus, error recovery and light mode.
No third-party visual assets or copied marks are required for this stage.

Implemented Stage1: system-font UI, Lucide allocation-layer symbol, locally
measured SVG chart with readable mobile axes and table alternative. Reviewed
real captures and limits are in docs/validation-report.md. This is a working
foundation, not an accessibility certification or final design of pending pages.

Agent Desk uses the same cards, controls and type tokens. Keep the hypothetical
allocation separate from academic performance charts. Show a Judge verdict
alongside the independent risk decision, bring vetoed checks to the top, and
preserve the recorded provider identity and snapshot hash. On tablet and mobile
stack the configuration and decision cards. Risk tables scroll within a labeled
region. The mock provider label stays visible whenever test results are shown.
