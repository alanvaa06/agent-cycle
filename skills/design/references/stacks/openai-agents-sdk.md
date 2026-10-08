---
id: openai-agents-sdk
name: OpenAI Agents SDK
level: framework
nests_on: none
package: openai-agents
version_verified: 0.23.1
license: MIT
ts_sdk: full
verified_on: 2026-10-07
status: active
---

# OpenAI Agents SDK

## 1. What it is
A Python agent library from OpenAI: a `Runner` loops model call, tool execution and handoff until a final output, with sessions, guardrails, human-in-the-loop approvals (`RunState`) and built-in tracing. Sources: https://openai.github.io/openai-agents-python/ and https://openai.github.io/openai-agents-python/running_agents/ . Version 0.23.1 (released 2026-10-02), MIT license, Python 3.10 or later: https://pypi.org/project/openai-agents/ . A JavaScript/TypeScript port exists (`@openai/agents`, 0.19.0 per the research file docs/superpowers/research/2026-10-07-stack-catalog/openai-agents-sdk.md, citing https://registry.npmjs.org/@openai/agents/latest ); `ts_sdk: full` is the catalog's decided value, feature parity with Python is unverified.

## 2. Filter attributes
| Attribute | Value | Source |
|---|---|---|
| model_portability | any | https://openai.github.io/openai-agents-python/models/ |
| a2a | none | https://openai.github.io/openai-agents-python/multi_agent/ |
| mcp_client | native | https://openai.github.io/openai-agents-python/mcp/ |
| deploy_constraints | none | https://developers.openai.com/api/docs/guides/agents |
| default_egress | tracing to OpenAI ON by default, inputs and outputs included | https://openai.github.io/openai-agents-python/tracing/ |
| stability | pre-1.0 | https://openai.github.io/openai-agents-python/release/ |

