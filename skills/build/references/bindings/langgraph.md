---
card: langgraph
version_pinned: 1.2.14
---

# LangGraph - build binding

Facts below cite the same sources as the card (`skills/design/references/stacks/langgraph.md`); a URL is repeated where a rule depends on it.

## Sessions and state
- Postgres: `PostgresSaver` / `AsyncPostgresSaver` from `langgraph-checkpoint-postgres` (pin it). Source: https://docs.langchain.com/oss/python/langgraph/checkpointers.md
- A connection you create yourself must use `autocommit=True` and `row_factory=dict_row` (autocommit makes `.setup()` persist the tables; the saver reads columns by name). Source: https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint-postgres/README.md
- Call `.setup()` once, as the migrations step of the deploy recipe, not per request. Source: https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint-postgres/README.md
- Run with `durability="sync"` (persists before the next step starts; highest durability). Source: https://docs.langchain.com/oss/python/langgraph/checkpointers.md
- `thread_id` = the spec's session key; keep it under 255 characters on Postgres. Source: https://docs.langchain.com/oss/python/langgraph/persistence
- Concurrency: the OSS library has no per-thread locking, so the adapter's per-sender queue must guarantee one turn per thread. Source: https://docs.langchain.com/langsmith/double-texting.md
- Supabase: use the direct connection or the Supavisor session mode (port 5432); never the transaction pooler (port 6543), which does not support prepared statements (psycopg3 uses them by default, inference). Source: https://supabase.com/docs/guides/database/connecting-to-postgres
- Supabase schema: put the checkpoint tables in a schema that is not exposed through the Data API (for example `agent_state`, selected via the connection's search_path; the search_path wiring is unverified, so confirm it with a spike) and enable RLS on them. Source: https://supabase.com/docs/guides/database/postgres/row-level-security
- Supabase Free plan: projects are paused after 1 week of inactivity, so it is not for production. Source: https://supabase.com/pricing
- DynamoDB: `langgraph-checkpoint-aws` provides the checkpointer (the class is named DynamoDBSaver in the research digest; the docs page lists only the package, so confirm the class name when you pin the package). The same page also lists a separate community package, `langgraph-dynamodb-checkpoint` (agentstate); prefer the AWS package and confirm either with a spike. Source: https://docs.langchain.com/oss/python/integrations/checkpointers/index.md
- Firestore: no official checkpointer (a community package exists, unverified for production); on GCP use Cloud SQL Postgres. Source: https://docs.langchain.com/oss/python/integrations/checkpointers/index.md

## HITL gate
- Put `interrupt()` inside the gated tool, or in a gate node placed before it; approval resumes with `Command(resume=decision)` on the same `thread_id`. A durable checkpointer is required. Source: https://docs.langchain.com/oss/python/langgraph/interrupts
- The whole node re-runs on resume: everything before the `interrupt()` call must be idempotent; put non-idempotent work after it or in a separate node. Source: https://docs.langchain.com/oss/python/langgraph/interrupts
- Interrupts in a node are matched to resume values by position: never reorder them or skip them conditionally. Source: https://docs.langchain.com/oss/python/langgraph/interrupts
- Do not use static breakpoints (`interrupt_before` / `interrupt_after`) for approvals; they are for debugging. Source: https://docs.langchain.com/oss/python/langgraph/interrupts

## Caps
- Step cap: set `recursion_limit` at the top level of the run config (not inside `configurable`) to the spec's step cap; it counts super-steps and raises `GraphRecursionError`. Use `RemainingSteps` in a router to wind down gracefully. Source: https://docs.langchain.com/oss/python/langgraph/graph-api
- Tool-call cap: a counter in graph state, incremented per tool call and checked by the router, exiting with the spec's single failure reply (own code, inference: raw LangGraph has no tool-call limit). Source: https://docs.langchain.com/oss/python/langgraph/graph-api
- Never use one limit for both: super-steps are not tool calls.

## Model provider
- `ChatLiteLLM(model=<spec model route>)` from `langchain-litellm`, pinned; the docs recommend it for routers and proxies (maintainer unverified). Source: https://docs.langchain.com/oss/python/langchain/models
- Or `init_chat_model("provider:model")` when the spec pins a single provider. Source: https://docs.langchain.com/oss/python/langchain/models

## Telemetry
- Install `langsmith[otel]` (docs ask for langsmith>=0.3.18, recommend >=0.4.25), set `LANGSMITH_OTEL_ENABLED=true` and `LANGSMITH_OTEL_ONLY=true`, and point `OTEL_EXPORTER_OTLP_*` at the design's backend. `OTEL_EXPORTER_OTLP_ENDPOINT` is a base URL (no `/v1/traces`). Source: https://docs.langchain.com/langsmith/trace-with-opentelemetry.md
- MANDATORY SPIKE before the build relies on it: emit one turn and confirm `gen_ai.usage.input_tokens` / `output_tokens` attributes arrive at the backend. The docs show how LangSmith reads those attributes on ingest but do not state what the SDK emits (unverified). If they do not arrive, add own spans carrying those attributes. Source: https://docs.langchain.com/langsmith/trace-with-opentelemetry.md
- Never set `LANGSMITH_TRACING` unless the design's telemetry backend is LangSmith (the docs examples pair it with the LangSmith endpoint). Source: https://docs.langchain.com/langsmith/trace-with-opentelemetry.md

## Eval runner mapping
- Fresh graph and a fresh `InMemorySaver` per test. Source: https://docs.langchain.com/oss/python/langgraph/test.md
- Model double: `GenericFakeChatModel` scripted with the tool calls and replies. Source: https://docs.langchain.com/oss/python/langchain/test/unit-testing.md
- Trajectory: taken from the graph's event stream (the pipeline runner's own capture, inference). The agentevals modes are strict, unordered, subset and superset. Source: https://docs.langchain.com/oss/python/langchain/test/evals.md
- EXACT = agentevals `strict`; ANY_ORDER = agentevals `unordered`; IN_ORDER has no agentevals mode, so the pipeline runner implements it as a subsequence check. Source: https://docs.langchain.com/oss/python/langchain/test/evals.md
- `harness_condition.force_step_cap` = a fake model that never gives a final answer (runs until `recursion_limit`); `tool_always_errors` = an erroring tool node (both inference, built on the primitives above). Source: https://docs.langchain.com/oss/python/langgraph/graph-api
- pass^k is computed by the pipeline runner; it is not native to the stack (digest).

