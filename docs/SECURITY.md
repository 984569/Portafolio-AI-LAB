# Local Stage 1 operating boundary

PAPER is enforced in code; unsupported live environment values must fail startup.
No live-order route, broker key, arbitrary dataset URL, shell execution or LLM
tool exists. Backend validates finite bounded request values and enums. Queue
and list sizes are capped. Errors returned to users must not disclose stack
traces or environment values. Only known paths pass through the web proxy.

The application is a single-user local prototype, bound to loopback. It has no
production authentication, tenant isolation or public-hosting threat model.
Do not expose it externally without a separate design and authorization.
The local Next.js mutation proxy should reject cross-origin browser submissions
and only forward JSON configuration. Secrets stay out of NEXT_PUBLIC variables.

Stage2 historical dataset IDs are constrained, file paths and hashes are verified,
and no user URL/provider credential is accepted over HTTP. Corporate/source
quality is validated before registry publication. FINAL2024 evaluation is rejected
by request schema and research engine. ENABLE_TEST_FIXTURES defaults false;
normal API sources/jobs/history cannot expose synthetic research inputs. Baseline
test harnesses opt in, while the real historical suite explicitly disables it.

SQLite state is ignored by Git. Results and terminal status update atomically.
Interrupted jobs are failed explicitly on next API startup, not marked done.

## Stage 4 provider and proposal boundary

Agent Desk accepts only a local snapshot identifier, a decision date, an
allowlisted strategy and, where applicable, a verified model ID. The desk
rejects 2024 and sends only typed numeric facts and closed labels to OpenRouter.
There are no free-form external prompts, news fields or executable agent tools.
The adapter disables search plugins and rejects external annotations. The
Nemotron Lightning route accepts one named function envelope as response data,
validates its arguments against the stage schema, and never executes it.
All unexpected calls or arguments block the workflow.
Use a workspace without mandatory search plugins, since provider-side settings
may prevent request overrides.

Keys remain process-local to the API. The adapter verifies the fixed free
endpoint, caps request attempts and output size, and logs structured metadata.
Raw provider output, response bodies and credentials are excluded from the audit.
Provider or validation failure blocks the workflow. Deterministic risk gates
remain authoritative even if the Judge approves. Desk APIs expose proposals and
read-only event history. They have no order or execution endpoint.
