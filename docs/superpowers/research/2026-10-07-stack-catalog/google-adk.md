# Stack card: Google Agent Development Kit (ADK)

Researched 2026-10-07. Primary sources: adk.dev (the old google.github.io/adk-docs 301-redirects there), PyPI, GitHub releases and source. Labels: **unverified** means not confirmed on a page I read. **inference** means my own reasoning.

## 1. Identity

- **Package:** `google-adk` on PyPI. Current version is **2.11.0, released 2026-10-02**. Requires Python >=3.10. License is Apache 2.0. Author is Google LLC (maintainer account `vertex_ai`). https://pypi.org/project/google-adk/
- **Extras:** a2a, agent-identity, antigravity, bigquery-analytics, community, daytona, db, dev, e2b, eval, extensions, gcp, livekit, mcp, mongodb, oci, openai, otel-gcp, redis, slack, test, toolbox, tools, and others (same PyPI page).
- **Other languages:** TypeScript `@google/adk`, Go `google.golang.org/adk/v2`, Java `com.google.adk:google-adk`, Kotlin `google-adk-kotlin-core`. https://adk.dev/
- **2.0 GA dates:** Python 2.0 on 2026-05-19, Go 2.0 on 2026-06-30, TypeScript 2.0 on 2026-08-21. https://adk.dev/2.0/
- **Release cadence:** roughly weekly minors (2.3.0 on Jun 18 through 2.11.0 on Oct 2). Fixes are backported to a maintained 1.x line (v1.39.1, Aug 27). https://github.com/google/adk-python/releases
- **Versioning policy:** none is published. The 2.0 page claims compatibility with 1.x but lists breaking changes. Minor releases also carry "Breaking" entries (2.7.0, 2.9.0, 2.11.0). For 1.x, the only guidance is to pin `google-adk~=1.0`, with no end-of-life date. https://adk.dev/2.0/ , https://github.com/google/adk-python/releases
- **Inference:** semver is not honored in practice, so pin exact versions.

## 2. Core abstractions and loop

