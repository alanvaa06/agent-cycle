---
id: google-adk
name: Google ADK
level: framework
nests_on: none
package: google-adk
version_verified: 2.11.0
license: Apache-2.0
ts_sdk: full
verified_on: 2026-10-07
status: active
---

# Google ADK

## 1. What it is
A code-first agent framework from Google: an `LlmAgent` runs a model-calls-tools loop, a `Runner` executes it and commits every yielded Event through a session service, and plugins and callbacks hook the lifecycle. 2.0 added a graph-based workflow runtime. Sources: https://adk.dev/ and https://adk.dev/runtime/event-loop/ . Version 2.11.0 (released 2026-10-02), Apache-2.0, Python 3.10 or later: https://pypi.org/project/google-adk/ . TypeScript, Go, Java and Kotlin SDKs exist (https://adk.dev/); `ts_sdk: full` is the catalog's decided value, feature parity with Python is unverified.

## 2. Filter attributes
| Attribute | Value | Source |
|---|---|---|
| model_portability | any | https://adk.dev/agents/models/litellm/ |
| a2a | client+server | https://adk.dev/a2a/quickstart-exposing/ and https://adk.dev/a2a/quickstart-consuming/ |
| mcp_client | native | https://adk.dev/tools-custom/mcp-tools/ |
| deploy_constraints | none (Vertex AI Agent Engine optional) | https://adk.dev/deploy/ |
| default_egress | none | https://adk.dev/observability/traces/ |
| stability | fast-moving | https://github.com/google/adk-python/releases |

