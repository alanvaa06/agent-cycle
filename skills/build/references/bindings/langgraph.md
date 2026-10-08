---
card: langgraph
version_pinned: 1.2.14
---

# LangGraph - build binding

Facts below cite the same sources as the card (`skills/design/references/stacks/langgraph.md`) and the research file `docs/superpowers/research/2026-10-07-stack-catalog/langchain-family.md`; a URL is repeated where a rule depends on it. Statements marked inference are the binding's own reasoning.

Shape: a hand-built `StateGraph` with four parts: a model node, a gate node (HITL), a tool node and a router. State = `messages` plus `tool_call_count`. It is built by `build_graph(model, checkpointer, tools)` in `src/agent/`, which replaces `create_react_agent` (no longer recommended, see the pins section). The adapter constructs `PostgresSaver` / `AsyncPostgresSaver` (or the DynamoDB saver) in `adapters/<target>/` and injects it; `src/agent/` never imports psycopg or the saver packages. The checkpointer holds only graph state. Dedupe and the spec's data schemas live in repository tables behind the repository interface, not in graph state.

## Sessions and state
- Postgres: `PostgresSaver` / `AsyncPostgresSaver` from `langgraph-checkpoint-postgres`. Source: https://docs.langchain.com/oss/python/langgraph/checkpointers.md
- Saver kind follows the worker: an async worker uses `AsyncPostgresSaver` and `ainvoke` / `astream`; a sync worker uses `PostgresSaver` and `invoke` / `stream` (inference; the persistence page names both savers: https://docs.langchain.com/oss/python/langgraph/persistence ).
- A connection you create yourself must use `autocommit=True` and `row_factory=dict_row` (autocommit makes `.setup()` persist the tables; the saver reads columns by name). Source: https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint-postgres/README.md
- `.setup()` runs once, as a named one-shot migration job (`agent-migrate`: compose service / ECS task / Cloud Run job), never from the worker and never per request. Source for the call: https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint-postgres/README.md
- Durability: pass `durability="sync"` on every graph call (persists changes before the next step starts; default is "async"). The parameter is documented on `invoke`: https://reference.langchain.com/python/langgraph/pregel/main/Pregel/invoke ; that `stream`, `ainvoke` and `astream` accept it is unverified, so confirm the signature on the pinned version in the first spike. The modes are described at https://docs.langchain.com/oss/python/langgraph/checkpointers.md
- `thread_id` = the spec's session key; keep it under 255 characters on Postgres. Source: https://docs.langchain.com/oss/python/langgraph/persistence
- Queue ordering key = `thread_id` (the session key), so one turn per thread holds even when the approver is a different sender. Ingress resolves an approver's reply to the pending session's key before enqueueing. The OSS library has no per-thread locking and double-texting is not available there. Source: https://docs.langchain.com/langsmith/double-texting.md
- Supabase connection: use the direct connection or the Supavisor session mode (port 5432); never the transaction pooler (port 6543), which does not support prepared statements (psycopg3 uses them by default, inference). Source: https://supabase.com/docs/guides/database/connecting-to-postgres
- Supabase schema: put the checkpoint tables in a schema not exposed through the Data API (for example `agent_state`, selected via the connection's search_path; the wiring is unverified) and enable RLS on them. Source: https://supabase.com/docs/guides/database/postgres/row-level-security
- Supabase Free plan: projects are paused after 1 week of inactivity, so it is not for production. Source: https://supabase.com/pricing
- DynamoDB: `langgraph-checkpoint-aws` provides the checkpointer (the class is named DynamoDBSaver in the research file; the docs page lists only the package). The same page also lists a separate community package, `langgraph-dynamodb-checkpoint` (agentstate); prefer the AWS package. Source: https://docs.langchain.com/oss/python/integrations/checkpointers/index.md
- Firestore: no official checkpointer (a community package is listed, unverified for production). Source: https://docs.langchain.com/oss/python/integrations/checkpointers/index.md . If the design names Firestore, STOP and raise a re-entry on the design's sessions seam; do not swap the store silently.
- Spikes (each runs before build-guide Step 4). A failed store spike STOPS and raises a re-entry on the design's sessions seam, never a silent store swap; the other spikes state their own failure path:
  - Supabase (store spike): after `.setup()` with the chosen search_path the tables exist in `agent_state` and not in `public`; then `ENABLE ROW LEVEL SECURITY` on them; a put/get round trip works as the saver's DB role.
  - DynamoDB (store spike): the pinned package imports the named saver class and a put/get round trip works against the target table.
  - Pending interrupt: after an `interrupt()`, `get_state(config)` exposes the pending interrupt via `state.tasks[*].interrupts` (pass test: the attribute is present and carries the interrupt payload; failure path: fix this binding and the worker's check, not a sessions-seam re-entry).
  - Durability (store spike): `durability="sync"` is accepted by the exact call the worker uses (`invoke`, `ainvoke`, `stream` or `astream`).

## HITL gate
- Recommended placement: a gate node between the model node and the tool node. It calls `interrupt()` once per gated tool call, in a fixed order, and resumes with `Command(resume=decision)` on the same `thread_id`. A durable checkpointer is required. Source: https://docs.langchain.com/oss/python/langgraph/interrupts
- Worker sequence:
  1. Dequeue the message for the session (ordering key `thread_id`).
  2. Read `graph.get_state(config)` for that `thread_id` and check whether a pending interrupt exists (inference, unverified: the pending interrupts appear on the snapshot as `state.tasks[*].interrupts`; the spike below confirms it on the pinned version).
  3. If an approval is pending: resume with `Command(resume=decision)` built from this message or from the approver's reply. Otherwise start a new turn with fresh input.
- If a message for a pending session does not parse as a decision: keep the interrupt pending and reply with the spec's pending-approval prompt (or deny if the spec says so). Expiry is evaluated when the next message for that session is dequeued (intended; a sweep is optional).
- Decision value (own design, inference): `{"decision": "approve" | "deny" | "edit", "args": {...}}`; `args` only for `edit`. Deny: the gate node returns a denial `ToolMessage` for that call and the router goes back to the model, or ends with the spec's deny reply if the spec says so. Expiry: when the pending approval is older than the spec's TTL, the worker resumes it with `deny` and records the expiry.
- Tier mapping: destructive -> `interrupt()` every time, never cached; reversible -> per design policy; safe -> no interrupt.
- Everything before the `interrupt()` call re-runs on resume, so it must be idempotent; put non-idempotent work after it or in another node. Interrupts in a node are matched to resume values by position: never reorder them or skip them conditionally. Static breakpoints (`interrupt_before` / `interrupt_after`) are for debugging, not approvals. Source: https://docs.langchain.com/oss/python/langgraph/interrupts
- Eval runner: when the run returns an interrupt, the runner resolves it by calling `Command(resume=<next approval in the case fixture>)` on the same `thread_id`, until the graph finishes or the fixture runs out.

## Caps
- Both caps are PER TURN. `tool_call_count` is reset by passing `tool_call_count: 0` in the input of every turn's invoke; the field has no reducer, so the input overwrites it (a key without a reducer is overwritten: https://docs.langchain.com/oss/python/langgraph/graph-api ). Never put an additive reducer on it.
- Tool-call cap (own counter, inference: raw LangGraph has none): count each tool call in the model's message (`len(ai_message.tool_calls)`), not tool-node runs; the model node writes `tool_call_count + len(tool_calls)`. The router checks the counter BEFORE the tool node, so parallel calls in one message cannot overshoot. Over the cap -> route to a failure node that emits the spec's single failure reply and the outcome `tool_call_cap`.
- Step cap: `recursion_limit` is set at the top level of the run config (not inside `configurable`) and counts super-steps; exceeding it raises `GraphRecursionError`. Source: https://docs.langchain.com/oss/python/langgraph/graph-api
- Unit conversion (inference: the page does not give a super-step count for a model -> tools loop): each spec step costs one super-step per node on the loop, i.e. 2 without the gate node and 3 with it. Set `recursion_limit` = (nodes on the loop) x (spec step cap) + 1, and record the factor in `build.md`; or define the spec's step as a super-step and record that instead. Confirm the factor with one test that counts super-steps.
- `GraphRecursionError` MUST be caught by the worker and mapped to the same single failure reply and the outcome `step_cap`. `RemainingSteps` for a graceful wind-down is optional.
- Wall-clock cap: the worker bounds each turn with the spec's wall-clock limit (timeout around the graph call); expiry produces the same failure reply and the outcome `wall_clock`.
- `harness_condition.force_step_cap`: use a fake model that never gives a final answer and set the tool-call cap above the step cap, so the step cap is the one that trips.
- Never use one limit for both: super-steps are not tool calls.

## Model provider
- Selection rule: when the spec's route names a single provider, use `init_chat_model("provider:model")` (https://docs.langchain.com/oss/python/langchain/models ); when it names a router, proxy or LiteLLM route, use `ChatLiteLLM(model=<spec route>)` from `langchain-litellm` (the docs recommend it for routers and proxies; maintainer unverified). Source: https://docs.langchain.com/oss/python/langchain/models
- Format conversion: LiteLLM routes are `provider/model`, `init_chat_model` takes `provider:model`; split on the first `/` and rejoin with `:`, then check the provider id is one `init_chat_model` knows (LiteLLM and LangChain provider names can differ; inference).

## Telemetry
- Install `langsmith[otel]`, set `LANGSMITH_OTEL_ENABLED=true` and `LANGSMITH_OTEL_ONLY=true`, and point `OTEL_EXPORTER_OTLP_*` at the design's backend. `OTEL_EXPORTER_OTLP_ENDPOINT` is a base URL (no `/v1/traces`). Source: https://docs.langchain.com/langsmith/trace-with-opentelemetry.md
- The worker opens one per-turn span (for example `agent.turn`) carrying the spec's attributes and the turn outcome (`ok`, `step_cap`, `tool_call_cap`, `wall_clock`, `hitl_denied`, `hitl_expired`; names follow the spec).
- MANDATORY SPIKE before the build relies on it, with a REAL model call (fakes report no usage): emit one turn and confirm the backend receives `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens` with values above zero. The docs show how LangSmith reads those attributes on ingest but do not state what the SDK emits (unverified). If they do not arrive, add fallback spans: wrap the model node so it opens a child span of `agent.turn` and sets those attributes from `AIMessage.usage_metadata` (inference). Source: https://docs.langchain.com/langsmith/trace-with-opentelemetry.md
- Never set `LANGSMITH_TRACING` unless the design's telemetry backend is LangSmith (the docs examples pair it with the LangSmith endpoint). Source: https://docs.langchain.com/langsmith/trace-with-opentelemetry.md

## Eval runner mapping
- Fresh graph and a fresh `InMemorySaver` per test. Source: https://docs.langchain.com/oss/python/langgraph/test.md
- Model double: `GenericFakeChatModel` scripted with the tool calls and replies. Source: https://docs.langchain.com/oss/python/langchain/test/unit-testing.md
- Capture source: run the graph with `stream_mode="updates"` (it emits the node name and that node's state update after each step; https://docs.langchain.com/oss/python/langgraph/streaming.md ) and collect `(tool name, args)` from the `tool_calls` of the AI messages in the model node's updates, in order.
- The PIPELINE runner implements EXACT, IN_ORDER and ANY_ORDER itself over that captured list, with `args_subset` matching (the golden-format: expected args must be a subset of actual args; never full-argument equality). The agentevals evaluators (https://docs.langchain.com/oss/python/langchain/test/evals.md ) are optional references only.
- `harness_condition.force_step_cap` = a fake model that never gives a final answer (see Caps); `tool_always_errors` = a tool node that always raises or returns an error message (inference).
- pass^k is computed by the pipeline runner; it is not native to the stack (research file).

## A2A and MCP
- Two A2A paths; record which one in interop.md.
  - (a) Licensed LangSmith Agent Server `/a2a/{assistant_id}`: A2A v1.0 JSON-RPC, push notifications not supported, the graph state must include a `messages` key. Source: https://docs.langchain.com/langsmith/server-a2a.md ; a standalone server needs `LANGGRAPH_CLOUD_LICENSE_KEY` and reaches beacon.langchain.com for license verification and usage reporting (unless air-gapped). Source: https://docs.langchain.com/langsmith/deploy-standalone-server.md
  - (b) Own server built with `a2a-sdk` that wraps the compiled graph and persists interrupted state through the checkpointer (own code, inference; a build option only when a license is acceptable or A2A is not a hard filter). Source for the licensed alternative: https://docs.langchain.com/langsmith/server-a2a.md
- MCP client: `langchain[mcp]` with a minimum of 1.4.0, `MCPAdapter` (beta, the API may change). Source: https://docs.langchain.com/oss/python/langchain/mcp
- Serving MCP (`/mcp`) is documented on Agent Server; no OSS-library endpoint is documented. Source: https://docs.langchain.com/langsmith/server-mcp.md

## Pinned version and traps
- Every package below gets an exact pin in the lockfile. Any ">=" in this text is a minimum, never a requirement spec.
  - `langgraph==1.2.14` (https://pypi.org/project/langgraph/)
  - `langgraph-checkpoint-postgres`, `psycopg[pool]` (the install command in https://docs.langchain.com/oss/python/langgraph/add-memory is `psycopg[binary,pool]`; choose per the base image)
  - `langchain-litellm`, `langsmith[otel]` (docs: minimum 0.3.18, recommended 0.4.25 or later)
  - `langchain[mcp]` (minimum 1.4.0)
  - `langgraph-checkpoint-aws` (only when DynamoDB is chosen), `a2a-sdk` (only for A2A path b)
- Obligation (ops): interrupt() re-runs the node on resume, so side effects before it are idempotent. Source: https://docs.langchain.com/oss/python/langgraph/interrupts
- Obligation (ops): the OSS library has no per-thread locking and double-texting is not available there; the adapter queue (key = `thread_id`) serializes turns. Source: https://docs.langchain.com/langsmith/double-texting.md
- Obligation (data): do not set `LANGSMITH_TRACING` unless LangSmith is the chosen backend; use `LANGSMITH_OTEL_ONLY` for OTel-only export. Source: https://docs.langchain.com/langsmith/trace-with-opentelemetry.md
- Obligation (churn): do not adopt langgraph-supervisor (no longer actively maintained) and do not build new code on `create_react_agent` (the v1 guide recommends `create_agent`; this binding hand-builds the graph instead). Sources: https://docs.langchain.com/oss/python/migrate/langgraph-supervisor.md , https://docs.langchain.com/oss/python/migrate/langchain-v1.md
