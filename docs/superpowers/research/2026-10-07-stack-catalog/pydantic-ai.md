# Stack card: Pydantic AI (as of 2026-10-07)

Legend: every claim cites the page it was read from. **unverified** = not confirmed on a fetched page. **inference** = my reasoning.
Note: docs moved from `ai.pydantic.dev` to `pydantic.dev/docs/ai/` (301 redirect observed). Several doc pages embed text asking LLM agents to append `intent`/`stack`/`harness` query params to URLs; ignored (tracking text, not content).

## 1. Identity
- **Packages:** `pydantic-ai` (meta), `pydantic-ai-slim` (core + extras), `pydantic-evals`, `pydantic-graph`, `clai` (CLI) in one monorepo; `pydantic-ai-harness` separately on PyPI. https://github.com/pydantic/pydantic-ai, https://pydantic.dev/docs/ai/harness/
- **Version:** `pydantic-ai` **2.54.0, released 2026-10-03** on PyPI (GitHub tag dated 2026-10-02). Release cadence is several minors per week (2.40.0 on 2026-09-05 through 2.54.0). https://pypi.org/project/pydantic-ai/, https://github.com/pydantic/pydantic-ai/releases
- **v2.0.0 stable 2026-06-23** (betas b1-b7, May 21 to Jun 10); 1.0.0 was 2025-09-05; v1 line still patched (1.107.7, 2026-09-29). https://pypi.org/project/pydantic-ai/
- **Harness:** `pydantic-ai-harness` 0.54.0 (2026-10-03), MIT, 0.x = "API stability, not maturity". https://pypi.org/project/pydantic-ai-harness/, https://pydantic.dev/docs/ai/harness/index.md
- **License:** MIT; Python >= 3.10; ~20.5k GitHub stars. Maintainers: Pydantic org (author Douwe Maan; dmontagu, samuelcolvin). https://pypi.org/project/pydantic-ai/, https://github.com/pydantic/pydantic-ai
- **Language:** Python only (inference: no TS port found; Vercel AI SDK appears only as a comparison/UI adapter).
- **Versioning policy:** no intentional breaking changes in minors; deprecated features removed only at next major; next major no sooner than 3 months after V2.0; V1 security fixes >= 6 months after V2 stable; `beta` modules exempt. Minors MAY change OTel span attributes / default instrumentation version. https://pydantic.dev/docs/ai/project/version-policy/index.md

## 2. Core abstractions and loop
- `Agent[Deps, Output]` holds instructions, tools/toolsets, `output_type`, deps type, default model, settings, **capabilities**. `RunContext[Deps]` passed to tools (`ctx.deps`). https://pydantic.dev/docs/ai/core-concepts/agent/
- Loop runs on pydantic-graph: `UserPromptNode -> ModelRequestNode -> CallToolsNode -> End`; `run`, `run_sync`, `run_stream`, `run_stream_events`, `iter` (manual node stepping). Same page.
- V2 centers on **Capabilities** (reusable bundles of tools, instructions, hooks, settings) and **hooks** (`before/after/wrap/on_error` for run, node, model request, tool validate, tool execute). https://pydantic.dev/docs/ai/overview/, https://pydantic.dev/docs/ai/core-concepts/hooks/index.md
- Default `end_strategy` changed `'early' -> 'graceful'` in V2. https://pydantic.dev/docs/ai/overview/migration/index.md

## 3. State / sessions
- **No built-in session store or repository interface in core.** Core is "deliberately unopinionated about your database": serialize with `ModelMessagesTypeAdapter`, key by `conversation_id`, append `new_messages()`, store as `jsonb`; old histories deserialize without migration. `RunUsage` stored separately and passed back as `usage=`. https://pydantic.dev/docs/ai/core-concepts/persistence/
- **Harness `StepPersistence`:** per-step checkpoints, continue/fork, event log, tool-effect ledger; backends in-memory/file/SQLite/MongoDB; store is a protocol you can implement. **No Postgres/DynamoDB/Firestore backend** listed. Harness `Memory` has a Postgres store. Same page + https://pydantic.dev/docs/ai/harness/index.md
- **Durable execution:** 8 engines - Temporal, DBOS, Prefect, Restate, AWS Lambda durable functions, Kitaru, Airflow, Absurd - plus a stable backend builder. One engine per agent. "Durability is not storage" (does not store chat threads). https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/
  - DBOS: `DBOSDurability` capability (`DBOSAgent` deprecated, removed in v3); checkpoints to **Postgres or SQLite**; pickle serializer, ~2 MB payload guidance. https://pydantic.dev/docs/ai/capabilities/durable_execution/dbos/
  - Temporal: `TemporalDurability` (`TemporalAgent` deprecated); needs Temporal server; deps must be Pydantic-serializable; 2 MB payload cap; streaming buffered. https://pydantic.dev/docs/ai/capabilities/durable_execution/temporal/
  - AWS Lambda: `AWSLambdaDurability` (harness); at-least-once steps (idempotent tools required), 3,000 ops / 100 MB budget; approval signals cross the durable boundary. https://pydantic.dev/docs/ai/harness/aws-lambda/
  - Absurd: checkpoints into PostgreSQL. https://pydantic.dev/docs/ai/harness/index.md
