# Stack card: OpenAI Agents SDK (Python `openai-agents`, JS/TS `@openai/agents`)

Researched 2026-10-07. Every claim cites the page it came from. "unverified" means I could not confirm it on a page. "inference" means my own reasoning.

Sources (short keys used below):
- [PYPI] https://pypi.org/project/openai-agents/
- [DOCS] https://openai.github.io/openai-agents-python/
- [REL] https://openai.github.io/openai-agents-python/release/
- [GHREL] https://github.com/openai/openai-agents-python/releases
- [SESS] https://openai.github.io/openai-agents-python/sessions/
- [HITL] https://openai.github.io/openai-agents-python/human_in_the_loop/
- [RUN] https://openai.github.io/openai-agents-python/running_agents/
- [RUNCFG] https://raw.githubusercontent.com/openai/openai-agents-python/main/src/agents/run_config.py
- [MODELS] https://openai.github.io/openai-agents-python/models/
- [TOOLS] https://openai.github.io/openai-agents-python/tools/
- [AGENTS] https://openai.github.io/openai-agents-python/agents/
- [LIFE] https://openai.github.io/openai-agents-python/ref/lifecycle/
- [MCP] https://openai.github.io/openai-agents-python/mcp/
- [GUARD] https://openai.github.io/openai-agents-python/guardrails/
- [MULTI] https://openai.github.io/openai-agents-python/multi_agent/
- [TRACE] https://openai.github.io/openai-agents-python/tracing/
- [TEST] https://openai.github.io/openai-agents-python/testing/
- [NPM] https://registry.npmjs.org/@openai/agents/latest
- [JSREL] https://github.com/openai/openai-agents-js/releases
- [JSCFG] https://openai.github.io/openai-agents-js/guides/config/
- [JSAISDK] https://openai.github.io/openai-agents-js/extensions/ai-sdk/
- [JSSESS] https://openai.github.io/openai-agents-js/guides/sessions/
- [A2AISSUE] https://github.com/openai/openai-agents-python/issues/1374
- [DEPR] https://developers.openai.com/api/docs/deprecations
- [OAIAG] https://developers.openai.com/api/docs/guides/agents
- [AGENTSAPI] https://openai.com/index/introducing-the-agents-api/ (via search result summary; page not fetched directly)
- [TEMPORAL] https://docs.temporal.io/develop/python/integrations/openai-agents (via search result summary)
- [OTELSEARCH] https://grafana.com/blog/observing-agentic-ai-workflows-with-grafana-cloud-opentelemetry-and-the-openai-agents-sdk , https://coralogix.com/docs/user-guides/ai/otel-integration/code-examples/openai-agents-sdk/ , https://pypi.org/project/openai-agents-opentelemetry/0.3.0/ (via search result summaries)

---

## 1. Identity

| Item | Python | JS/TS |
|---|---|---|
| Package | `openai-agents` [PYPI] | `@openai/agents` (+ `-core`, `-openai`, `-realtime`, `-extensions`) [NPM][JSREL] |
| Current version | 0.23.1, released 2026-10-02 [PYPI][GHREL] | 0.19.0, published 05 Oct (2026 per npm timestamp) [NPM][JSREL] |
| License | MIT [PYPI] | MIT [NPM] |
| Runtime | Python >=3.10 [PYPI] | Node server runtimes; tracing off by default in browsers [JSCFG] |
| Maintainer | OpenAI (maintainers kwhinnery-openai, rm-openai, seratch-openai) [PYPI] | OpenAI [JSREL] |

- **Versioning policy:** modified semver `0.Y.Z`. Breaking changes to non-beta public APIs bump `Y`; patches carry fixes, new features, and beta changes [REL]. Pin to a minor line.
- **Churn is real:** 10 Python releases between 2026-08-04 and 2026-10-02 [PYPI]. Recent minors broke things: default model changed twice (0.16 to `gpt-5.4-mini`, 0.20 to `gpt-5.6-luna`), MCP SDK v2 move (0.20), `openai>=3` and HTTPX2 move (0.21), `ModelBehaviorError` on failed/incomplete responses (0.22) [REL]; 0.23.0 requires migration for strict-tool params, legacy approvals, encrypted history import [GHREL].
- Maturity: docs call it "production-ready" successor to Swarm [DOCS]; the 0.x version line says otherwise about API stability (inference).
- Python optional extras include `litellm`, `any-llm`, `redis`, `sqlalchemy`, `mongodb`, `dapr`, `temporal`, `encrypt`, `docker`, `e2b`, `modal`, `voice`, `realtime`, `viz` [PYPI].