Notes on the filter values (each with its own source):
- model_portability: OpenAI models are native (Responses API recommended); other providers go through the LiteLLM and Any-LLM adapters, both "included on a best-effort, beta basis", or any OpenAI-compatible `base_url`. The catalog value stays `any`; the beta status and the lost hosted tools are in the model_provider row. Source: https://openai.github.io/openai-agents-python/models/
- a2a: the multi-agent page does not mention A2A (https://openai.github.io/openai-agents-python/multi_agent/ ) and the A2A feature request #1374 (opened 2025-08-05) is closed with no visible maintainer comment (https://github.com/openai/openai-agents-python/issues/1374 ). An A2A server would be build-written (inference).
- deploy_constraints: no managed runtime is required; the SDK runs inside your application and the guide says you control deployment. That no deployment guide exists on the documentation pages read is a finding of this check, not a page statement. Source: https://developers.openai.com/api/docs/guides/agents
- default_egress: "Tracing is enabled by default" and uploads to the OpenAI Traces dashboard; `trace_include_sensitive_data` defaults to True (LLM and tool inputs and outputs included; env `OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA`); unavailable for Zero Data Retention organizations. The default exporter posts to `https://api.openai.com/v1/traces/ingest` (source file `tracing/processors.py`, below). Sources: https://openai.github.io/openai-agents-python/tracing/ and https://raw.githubusercontent.com/openai/openai-agents-python/v0.23.1/src/agents/tracing/processors.py
- stability: version scheme `0.Y.Z`; `Y` rises for breaking changes to non-beta public interfaces, `Z` for fixes, features and beta changes; 10 Python releases between 2026-08-04 and 2026-10-02. Sources: https://openai.github.io/openai-agents-python/release/ and https://pypi.org/project/openai-agents/

## 3. Seam mapping
| Seam | Support | How | Source |
|---|---|---|---|
| sessions | adapter | `SQLAlchemySession` (Postgres, Supabase and Cloud SQL as plain Postgres via `postgresql+asyncpg://`), also Redis, SQLite, MongoDB, Dapr sessions; DynamoDB/Firestore via a small custom Session class (inference: the protocol is `session_id`, `session_settings`, `get_items`, `add_items`, `pop_item`, `clear_session`, no inheritance required); the docs give no locking guidance for concurrent runs on one session; items are written per turn, after that turn's tools ran | https://openai.github.io/openai-agents-python/sessions/ |
| hitl_gate | native | `needs_approval` (bool or async policy `(context, params, call_id)`) on function tools and agent-tools, `require_approval` on local MCP servers; the run pauses with `result.interruptions`, `result.to_state()`, `state.approve()/reject()`, `Runner.run(agent, state)`; `RunState.to_json()` resumes in another process; the resume continues the same run (turn count, `max_turns` and usage are in the snapshot, source-verified, the docs are silent); snapshots are not authenticated | https://openai.github.io/openai-agents-python/human_in_the_loop/ |
| step_cap | native | `max_turns` (default 10, `MaxTurnsExceeded`); a turn is one model invocation; the turn count and the cap travel in `RunState`, so the cap is per turn across an approval pause (source-verified, the docs do not say) | https://raw.githubusercontent.com/openai/openai-agents-python/v0.23.1/src/agents/run.py |
| tool_call_cap | custom | No native total tool-call cap; the build counts requested calls itself in a `RunHooks.on_llm_end` hook, which runs after the model response is processed and before any tool executes (source-verified); tool input guardrails run per tool invocation and are not used for the cap | https://raw.githubusercontent.com/openai/openai-agents-python/v0.23.1/src/agents/run_internal/turn_resolution.py |
| model_provider | adapter | OpenAI native (Responses API); LiteLLM (`litellm/...` names or `LitellmModel`) and Any-LLM adapters are beta and best-effort, hosted tools are Responses-only | https://openai.github.io/openai-agents-python/models/ |
| telemetry | custom | No native OpenTelemetry; the default trace processor exports to OpenAI, `set_tracing_disabled(True)` switches tracing off, `set_trace_processors()` replaces the default exporter (an OTel bridge is third-party: unverified), `add_trace_processor()` adds beside it | https://openai.github.io/openai-agents-python/tracing/ |
| eval_runner | adapter | `agents.testing.ScriptedModel` model double with `calls` (each call's `input` and `tools`) and `assert_complete()`; no trajectory API, the build reads requested calls from its own hook; OpenAI Evals goes read-only 2026-10-31 and shuts down 2026-11-30 | https://openai.github.io/openai-agents-python/testing/ and https://developers.openai.com/api/docs/deprecations |
| deploy | custom | Plain Python library: the build writes its own container (worker); the guide says the application controls deployment and the documentation pages read contain no deployment guide for the SDK (inference: any async-Python host works) | https://developers.openai.com/api/docs/guides/agents |

Further sources for the rows above:
- sessions (`SQLAlchemySession` signature, no schema argument, `create_tables` default False, row lock on mutations): https://raw.githubusercontent.com/openai/openai-agents-python/v0.23.1/src/agents/extensions/memory/sqlalchemy_session.py ; the `Session` protocol: https://raw.githubusercontent.com/openai/openai-agents-python/v0.23.1/src/agents/memory/session.py ; the SQLAlchemy page: https://openai.github.io/openai-agents-python/sessions/sqlalchemy_session/
- hitl_gate (snapshot trust, server-side storage, replay protection): https://openai.github.io/openai-agents-python/human_in_the_loop/ ; resume reads `current_turn` and `max_turns` from the state: https://raw.githubusercontent.com/openai/openai-agents-python/v0.23.1/src/agents/run.py ; `RunState.approve`, `reject`, `to_json`, `from_json`: https://raw.githubusercontent.com/openai/openai-agents-python/v0.23.1/src/agents/run_state.py
- step_cap (docs: `MaxTurnsExceeded`, `max_turns=None` disables, an `error_handlers` entry can return a controlled output): https://openai.github.io/openai-agents-python/running_agents/
- tool_call_cap (the guardrails page: tool guardrails run every time that tool is invoked and do not cover hosted or built-in tools): https://openai.github.io/openai-agents-python/guardrails/
- eval_runner (`ScriptedModel` helpers `assistant_message`, `function_call(..., call_id=...)`): https://raw.githubusercontent.com/openai/openai-agents-python/v0.23.1/src/agents/testing/model.py
- version 0.23.1, MIT license, Python 3.10 or later: https://pypi.org/project/openai-agents/

## 4. Known traps
- [data] Default tracing exports inputs and outputs of LLM calls and tools to OpenAI's Traces backend; disable it or replace the exporter as the first line of process start, before any client data flows. Source: https://openai.github.io/openai-agents-python/tracing/ and https://openai.github.io/openai-agents-python/models/
- [security] A serialized `RunState` is not authenticated and carries tool arguments and approval decisions: keep it in server-side storage only, authorize every resume, and prevent replay; a schema check does not authenticate a snapshot. Source: https://openai.github.io/openai-agents-python/human_in_the_loop/
- [ops] At an approval pause the session already holds the model's function call with no output, and the next run drops such calls from the model input in memory only, so the model never learns the call was not run unless the build writes an output item. Source: https://raw.githubusercontent.com/openai/openai-agents-python/v0.23.1/src/agents/run_internal/session_persistence.py
- [ops] Session items are saved after the turn's tools have run, so a crash or cancel during tool execution leaves no trace of the calls in the session; the build needs its own turn-status marker. Source: https://raw.githubusercontent.com/openai/openai-agents-python/v0.23.1/src/agents/run.py
- [ops] A function tool that raises is turned into the fixed model-visible text "An error occurred while running the tool. Please try again." by default, which invites a retry of a call whose effect is unknown; a tool timeout returns a model-visible message by default too. Source: https://raw.githubusercontent.com/openai/openai-agents-python/v0.23.1/src/agents/tool.py
- [ops] A `require_approval` dict on a local MCP server leaves every tool not named in it ungated, and `None` gates nothing. Source: https://raw.githubusercontent.com/openai/openai-agents-python/v0.23.1/src/agents/mcp/server.py
- [ops] Synchronous function tools run in a thread (`asyncio.to_thread`), which a wall-clock cancel cannot stop; write tools as `async def`. Source: https://raw.githubusercontent.com/openai/openai-agents-python/v0.23.1/src/agents/tool.py
- [churn] Breaking changes ship in minors (0.Y): default model changes in 0.16 and 0.20, the MCP SDK v2 move in 0.20, `openai>=3` in 0.21, and 0.23.0 needs migration (explicit strict-tool parameters, fresh legacy approvals, trusted encrypted-history import). Pin exactly and re-run every spike on any upgrade. Source: https://github.com/openai/openai-agents-python/releases and https://openai.github.io/openai-agents-python/release/
- [churn] RunState snapshots carry a schema version (1.18 at 0.23.1) and older SDKs reject newer versions, so pending approvals must be drained before any upgrade or rollback. Source: https://raw.githubusercontent.com/openai/openai-agents-python/v0.23.1/src/agents/run_state.py
- [churn] OpenAI Evals goes read-only 2026-10-31 and shuts down 2026-11-30, and Agent Builder shuts down 2026-11-30; do not build the eval seam on them. Source: https://developers.openai.com/api/docs/deprecations

## 5. Pick when / avoid when
Pick when the client is OpenAI-first and wants the strongest native approval and resume flow: per-tool `needs_approval`, a pause that returns control to the caller, a snapshot that resumes in another process with the turn count carried (https://openai.github.io/openai-agents-python/human_in_the_loop/ , https://raw.githubusercontent.com/openai/openai-agents-python/v0.23.1/src/agents/run.py ). OpenAI's guide frames the SDK as the choice when the application controls deployment, storage and approvals (https://developers.openai.com/api/docs/guides/agents ). The build still owns the pending-approval record, the tool-call cap, the dangling-call and crash repair, the telemetry replacement and any A2A server.
Avoid for provider-neutral clients: the LiteLLM and Any-LLM adapters are beta and lose hosted tools (https://openai.github.io/openai-agents-python/models/ ). Avoid when A2A is required: no native support (https://github.com/openai/openai-agents-python/issues/1374 ). Avoid when no data may leave to OpenAI unless the tracing replacement is enforced and proven by the build's telemetry spike (https://openai.github.io/openai-agents-python/tracing/ ). Avoid when breaking minors cannot be absorbed (https://github.com/openai/openai-agents-python/releases ).

## 6. Build binding
`skills/build/references/bindings/openai-agents-sdk.md`