## A2A and MCP
- Two A2A paths; record which one in interop.md.
  - (a) Licensed LangSmith Agent Server `/a2a/{assistant_id}`: A2A v1.0 JSON-RPC, push notifications not supported, the graph state must include a `messages` key. Source: https://docs.langchain.com/langsmith/server-a2a.md ; a standalone server needs `LANGGRAPH_CLOUD_LICENSE_KEY` and reaches beacon.langchain.com for license verification and usage reporting (unless air-gapped). Source: https://docs.langchain.com/langsmith/deploy-standalone-server.md
  - (b) Free: your own server built with `a2a-sdk` that wraps the compiled graph and persists interrupted state through the checkpointer (the digest's path; own code, inference). Source: https://docs.langchain.com/langsmith/server-a2a.md
- MCP client: `langchain[mcp]>=1.4.0`, `MCPAdapter` (beta, the API may change). Source: https://docs.langchain.com/oss/python/langchain/mcp
- Serving MCP (`/mcp`) is documented on Agent Server; no OSS-library endpoint is documented. Source: https://docs.langchain.com/langsmith/server-mcp.md

## Pinned version and traps
- Pins: `langgraph==1.2.14`, `langgraph-checkpoint-postgres` (exact version), `langchain-litellm` (exact version). Source: https://pypi.org/project/langgraph/
- Obligation (ops): interrupt() re-runs the node on resume, so side effects before it are idempotent. Source: https://docs.langchain.com/oss/python/langgraph/interrupts
- Obligation (ops): the OSS library has no per-thread locking and double-texting is not available there; the adapter queue serializes turns. Source: https://docs.langchain.com/langsmith/double-texting.md
- Obligation (data): do not set `LANGSMITH_TRACING` unless LangSmith is the chosen backend; use `LANGSMITH_OTEL_ONLY` for OTel-only export. Source: https://docs.langchain.com/langsmith/trace-with-opentelemetry.md
- Obligation (churn): do not adopt langgraph-supervisor (no longer actively maintained) or build new code on `create_react_agent`; LangGraph 0.4 maintenance ends December 2026. Sources: https://docs.langchain.com/oss/python/migrate/langgraph-supervisor.md , https://docs.langchain.com/oss/python/migrate/langchain-v1.md , https://docs.langchain.com/oss/python/release-policy