## 2. Core abstractions and agent loop

- Primitives: **Agent** (LLM + instructions + tools), **handoffs / agents-as-tools**, **guardrails**; runtime adds sessions, HITL, tracing, sandbox agents, realtime and voice agents [DOCS].
- **Runner loop:** call the LLM for the current agent; if output is final (desired type, no tool calls) stop; on handoff switch agent and loop; on tool calls execute, append results, loop [RUN]. Input can be a string, Responses API input items, or a `RunState` for resume [RUN].
- `tool_use_behavior`: `run_llm_again` (default), `stop_on_first_tool`, `StopAtTools`, or a custom function; `reset_tool_choice=True` by default to avoid tool loops [AGENTS].
- Lifecycle hooks `RunHooks`/`AgentHooks` with `on_llm_start/end`, `on_tool_start/end`, `on_handoff` [LIFE].

## 3. State / sessions

- Built-in `Session` implementations: `SQLiteSession` (default), `AsyncSQLiteSession`, `RedisSession`, `SQLAlchemySession` (any SQLAlchemy DB, i.e. Postgres), `MongoDBSession`, `DaprSession` (any Dapr state store), `OpenAIConversationsSession` (server-side), `OpenAIResponsesCompactionSession` (wrapper), `AdvancedSQLiteSession` (branching + usage), `EncryptedSession` (wrapper with TTL); community Django session [SESS].
- **Custom sessions** need only `session_id`, `session_settings`, `get_items`, `add_items`, `pop_item`, `clear_session`; no inheritance required [SESS]. A DynamoDB or Firestore backend is a small custom class (inference; no built-in DynamoDB/Firestore session found on [SESS]).
- **Concurrency per session:** the docs do not describe locking for concurrent runs on one session [SESS]; only compaction serializes its own mutations [SESS]. 0.22.1 fixed "concurrent writes during compaction" [GHREL]. Treat per-session serialization as the app's job (inference), which matches the pipeline's serial-per-user worker.
- Session trust boundary: session IDs select history but do not authenticate users [SESS].
- Session cannot be combined with `conversation_id`/`previous_response_id` in the same run [RUN].
- **Durable execution:** docs list Temporal, Dapr, Restate, DBOS integrations [RUN]. Temporal runs the agent loop inside a Workflow with each model call as an Activity, via `temporalio[openai-agents]` and `OpenAIAgentsPlugin` [TEMPORAL]; Temporal's TypeScript integration is labelled pre-release [TEMPORAL]. DBOS needs only SQLite or Postgres [RUN].
- JS sessions: `MemorySession`, `OpenAIConversationsSession`, `OpenAIResponsesCompactionSession` plus a `Session` interface with transaction-aware extensions [JSSESS]. No Redis/SQL session in JS found on that page (unverified whether one exists elsewhere).

## 4. HITL / approval gate

- Native: `needs_approval=True` or an async callable (context, parsed args, call ID) on function tools, `Agent.as_tool`, `ShellTool`, `ApplyPatchTool`; `require_approval` on local MCP servers (stdio/SSE/Streamable HTTP); `tool_config={"require_approval": "always"}` on `HostedMCPTool` [HITL].
- Flow: run pauses, `result.interruptions` holds `ToolApprovalItem`s; `result.to_state()`, `state.approve()/reject()`, `Runner.run(agent, state)` [HITL].
- **Durable across processes:** `RunState.to_json()/to_string()` and `from_json()/from_string()` are designed to be stored in a DB or queue and resumed in another process [HITL].
- Caveats: snapshots are not authenticated, include app context and tool args, and need a version marker; the app must handle authz and replay protection [HITL]. Unparseable args force manual approval (fail closed) [HITL]. Computer tool uses a separate `on_safety_check`; hosted shell does not support approval [HITL].
- **Mapping to tiers (inference):** set `needs_approval` from tool tier metadata (`destructive` always True, `reversible` callable policy, `safe` False). Store `RunState` JSON in the session repository, emit approval request via webhook/queue, resume in a worker. Clean fit. `tool_input_guardrails` can run before the approval interruption with `ToolExecutionConfig(pre_approval_tool_input_guardrails=True)` [GUARD].

## 5. Caps