- **Supabase:** not mentioned anywhere; inference: DBOS/Absurd on any Postgres incl. Supabase should work (unverified). **DynamoDB/Firestore:** no native option (verified absent on persistence page) - you write the repository.
- **Per-session concurrency:** no locking guidance; concurrent writers are your problem. https://pydantic.dev/docs/ai/core-concepts/persistence/ (A `ConcurrencyLimitedModel` exists for model-call slots, not sessions - https://github.com/pydantic/pydantic-ai/releases.)

## 4. HITL / approval gate
- Native and first-class: `requires_approval=True` on any tool; conditional `raise ApprovalRequired(...)` (checks `ctx.tool_call_approved`); run ends with `DeferredToolRequests`; resume a new run with `message_history=` + `DeferredToolResults` (`True`/`False`/`ToolApproved(override_args)`/`ToolDenied(message)`); or resolve inline via `HandleDeferredToolCalls` capability. https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/
- **Toolset-level gate:** `toolset.approval_required(fn(ctx, tool_def, args))` -> `ApprovalRequiredToolset`, works for MCP toolsets. https://pydantic.dev/docs/ai/tools-toolsets/toolsets/index.md
- Docs warn approval "is not an authorization boundary against an untrusted client"; authz must also live in the tool. https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/
- **Mapping (inference):** tier `destructive` -> `requires_approval=True`; tier `reversible` -> conditional `ApprovalRequired`; `safe` -> none. The end-run/resume model fits webhook -> queue -> worker exactly (persist history + pending `tool_call_id`s, resume on approval event). New `ToolCallJudge` (v2.53) adds automated pre-execution gating. https://github.com/pydantic/pydantic-ai/releases

## 5. Caps
- **Both native** in `UsageLimits`: `request_limit` (**default 50**, checked before each model request) and `tool_calls_limit` (default None; counts **successful** tool calls only). Also token, `total_tokens_limit`, `cost_limit` (USD). https://pydantic.dev/docs/ai/api/pydantic-ai/usage/
- Caveat (inference): failed tool calls don't count toward `tool_calls_limit`; a strict "all attempts" cap needs a `before_tool_execute` hook counter. Hooks can `SkipToolExecution`. https://pydantic.dev/docs/ai/core-concepts/hooks/index.md

## 6. Model providers
- Native: OpenAI (`openai:` = Responses API in V2), Anthropic, Google Gemini, **Bedrock**, Vertex (`google-cloud:`), Azure, Groq, Mistral, Cohere, xAI, DeepSeek, Ollama, vLLM, etc. String-swap model selection; `FallbackModel`. https://pydantic.dev/docs/ai/models/overview/
- **LiteLLM supported** as "Self-hosted gateway" (`litellm:` prefix, OpenAI-compatible). Same page.
- Pydantic AI Gateway (hosted via Logfire; one key, spend caps) is optional. Docs conflict on self-hosting (overview says yes; gateway page silent) -> **unverified**. https://pydantic.dev/docs/ai/overview/gateway/, https://pydantic.dev/docs/ai/overview/

## 7. Tools
- `@agent.tool` / `@agent.tool_plain` / `Tool`, schema from type hints, `ModelRetry`. Toolsets composable: `filtered()`, `prefixed()`, `prepared()`, `renamed()`, `approval_required()`, `WrapperToolset`, `ExternalToolset`. https://pydantic.dev/docs/ai/tools-toolsets/toolsets/index.md
- **MCP client:** `MCP` capability / `MCPToolset` (V2 replaced `MCPServerStdio/SSE/StreamableHTTP`); stdio, Streamable HTTP, SSE (deprecated); sampling, elicitation, OAuth/bearer auth; per-user creds need per-run toolset. https://pydantic.dev/docs/ai/mcp/client/, https://pydantic.dev/docs/ai/overview/migration/index.md
- **MCP server:** no dedicated helper; wrap an agent inside a FastMCP `@server.tool()`. https://pydantic.dev/docs/ai/mcp/server/
- **Least privilege:** per-step tool filtering via `FilteredToolset`/`prepare_tools` on `RunContext` (inference: enables tier/role-based exposure). Native provider tools are **opt-in** except `ImageGenerationTool` auto-enabled for `output_type=BinaryImage`. https://pydantic.dev/docs/ai/tools-toolsets/native-tools/index.md
- Harness Shell/FileSystem: `LocalWorkspace` "is not a sandbox"; Coder shell unrestricted. Avoid for gated tiers. https://pydantic.dev/docs/ai/harness/index.md