Notes on the filter values (each with its own source):
- model_portability: Gemini is native; other providers go through the `LiteLlm` wrapper (`litellm>=1.84`). Source: https://adk.dev/agents/models/litellm/ . Claude in Python is native only through Vertex (Agent Platform); direct Anthropic API uses LiteLLM (research file docs/superpowers/research/2026-10-07-stack-catalog/google-adk.md, citing https://adk.dev/agents/models/anthropic/ ).
- a2a: both roles exist and both are labelled experimental. Server: `to_a2a(agent, port=...)` (`google.adk.a2a.utils.agent_to_a2a`) or `adk api_server --a2a`: https://adk.dev/a2a/quickstart-exposing/ . Client: `RemoteA2aAgent` (`google.adk.agents.remote_a2a_agent`): https://adk.dev/a2a/quickstart-consuming/ . Needs `google-adk[a2a]`; works with `a2a-sdk` 0.3.x (compatibility mode) and 1.x.
- deploy_constraints: no managed runtime is required; a container image on any host is a documented path (https://adk.dev/deploy/ , https://adk.dev/deploy/cloud-run/ ). The managed option is now named Agent Runtime on Agent Platform; the catalog value keeps the older "Vertex AI Agent Engine" wording.
- default_egress: telemetry export happens only when configured: OTLP exporters are added only when an `OTEL_EXPORTER_OTLP_*` variable is set (https://raw.githubusercontent.com/google/adk-python/v2.11.0/src/google/adk/telemetry/setup.py ), and Cloud Trace is opt in (https://adk.dev/observability/traces/ ). That ADK sends no other telemetry of its own is unverified. Model calls go to the configured model provider; eval judges default to a Gemini model (see traps).
- stability: no published versioning policy; "Breaking" entries ship in minors 2.7.0, 2.9.0 and 2.11.0, about one minor per week from 2.3.0 (2026-06-18) to 2.11.0 (2026-10-02). Sources: https://github.com/google/adk-python/releases and https://adk.dev/2.0/

## 3. Seam mapping
| Seam | Support | How | Source |
|---|---|---|---|
| sessions | native | `DatabaseSessionService` on PostgreSQL, MySQL or SQLite with an async driver (`postgresql+asyncpg://`); Supabase and Cloud SQL as plain Postgres is inference; `prepare_tables()` can run up front; a stale `Session` makes `append_event` raise `StaleSessionError`; the schema limits ids to 128 characters; official Firestore service is Java only; no DynamoDB service found (unverified absence), so a custom `BaseSessionService` | https://adk.dev/sessions/session/ and https://adk.dev/integrations/firestore-session-service/ |
| hitl_gate | custom | Native `require_confirmation` and `tool_context.request_confirmation` pause a tool call and resume in a NEW run that carries an `adk_request_confirmation` FunctionResponse; the feature is experimental and the docs list `DatabaseSessionService` and `VertexAiSessionService` as unsupported, so the binding does not rely on it: its own gate is a plugin `before_tool_callback` that ends the run, a repository row that holds the pending call, and a replay of the exact approved call from `before_model_callback` (inference, proven by build spikes) | https://adk.dev/tools-custom/confirmation/ and https://adk.dev/callbacks/types-of-callbacks/ |
| step_cap | custom | Native `RunConfig.max_llm_calls` (default 500, 0 or below means unlimited) is counted on the invocation context, and every `run_async` call builds a new one, so a resume after an approval restarts it; since 2.7.0 compositional function calling also counts against it; the binding counts model calls itself in a plugin and passes the remainder as a backstop | https://adk.dev/runtime/runconfig/ and https://raw.githubusercontent.com/google/adk-python/v2.11.0/src/google/adk/agents/invocation_context.py |
| tool_call_cap | custom | No native tool-call limit found (the invocation cost manager counts LLM calls only); the binding counts requested calls in a plugin `after_model_callback` (inference) | https://raw.githubusercontent.com/google/adk-python/v2.11.0/src/google/adk/agents/invocation_context.py |
| model_provider | native | Gemini native; other providers through `LiteLlm(model="provider/model")` | https://adk.dev/agents/models/litellm/ |
| telemetry | native | OTel GenAI conventions, spans `invoke_agent`, `execute_tool`, `generate_content` with `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens`; OTLP export through `OTEL_EXPORTER_OTLP_*` | https://adk.dev/observability/traces/ |
| eval_runner | native | `AgentEvaluator` with `tool_trajectory_avg_score` and match types EXACT, IN_ORDER, ANY_ORDER (arguments compared for equality unless ignored); `num_runs` (default 2) averages scores, which is not pass^k; model doubles by a custom `BaseLlm` or callbacks (inference) | https://adk.dev/evaluate/criteria/ |
| deploy | native | `adk api_server` (FastAPI), `get_fast_api_app` plus a Dockerfile on any container host, Cloud Run, GKE, Agent Runtime | https://adk.dev/deploy/cloud-run/ and https://adk.dev/runtime/api-server/ |

Further sources for the rows above:
- sessions (concurrency: in-process lock per session plus `SELECT ... FOR UPDATE` on Postgres, MySQL and MariaDB; no guidance for concurrent invocations on one session): https://adk.dev/sessions/session/ , https://adk.dev/runtime/event-loop/ ; stale-session check, `prepare_tables()` and the 128-character id limit are in the 2.11.0 source: https://raw.githubusercontent.com/google/adk-python/v2.11.0/src/google/adk/sessions/database_session_service.py and https://raw.githubusercontent.com/google/adk-python/v2.11.0/src/google/adk/sessions/schemas/shared.py
- hitl_gate (a before-tool callback or plugin that returns a dict skips the tool; plugins run before agent callbacks and wrap their exceptions in `RuntimeError`): https://adk.dev/plugins/ ; the confirmation flow, its gate and the resume path are in https://raw.githubusercontent.com/google/adk-python/v2.11.0/src/google/adk/flows/llm_flows/tools/_caller.py and https://raw.githubusercontent.com/google/adk-python/v2.11.0/src/google/adk/flows/llm_flows/tools/_confirmation.py
- eval_runner (`num_runs` and the mean-against-threshold rule, argument equality): https://raw.githubusercontent.com/google/adk-python/v2.11.0/src/google/adk/evaluation/agent_evaluator.py and https://raw.githubusercontent.com/google/adk-python/v2.11.0/src/google/adk/evaluation/trajectory_evaluator.py
- version 2.11.0, Apache-2.0, Python 3.10 or later: https://pypi.org/project/google-adk/

## 4. Known traps
- [ops] Resumed or replayed runs execute tools at least once ("run at least once, and may run more than once when resuming"), so destructive tools need idempotency keys. Source: https://adk.dev/runtime/resume/
- [ops] 2.9.0 breaking change: a failed workflow node now runs again on resume, repeating its side effects; node bodies must be idempotent (the binding uses no workflow nodes). Source: https://github.com/google/adk-python/releases/tag/v2.9.0
- [churn] No published versioning policy; "Breaking" entries ship in minors 2.7.0, 2.9.0 and 2.11.0, and 2.0 changed the stored Event schema (adds `node_info` and `output`). Pin exact versions and re-run the binding spikes on every upgrade. Source: https://adk.dev/2.0/ and https://github.com/google/adk-python/releases/tag/v2.11.0
- [ops] Native tool confirmation is experimental and the docs list `DatabaseSessionService` and `VertexAiSessionService` as unsupported; the one runner-level confirmation test read (tests/unittests/runners/test_run_tool_confirmation.py) uses an in-memory runner (inference that the database case is untested). The binding uses its own gate. Source: https://adk.dev/tools-custom/confirmation/
- [ops] `max_llm_calls` is counted per invocation context and every `run_async` starts at zero (so an approval resume restarts it); 0 or below means unlimited, which makes a naive "remaining budget" of 0 unlimited; compositional function calling counts against it since 2.7.0. Source: https://adk.dev/runtime/runconfig/ and https://github.com/google/adk-python/releases/tag/v2.7.0
- [ops] Request building drops function calls that have no matching response, so after a crash or timeout the model never learns a call may have run unless the build writes a response; an abort through `abort_signal` seals dangling calls with the text "aborted by client". Source: https://github.com/google/adk-python/blob/v2.11.0/docs/guides/runners/runner/abort.md
- [ops] A synchronous tool blocks the event loop, so a wall-clock timeout cannot fire until it returns; write tools as `async def` or set `tool_thread_pool_config`. Source: https://github.com/google/adk-python/blob/v2.11.0/docs/guides/runners/runner/abort.md
- [ops] Exceptions raised inside plugin callbacks are wrapped in `RuntimeError`, so caps and gates return responses instead of raising. Source: https://adk.dev/plugins/
- [ops] Enabling `ResumabilityConfig` makes the flow replay unexecuted tool calls of an invocation; the binding leaves it off. Source: https://adk.dev/runtime/resume/
- [ops] Eval judges default to a Gemini model: `JudgeModelOptions.judge_model` defaults to `gemini-2.5-flash` in the 2.11.0 source and the docs examples set `gemini-flash-latest`; the user simulator's default is unverified. Set the judge model explicitly. Source: https://raw.githubusercontent.com/google/adk-python/v2.11.0/src/google/adk/evaluation/eval_metrics.py and https://adk.dev/evaluate/criteria/
- [security] LiteLLM 1.82.7 and 1.82.8 on PyPI contained unauthorized code (2026-03-24); pin `litellm` exactly and lock with hashes. Source: https://adk.dev/agents/models/litellm/
- [security] MCP toolsets expose every server tool unless filtered; the docs say to always supply `tool_filter`. Source: https://adk.dev/tools-custom/mcp-tools/
- [churn] A2A is labelled experimental, and 2.8.0 shipped then reverted a guard that broke every HITL tool confirmation. Source: https://github.com/google/adk-python/releases/tag/v2.8.0

## 5. Pick when / avoid when
Pick when the client is GCP-centric (Gemini, Cloud Run, Agent Runtime: https://adk.dev/deploy/ ), or when native trajectory evals with EXACT, IN_ORDER and ANY_ORDER match types and native OTel GenAI spans matter (https://adk.dev/evaluate/criteria/ , https://adk.dev/observability/traces/ ).
Avoid when weekly releases with breaking minors cannot be absorbed (https://github.com/google/adk-python/releases ). Avoid when the design needs ADK's own confirmation flow to persist in a database session store: the docs list that as unsupported, so the binding substitutes its own gate (https://adk.dev/tools-custom/confirmation/ ). Avoid when sessions must live in Firestore or DynamoDB from Python: Firestore is Java only and DynamoDB needs a custom `BaseSessionService` (https://adk.dev/integrations/firestore-session-service/ ).

## 6. Build binding
`skills/build/references/bindings/google-adk.md`