- `max_turns` default **10** (`DEFAULT_MAX_TURNS = 10`) [RUNCFG]; a turn is one LLM call including its tool calls [RUN]; exceeding raises `MaxTurnsExceeded`, or `error_handlers["max_turns"]` returns a controlled final output [RUN]. `None` disables it [RUN].
- **No native total tool-call cap.** Docs show none [RUN][TOOLS]; the nearest knob is `tool_execution.max_function_tool_concurrency`, which caps parallelism, not total [RUN].
- Custom tool-call cap (inference): count in `RunHooks.on_tool_start` [LIFE] or a tool input guardrail that rejects after N [GUARD]. Whether raising inside a hook aborts the run is not documented [LIFE] (unverified); a tool input guardrail tripwire is documented to halt execution [GUARD], so prefer that path. Note hooks/tool guardrails do not cover hosted tools [GUARD].

## 6. Model providers

- OpenAI native; Responses API (`OpenAIResponsesModel`) recommended, Chat Completions (`OpenAIChatCompletionsModel`) as fallback [MODELS]. Default model `gpt-5.6-luna` [MODELS].
- Non-OpenAI: OpenAI-compatible `base_url`, custom `ModelProvider`, or adapters **LiteLLM** (`litellm/...` prefix) and **Any-LLM**, both "beta, best-effort" [MODELS]. `MultiProvider` routes by prefix [MODELS].
- Known gaps off-OpenAI: tracing 401s (traces upload to OpenAI), structured-output 400s, hosted tools usually unsupported, usage metrics need `include_usage=True`, unreliable streamed tool-call deltas [MODELS]. Tool search and Programmatic Tool Calling are Responses-only [MODELS].
- JS: Vercel AI SDK adapter `aisdk()` in `@openai/agents-extensions`, "still in beta", AI SDK provider spec v2-v4 [JSAISDK].
- Fit with LiteLLM-style config: workable via `litellm/<model>` strings (inference: the pipeline's provider config maps cleanly to this prefix), but feature parity is lower off-OpenAI.

## 7. Tools

- Function tools with auto schema + Pydantic validation [DOCS]; per-tool `timeout`, `failure_error_function`, `is_enabled` (visibility only, "not authorization") [TOOLS].
- Hosted tools (Responses-only): web search, file search, code interpreter, hosted MCP, image generation, tool search, programmatic tool calling [TOOLS].
- MCP client: stdio, Streamable HTTP, SSE (deprecated by MCP project), and hosted MCP [MCP]; static allow/block lists and dynamic filters for least privilege; `cache_tools_list`; `MCPServerManager` [MCP]. Exposing an agent as an MCP server is not covered [MCP].
- Guardrails: input (first agent only), output (last agent only), tool input/output guardrails on function tools and local MCP tools; not on hosted tools, handoffs, or built-in execution tools [GUARD]. Input guardrails run in parallel by default; set `run_in_parallel=False` to block before spend [GUARD].

## 8. Multi-agent

- Handoffs (triage routes, specialist owns the turn) and agents-as-tools (manager keeps control); code-driven orchestration also recommended [MULTI].
- **A2A: no native support.** The multi-agent page does not mention A2A [MULTI]; release notes for 0.22/0.23 don't mention it [GHREL]; the A2A feature request (#1374, opened 2025-08-05) is closed with no maintainer comment [A2AISSUE]. A2A would be a separate adapter, e.g. the `a2a-sdk` package wrapping `Runner.run` (inference).

## 9. Observability

- Tracing **on by default**, exported to the OpenAI Traces dashboard [TRACE]. `trace_include_sensitive_data` defaults to **True** (inputs/outputs captured) [TRACE]. Unavailable for ZDR orgs [TRACE]. Trace retention period is not stated on the tracing page [TRACE] or the data-controls page (unverified).
- Disable: `OPENAI_AGENTS_DISABLE_TRACING=1`, `set_tracing_disabled(True)`, or `RunConfig.tracing_disabled` [TRACE]. Redirect: `set_trace_processors()` replaces the OpenAI exporter; `add_trace_processor()` adds alongside it (a redactor added this way does not stop the default export) [TRACE].
- **OTel / GenAI semconv: not native.** The tracing page does not mention OpenTelemetry [TRACE]. Bridges exist: OpenTelemetry contrib `opentelemetry-instrumentation-openai-agents-v2` (GenAI semconv, `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`), OpenInference instrumentation, and third-party `openai-agents-opentelemetry` [OTELSEARCH] (contrib package's PyPI page did not load; version/status unverified). ~35 vendor processors listed (Langfuse, Phoenix, Logfire, Datadog, MLflow...) [TRACE].
- JS: tracing on in server runtimes, off in browsers and under `NODE_ENV=test`; model/tool data redacted in logs by default [JSCFG].

## 10. Testing / evals

- `agents.testing.ScriptedModel` (scripted model double; `assistant_message()`, `function_call()`, `ModelStep.raise_error()`), `assert_complete()`, `UnexpectedModelCall`; `ScriptedModel.calls` exposes each call's input, tools, handoffs [TEST]. No dedicated trajectory API; trajectory comes from recorded calls or `RunResult` items [TEST]. Provider-neutral and in-memory [TEST].
- Trajectory modes EXACT / IN_ORDER / ANY_ORDER: build from `RunResult` new items or a custom trace processor (inference). Pytest-friendly.
- **OpenAI Evals platform is being shut down:** read-only 2026-10-31, dashboard and API shut down 2026-11-30, migration to Promptfoo; graders are part of the transition [DEPR]. Do not build the eval seam on OpenAI Evals/trace grading.

## 11. Deployment

- Library only; you host the loop [OAIAG]. No deploy guide for Docker/AWS/GCP found in the doc nav [DOCS] (inference: deploys like any async Python/Node service, so VPS Compose, ECS/Lambda, Cloud Run all work).
- Costs: MIT, no license fee [PYPI]; you pay model tokens; hosted tools are billed by OpenAI (unverified pricing, not checked).
- Managed alternatives from OpenAI: **Agents API** (public beta, launched 2026-09-10, managed Codex harness, OpenAI-hosted loop, sandbox OpenAI-managed or yours) [AGENTSAPI][OAIAG].

## 12. When to pick / when not

Pick when: OpenAI models are primary; you want a thin loop with first-class HITL resume (`RunState`), sessions, guardrails, and MCP; you need Python and TS parity [DOCS][HITL]. OpenAI's own guidance: choose the SDK when you want to control deployment, storage, approvals [OAIAG].

Avoid or hedge when:
- Multi-provider is a hard requirement: LiteLLM/Any-LLM adapters are beta with documented gaps [MODELS].
- Data governance: default tracing ships prompts and tool I/O to OpenAI unless disabled or replaced [TRACE].
- API stability matters: 0.x with breaking minors roughly monthly [REL][PYPI].
- A2A or OTel-native telemetry are must-haves: both need third-party adapters [MULTI][TRACE].
- OpenAI product gravity: Agent Builder and Evals shut down 2026-11-30 [DEPR], Assistants API shut down 2026-08-26 [DEPR]; the hosted surface moves fast.

### Relation to OpenAI hosted offerings (3 lines)
1. The SDK is built on the **Responses API** (recommended model shape; hosted tools, Conversations, compaction are Responses-only) [MODELS][TOOLS].
2. **AgentKit's Agent Builder** is deprecated with shutdown 2026-11-30; OpenAI points users to the Agents SDK or ChatGPT Workspace Agents; ChatKit remains [DEPR].
3. The new **Agents API** (beta) is the managed alternative where OpenAI runs the loop; the SDK is the self-hosted option [OAIAG][AGENTSAPI].

## 13. Verdict

Good fit for most seams, with three adapters to own. **Sessions:** the `Session` protocol is a four-method repository interface; Postgres/Supabase/Cloud SQL via `SQLAlchemySession`, DynamoDB/Firestore via small custom classes; per-session serialization stays in your queue worker [SESS] (inference on DynamoDB/Firestore). **HITL:** strongest seam; `needs_approval` plus serializable `RunState` maps directly onto tiered tools and webhook resume [HITL]. **Caps:** step cap native (`max_turns`, default 10), tool-call cap must be custom via a tool input guardrail or hook counter [RUNCFG][GUARD]. **Providers:** LiteLLM prefix works but is beta and loses hosted tools and some structured-output reliability [MODELS]. **Telemetry:** must call `set_trace_processors()` with an OTel GenAI bridge (contrib or third-party) and disable the default OpenAI exporter, otherwise traces with sensitive data leave to OpenAI [TRACE][OTELSEARCH]. **Evals:** `ScriptedModel` is a solid model double for the pytest harness [TEST]; keep evals framework-agnostic since OpenAI Evals shuts down 2026-11-30 [DEPR]. **A2A:** absent natively [MULTI][A2AISSUE]; wrap with an external A2A server. **MCP:** good client coverage with allow/block filtering [MCP]. **Deploy:** plain library, any target (inference). Net: recommend when the client is OpenAI-first; for provider-neutral clients the seams still hold but you carry more adapter code and pin a 0.Y line against monthly breaking minors.