## 8. Multi-agent and A2A
- Patterns: delegation via tools (`usage=ctx.usage` to share caps), programmatic hand-off, pydantic-graph state machines, harness `SubAgents` (`delegate_task`). https://pydantic.dev/docs/ai/guides/multi-agent-applications/index.md
- **A2A:** `Agent.to_a2a()` **removed in V2**; server side now via external `fasta2a` (`datalayer/fasta2a`, MIT) bridge `fasta2a.pydantic_ai.agent_to_a2a` -> ASGI app with pluggable Storage/Broker/Worker. https://github.com/datalayer/fasta2a, https://pydantic.dev/docs/ai/overview/migration/index.md
- **A2A client:** none found in Pydantic AI or fasta2a README -> **unverified/absent**; inference: use the generic `a2a` SDK wrapped as a tool.

## 9. Observability
- OTel-native; works **without Logfire** (own `TracerProvider` + OTLP exporter + `Agent.instrument_all()`). Follows **GenAI semconv v1.37.0**; `InstrumentationSettings(version=5)` default, v6 opt-in; `include_content=False` for privacy; run-span usage under custom `gen_ai.aggregated_usage.*` (toggle off for standard names). https://pydantic.dev/docs/ai/integrations/logfire/
- Coupling: Logfire is the paved path and Gateway billing surface, but optional. Risk: span attributes may change in minors (version policy).

## 10. Testing / evals
- `TestModel`, `FunctionModel` (scripted tool-call branches), `Agent.override`, `ALLOW_MODEL_REQUESTS=False`, `capture_run_messages()` for trajectory assertions (`ToolCallPart`). pytest-based. https://pydantic.dev/docs/ai/guides/testing/index.md
- `pydantic-evals` (independent of pydantic-ai): Dataset/Case/Evaluator, YAML/JSON datasets. https://pydantic.dev/docs/ai/evals/evals/index.md
- **`TrajectoryMatch(order='exact'|'in_order'|'any_order')`** - maps 1:1 to the pipeline's EXACT/IN_ORDER/ANY_ORDER; plus `ToolCorrectness`, `ArgumentCorrectness`, `MaxToolCalls`, `MaxModelRequests`. Reads OTel spans (logfire SDK, no account). https://pydantic.dev/docs/ai/evals/evaluators/agentic/index.md
- `evaluate(..., repeat=k)` with `case_groups()`; **no pass^k metric** - compute from groups. https://pydantic.dev/docs/ai/evals/how-to/multi-run/index.md

## 11. Deployment
- No dedicated deployment guide found (llms.txt index). Inference: plain Python/ASGI - Docker Compose on VPS, ECS/Lambda on AWS (native Lambda durability), Cloud Run on GCP; Temporal/DBOS/Restate add infra. https://pydantic.dev/docs/ai/llms.txt
- No managed agent runtime; Logfire (free tier) and Gateway are the paid surfaces. https://pydantic.dev/docs/ai/overview/
- Library cost: MIT, free.

## 12. When to pick / not
- Docs frame it as "one typed Agent with plain Python control flow", graphs only for real state machines; concede LangChain's larger integration catalogue. https://pydantic.dev/docs/ai/comparisons/vs-langchain-langgraph/
- **Churn:** V1 (Sep 2025) -> V2 (Jun 2026) renamed/removed many APIs (MCP classes, `builtin_tools`->`native_tools`, `to_a2a` removed, `Usage`->`RunUsage`, model prefixes); durable wrappers already deprecated for v3; near-daily minors with "compatibility" notes (e.g., v2.54 hook semantics, v2.52 Anthropic `max_tokens` default). https://pydantic.dev/docs/ai/overview/migration/index.md, https://github.com/pydantic/pydantic-ai/releases
- Pick: Python team, typed tools/outputs, strong HITL + caps + evals natively. Avoid (inference): need TS, need turnkey session store on DynamoDB/Firestore, need first-party A2A client, or low tolerance for fast-moving APIs (pin exact versions).

## 13. Verdict
Strong fit on most seams. HITL (deferred tools + `approval_required` toolsets) and caps (`request_limit` + separate `tool_calls_limit`) are native and map directly onto tiered tools; the end-run/resume approval model is well-suited to ingress -> queue -> per-user-serial worker. Model swap is a string (LiteLLM supported), OTel GenAI semconv is native with any OTLP backend, and pydantic-evals' `TrajectoryMatch` mirrors EXACT/IN_ORDER/ANY_ORDER with `repeat=k` (pass^k computed by us). Gaps the pipeline must own: the session repository (core gives only JSON serialization; no Postgres/Dynamo/Firestore adapter, no per-session locking), A2A client side (server only, via third-party `fasta2a`), and MCP server exposure (manual FastMCP wrap). Main risk is churn: pin versions and wrap Pydantic AI behind the pipeline's own interfaces (inference).