- **Agents:** `LlmAgent` (alias `Agent`), workflow agents (`SequentialAgent`, `ParallelAgent`, `LoopAgent`), and custom agents. `Runner` orchestrates execution. Session, State and Memory hold context, Events are the unit of history, and Callbacks hook into the lifecycle. https://adk.dev/get-started/about/
- **2.0 Workflow Runtime:** 2.0 moves ADK "from a hierarchical agent executor to a graph-based execution engine". Agents, tools and functions become nodes, and Python agents subclass `BaseNode`. Overriding `_run_async_impl()` is now silently ignored. Catching `BaseException` breaks HITL pauses. https://adk.dev/2.0/
- **Graph workflows:** `Workflow(name, edges=[("START", agent, fn, ...)])`, with router nodes that emit `Event(route=...)`. https://adk.dev/graphs/
- **Deprecations:** TypeScript deprecates Sequential/Parallel/Loop agents (https://adk.dev/2.0/). The Python graphs page still presents them as templates (https://adk.dev/graphs/).
- **Event loop:** an agent yields an Event, then pauses. The Runner commits `event.actions` (state_delta) through the SessionService, and only then does the agent resume. State is guaranteed persisted only after the yielding event is processed, so uncommitted changes are lost on failure. https://adk.dev/runtime/event-loop/
- **Plugins:** `BasePlugin` registers once on the runner and applies globally. Plugin hooks run before object-level callbacks. https://adk.dev/plugins/

## 3. State and sessions

- **Built-in services:** `InMemorySessionService` (all languages), `VertexAiSessionService` (managed; Python, Go, Java, Kotlin), and `DatabaseSessionService` (Python, Go). https://adk.dev/sessions/session/
- **Python source also has** `sqlite_session_service.py`. https://github.com/google/adk-python/tree/main/src/google/adk/sessions
- **DatabaseSessionService:** relational only, "PostgreSQL, MySQL, SQLite". It requires an async driver (`asyncpg`, `aiomysql`, `sqlite+aiosqlite`). Python has had schema migrations (v1.22.0), and 2.0 changed the Event schema. https://adk.dev/sessions/session/ , https://adk.dev/2.0/
- **Supabase and Cloud SQL Postgres:** inference: these work as plain Postgres through `postgresql+asyncpg://`. Not tested on a page.
- **Firestore:** the official service is **Java only** (`google-adk-firestore-session-service`). https://adk.dev/integrations/firestore-session-service/
- **Redis:** a Python service exists in `google-adk-community`. https://github.com/google/adk-python-community/tree/main/src/google/adk_community/sessions
- **Aerospike:** available as a third-party package (search result, unverified).
- **DynamoDB:** no service found in any language (unverified absence). You would need to subclass `BaseSessionService` (inference).
- **Concurrency:** an in-process lock serializes `append_event` per session. On Postgres, MySQL and MariaDB the service also uses `SELECT ... FOR UPDATE` row locks. Optimistic locking is not documented. https://adk.dev/sessions/session/
- **Concurrent invocations on one session:** no guidance is given (https://adk.dev/runtime/event-loop/). Inference: enforce serial-per-user in your own queue worker.
- **Memory services:** `InMemoryMemoryService`, `VertexAiMemoryBankService` (needs a GCP Agent Runtime instance) and `VertexAiRagMemoryService`. https://adk.dev/sessions/memory/
- **SQLite memory:** added in 2.11.0 via a `sqlite://` URI. https://github.com/google/adk-python/releases/tag/v2.11.0

## 4. HITL / approval gate

- **Tool confirmation:** `FunctionTool(fn, require_confirmation=True | callable(args)->bool)`, which can be conditional (for example, amount > 1000). For structured approvals, use `tool_context.request_confirmation(hint, payload)`. https://adk.dev/tools-custom/confirmation/
- **Remote approval:** send a `FunctionResponse` named `adk_request_confirmation` with the matching call id and `{confirmed, payload}` to `/run` or `/run_sse`. Include `invocation_id` if Resume is enabled. Same URL.
- **Status: Experimental**, with listed known limitations: **"`DatabaseSessionService` is not supported" and "`VertexAiSessionService` is not supported."** Same URL. Release notes show ongoing fixes such as "resolve tool confirmation resumption failure in production" (search result, unverified). Inference: the doc limitation may be stale, but treat it as real until you test it.
- **Graph HITL:** a node yields `RequestInput(message, payload, response_schema)`. Supported in Python, TS and Go 2.0. The docs do not say which session stores support it. https://adk.dev/graphs/human-input/
- **2.11.0:** tool nodes pause through `RequestInput`. https://github.com/google/adk-python/releases/tag/v2.11.0
- **Resume:** enabled with `App(..., resumability_config=ResumabilityConfig(is_resumable=True))`. Tools run "at least once", so destructive tools need idempotency keys. https://adk.dev/runtime/resume/
- **2.9.0 breaking change:** failed workflow nodes re-run on resume, so side effects may repeat. https://github.com/google/adk-python/releases
- **Mapping to tier gates:** use `require_confirmation` (or a callable) on reversible and destructive tools. Add a global plugin `before_tool_callback` that returns a dict to block a tool outright: "the tool's `run_async` method is **skipped**." https://adk.dev/callbacks/types-of-callbacks/

## 5. Caps

- **LLM-call cap (native):** `RunConfig.max_llm_calls`, default 500. A value of 0 or below means unlimited. https://adk.dev/runtime/runconfig/
- **When exceeded:** `LlmCallsLimitExceededError("Max number of llm calls limit of N exceeded")` is raised. https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/agents/invocation_context.py
- **Environment variable:** `ADK_MAX_LLM_CALLS` was added in 2.8.0. https://github.com/google/adk-python/releases/tag/v2.8.0
- **Tool-call cap:** **none native**. The cost manager counts only LLM calls (same source file). Inference: build it as a plugin `before_tool_callback` with a counter in `temp:` state that returns an error dict once N is reached.
- **Step cap vs LLM calls:** inference: graph node steps have no separate cap, so `max_llm_calls` is the step proxy.

## 6. Model providers

- **Gemini:** native and the optimized default ("optimized for Google's Gemini models"). https://adk.dev/get-started/about/
- **LiteLLM:** the `LiteLlm(model="openai/gpt-4o")` wrapper requires `litellm>=1.84`. Anthropic thinking-block signatures are preserved since 1.28.0. https://adk.dev/agents/models/litellm/
- **LiteLLM security advisory:** the same page warns that LiteLLM 1.82.7 and 1.82.8 were compromised in March 2026.
- **Claude in Python:** native only via Agent Platform (Vertex). The direct Anthropic API goes through LiteLLM. Java has a native `Claude` wrapper. https://adk.dev/agents/models/anthropic/
- **OpenAI:** native in Go only (experimental). Python uses LiteLLM. https://adk.dev/agents/models/openai/ (An `openai` extra exists on PyPI; its purpose is unverified.)
- **Failover:** `FallbackModel` was added in 2.9.0. https://github.com/google/adk-python/releases
- **Eval judges and simulators:** these default to Gemini (`gemini-flash-latest`). https://adk.dev/evaluate/criteria/

## 7. Tools

- **Tool types:** function tools, OpenAPI tools, built-in Gemini tools (Search grounding, code exec), and auth via `auth_scheme` / `auth_credential` with OAuth refresh. https://adk.dev/ , https://adk.dev/tools-custom/mcp-tools/
- **MCP client:** `McpToolset` supports stdio, SSE and Streamable HTTP. The docs advise: "Always supply `tool_filter=[...]`" (least privilege). MCP connections are not restored with sessions. https://adk.dev/tools-custom/mcp-tools/
- **MCP server:** `to_mcp_server` exposes an agent. Same URL.
- **MCP SDK 2.x:** supported since 2.9.0. https://github.com/google/adk-python/releases
- **Least-privilege extras:** the Tool Call Integrity plugin signs function calls, and a Model Armor plugin is available. https://adk.dev/plugins/

## 8. Multi-agent and A2A

- **Patterns:** sub_agents/transfer, AgentTool, workflow agents, and graphs (navigation on https://adk.dev/).
- **A2A install:** `pip install google-adk[a2a]`.
- **Server side:** `to_a2a(root_agent, port=...)` auto-generates the agent card at `/.well-known/agent-card.json`. `adk api_server --a2a` is an alternative.
- **Client side:** `RemoteA2aAgent`.
- **SDK versions:** works with `a2a-sdk` 0.3.x (compat mode) and 1.x.
- **Status:** **labelled experimental**. Warnings can be suppressed with `ADK_SUPPRESS_A2A_EXPERIMENTAL_FEATURE_WARNINGS`. https://adk.dev/a2a/quickstart-exposing/
- **Recent A2A changes:** native task mode in `RemoteA2aAgent` (2.8.0). 2.8.0 also had churn: "reject tool confirmations arriving over A2A" was later reverted. https://github.com/google/adk-python/releases/tag/v2.8.0
- **Language coverage:** Python, Go, Java and Kotlin. https://adk.dev/a2a/intro/

## 9. Observability

- **Native OTel:** ADK "implements the OpenTelemetry (OTel) Semantic Conventions for GenAI" and exports OTLP. https://adk.dev/observability/traces/
- **Span names:** `invoke_agent`, `invoke_workflow`, `execute_tool`, `generate_content`.
- **Attributes:** `gen_ai.*`. The semconv version is not stated.
- **Any OTLP backend:** set `OTEL_EXPORTER_OTLP_(TRACES_)ENDPOINT`.
- **Cloud Trace:** opt in with `--otel_to_cloud` or `get_gcp_exporters()`.
- **Content-capture flag for Python:** not documented (Kotlin has one).
- **Inference:** not coupled to Cloud Trace, since the backend is exporter config.
- **2.9.2 fix:** OTel event names are now kept outside Agent Engine. https://github.com/google/adk-python/releases

## 10. Testing and evals

- **Formats:** `*.test.json` files (unit-style) and evalsets (multi-session).
- **pytest:** `await AgentEvaluator.evaluate(agent_module, path)`.
- **CLI:** `adk eval`.
- **Config:** `test_config.json` criteria. https://adk.dev/evaluate/
- **Trajectory matching:** `tool_trajectory_avg_score` with **`match_type` EXACT (default) / IN_ORDER / ANY_ORDER**. These map one-to-one to the pipeline modes. https://adk.dev/evaluate/criteria/
- **Other criteria:** ROUGE, LLM-judge, rubrics, hallucination and safety. Several need Vertex / GCP. Efficiency metrics are informational only.
- **Repeated runs:** `num_runs` defaults to 2, but **scores are averaged across runs** (`mean(scores) >= threshold`). That is pass@avg, **not pass^k**. https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/evaluation/agent_evaluator.py
- **Inference:** pass^k needs your own harness over per-run results.
- **Since 2.10.0:** raises `ValueError` if no cases run. https://github.com/google/adk-python/releases
- **User simulation:** available, but the trajectory and response-match criteria are unsupported with it. https://adk.dev/evaluate/
- **Model and tool doubles:** "Environment Simulation" (experimental, 1.24.0+) supports injected responses and errors or LLM-mocked tools, via callback or plugin. https://adk.dev/evaluate/environment_simulation/
- **Model-double alternative:** a `before_model_callback` returning `LlmResponse` skips the LLM. https://adk.dev/callbacks/types-of-callbacks/

## 11. Deployment

- **Self-hosted:** `adk api_server` (FastAPI; `/run`, `/run_sse`, session CRUD). https://adk.dev/runtime/api-server/
- **Custom app:** `get_fast_api_app(agents_dir, session_service_uri, allow_origins, web)`, run with uvicorn. A sample Dockerfile is provided. https://adk.dev/deploy/cloud-run/
- **Docker/Podman anywhere:** explicitly supported, including offline. https://adk.dev/deploy/
- **Inference:** this is how VPS Docker Compose and AWS ECS/App Runner would work. No AWS page exists.
- **GCP options:** `adk deploy cloud_run` (`--session_service_uri`, `--with_ui`, gcloud passthrough), GKE, and Agent Runtime (ex-Agent Engine, now "Agent Platform"). Agent Runtime supports Python and Go, and the Python payload excludes the API server. https://adk.dev/deploy/cloud-run/ , https://adk.dev/deploy/agent-runtime/
- **Agent Runtime pricing:** the docs only say it is paid above a no-cost tier (https://adk.dev/deploy/agent-runtime/). Third-party figures put it around $0.0864/vCPU-h, $0.0090/GiB-h, 50 vCPU-h free, and Sessions/Memory Bank around $0.25 per 1k events (**unverified**; Google's pricing page was too large to fetch).

## 12. When to pick / when not

**Pick ADK when:**
- the team is on Gemini or GCP;
- you want first-party eval with EXACT/IN_ORDER/ANY_ORDER trajectory matching;
- you want native OTel GenAI spans, graph workflows mixing code and LLM, or A2A plus MCP in one framework;
- you need multi-language parity (Py/TS/Go/Java).

**Avoid ADK when:**
- the primary model is Claude or OpenAI over direct APIs (Python goes through LiteLLM, and judges and simulators default to Gemini);
- you need Firestore or DynamoDB sessions in Python;
- you need durable HITL on a DB-backed session today (the confirmation doc says it is unsupported);
- you cannot absorb weekly releases that ship breaking changes in minors.

**Churn evidence:**
- the 2.0 rewrite to a graph runtime, with a session schema change;
- breaking entries in 2.7.0, 2.9.0 and 2.11.0;
- a schema migration in 1.22.0;
- the docs domain moved to adk.dev;
- the GCP product was renamed (Agent Engine to Agent Runtime / Agent Platform).

## 13. Verdict

Inference, based on the facts above. ADK fits the pipeline seams better than most frameworks on **observability** (OTel GenAI semconv, any OTLP backend), **eval** (trajectory modes match EXACT/IN_ORDER/ANY_ORDER natively, and pytest runs `AgentEvaluator`), **MCP** (client with `tool_filter`, plus server), **A2A** (first-party, but experimental) and **deploy** (FastAPI container on a VPS or AWS, plus Cloud Run and Agent Runtime). The weak seams need adapter code:

- **Sessions:** Postgres, Supabase and Cloud SQL work natively. DynamoDB and Python Firestore need a custom `BaseSessionService`, which suits the pipeline's repository interface but must track 2.0 Event schema changes.
- **HITL:** tool confirmation is experimental and documented as unsupported on DB/Vertex sessions, so the gate must be verified on Postgres or implemented as plugin plus `RequestInput` plus your own approval store.
- **Tool-call cap:** must be a custom plugin.
- **pass^k:** must come from the harness, since ADK averages across runs.
- **Model swap:** works via LiteLLM, but with Gemini gravity in judges and simulators.

Net: a viable choice when the target leans GCP/Gemini, and an acceptable one elsewhere if you pin exact versions and own those four adapters.
