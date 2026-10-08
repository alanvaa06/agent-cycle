---
id: langgraph
name: LangGraph
level: runtime
nests_on: none
package: langgraph
version_verified: 1.2.14
license: MIT
ts_sdk: full
verified_on: 2026-10-07
status: active
---

# LangGraph

## 1. What it is
Low-level orchestration framework and runtime for long-running, stateful agents (state graph, checkpointed threads, interrupts). It is the runtime that LangChain `create_agent` and Deep Agents run on. Source: https://docs.langchain.com/oss/python/concepts/products . The library is MIT licensed: https://github.com/langchain-ai/langgraph

## 2. Filter attributes
| Attribute | Value | Source |
|---|---|---|
| model_portability | any | https://docs.langchain.com/oss/python/langchain/models |
| a2a | licensed-server | https://docs.langchain.com/langsmith/server-a2a.md |
| mcp_client | beta | https://docs.langchain.com/oss/python/langchain/mcp |
| deploy_constraints | A2A, MCP serving and double-texting need the licensed LangSmith Agent Server; the MIT library runs free in your own container | https://docs.langchain.com/langsmith/double-texting.md |
| default_egress | none (LangSmith tracing only when enabled) | https://docs.langchain.com/langsmith/trace-with-opentelemetry.md |
| stability | semver-stable | https://docs.langchain.com/oss/python/release-policy |

Notes on the filter values (each with its own source):
- a2a: the A2A endpoint `/a2a/{assistant_id}` is documented on Agent Server; no OSS-library endpoint is documented. Source: https://docs.langchain.com/langsmith/server-a2a.md . A standalone Agent Server needs a LangSmith license key: https://docs.langchain.com/langsmith/deploy-standalone-server.md
- MCP serving (`/mcp`) is likewise documented on Agent Server; no OSS-library endpoint is documented: https://docs.langchain.com/langsmith/server-mcp.md
- mcp_client: `langchain.mcp` MCPAdapter needs `langchain[mcp]>=1.4.0` and is marked beta. Source: https://docs.langchain.com/oss/python/langchain/mcp
- deploy_constraints, "free in your own container": that the MIT library can be hosted in your own FastAPI container with your own checkpointer is the reading in docs/superpowers/research/2026-10-07-stack-catalog/langchain-family.md (inference); the pages above show only the licensed paths.

## 3. Seam mapping
| Seam | Support | How | Source |
|---|---|---|---|
| sessions | native | Checkpointer interface with Postgres for production and SQLite for local use only; stores, DynamoDB/Firestore caveats and durability settings are in the binding | https://docs.langchain.com/oss/python/langgraph/checkpointers.md |
| hitl_gate | native | `interrupt()` + `Command(resume=...)` on the same thread_id; requires a checkpointer; the whole node restarts on resume; static breakpoints (interrupt_before/after) are not recommended for HITL | https://docs.langchain.com/oss/python/langgraph/interrupts |
| step_cap | native | `recursion_limit` counts super-steps (default 1000 since 1.0.6), raises GraphRecursionError; RemainingSteps lets a router wind down gracefully | https://docs.langchain.com/oss/python/langgraph/graph-api |
| tool_call_cap | custom | none in raw LangGraph; a counter in state checked by a router (inference; recursion_limit counts super-steps, not tool calls) | https://docs.langchain.com/oss/python/langgraph/graph-api |
| model_provider | native | `init_chat_model("provider:model")`; LiteLLM via `ChatLiteLLM` from langchain-litellm (maintainer unverified) | https://docs.langchain.com/oss/python/langchain/models |
| telemetry | adapter | docs default to LangSmith; OTel export via `langsmith[otel]` + `LANGSMITH_OTEL_ENABLED` / `LANGSMITH_OTEL_ONLY=true`; the page documents how gen_ai.usage.* attributes are read on ingest, but whether the SDK emits GenAI semconv is unverified | https://docs.langchain.com/langsmith/trace-with-opentelemetry.md |
| eval_runner | adapter | InMemorySaver per test; GenericFakeChatModel scripts tool calls; agentevals trajectory match strict/unordered/subset/superset (no IN_ORDER mode) | https://docs.langchain.com/oss/python/langchain/test/evals.md |
| deploy | custom | The build writes its own container (worker or FastAPI) around the compiled graph with your own checkpointer (inference: no cited page documents library-only hosting); `langgraph dev` is an in-memory server for development and testing only; the standalone Agent Server needs a license key | https://docs.langchain.com/langsmith/deploy-standalone-server.md |

Further sources for the rows above:
- version 1.2.14 (released 2026-10-06) and MIT license: https://pypi.org/project/langgraph/
- sessions (DynamoDB: langgraph-checkpoint-aws and community langgraph-dynamodb-checkpoint; Firestore community package): https://docs.langchain.com/oss/python/integrations/checkpointers/index.md
- sessions (thread_id under 255 chars on Postgres): https://docs.langchain.com/oss/python/langgraph/persistence
- eval_runner (GenericFakeChatModel, InMemorySaver): https://docs.langchain.com/oss/python/langchain/test/unit-testing.md and https://docs.langchain.com/oss/python/langgraph/test.md
- deploy (`langgraph dev` is in-memory, dev and test only): https://docs.langchain.com/oss/python/langgraph/local-server.md
- MIT license of the library: https://github.com/langchain-ai/langgraph

## 4. Known traps
- [ops] interrupt() re-runs the whole node on resume: side effects before the interrupt must be idempotent. Source: https://docs.langchain.com/oss/python/langgraph/interrupts
- [ops] No per-thread locking in the OSS library; double-texting strategies are a LangSmith Deployment feature, not in the open source framework. Source: https://docs.langchain.com/langsmith/double-texting.md
- [data] LangSmith tracing sends traces to LangSmith by default (the docs call the default hybrid tracing and pair LANGSMITH_TRACING with the api.smith.langchain.com endpoint); set LANGSMITH_TRACING=true only together with LANGSMITH_OTEL_ONLY=true when the backend is not LangSmith, and verify no request reaches api.smith.langchain.com. Source: https://docs.langchain.com/langsmith/trace-with-opentelemetry.md
- [churn] langgraph-supervisor is no longer actively maintained (docs/superpowers/research/2026-10-07-stack-catalog/langchain-family.md says archived); the LangChain v1 guide now recommends create_agent over langgraph.prebuilt create_react_agent. Source: https://docs.langchain.com/oss/python/migrate/langgraph-supervisor.md and https://docs.langchain.com/oss/python/migrate/langchain-v1.md
- [churn] LangGraph 0.4 is in maintenance (security patches and critical fixes only) until December 2026. Source: https://docs.langchain.com/oss/python/release-policy

## 5. Pick when / avoid when
Pick when you need durable or resumable state machines, mixed deterministic and agentic steps, or fine-grained orchestration control. Source: https://docs.langchain.com/oss/python/concepts/products
Avoid when the agent is a linear tool loop (create_agent or no-framework is enough; inference backed by the same products page https://docs.langchain.com/oss/python/concepts/products ).
Avoid when A2A serving is required and no paid license is acceptable: A2A is documented on Agent Server (no OSS-library endpoint is documented) and a standalone server needs a license key, so the index filter eliminates LangGraph in that case (https://docs.langchain.com/langsmith/server-a2a.md , https://docs.langchain.com/langsmith/deploy-standalone-server.md ). An own a2a-sdk server is a build option only when a license is acceptable or A2A is not a hard filter (inference).

## 6. Build binding
`skills/build/references/bindings/langgraph.md`
