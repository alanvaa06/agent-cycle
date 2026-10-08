---
id: langchain-create-agent
name: LangChain create_agent
level: framework
nests_on: langgraph
package: langchain
version_verified: 1.4.3
license: MIT
ts_sdk: full
verified_on: 2026-10-07
status: active
---

# LangChain create_agent

## 1. What it is
The LangChain v1 agent harness: `create_agent` runs a model-calls-tools loop and is extended with middleware (human-in-the-loop, call limits, summarization and custom hooks). Its agents are built on top of LangGraph, which supplies persistence, interrupts and durable execution. Source: https://docs.langchain.com/oss/python/langchain/overview . Level in the product stack: https://docs.langchain.com/oss/python/concepts/products . The package is MIT licensed: https://pypi.org/project/langchain/

## 2. Filter attributes
| Attribute | Value | Source |
|---|---|---|
| model_portability | any | https://docs.langchain.com/oss/python/langchain/models |
| a2a | licensed-server | https://docs.langchain.com/langsmith/server-a2a.md |
| mcp_client | beta | https://docs.langchain.com/oss/python/langchain/mcp |
| deploy_constraints | A2A, MCP serving and double-texting need the licensed LangSmith Agent Server; the library runs free in your own container | https://docs.langchain.com/langsmith/double-texting.md |
| default_egress | none (LangSmith tracing only when enabled) | https://docs.langchain.com/langsmith/trace-with-opentelemetry.md |
| stability | semver-stable | https://docs.langchain.com/oss/python/release-policy |

Notes on the filter values (each with its own source):
- a2a: the A2A endpoint `/a2a/{assistant_id}` is documented on Agent Server; no OSS-library endpoint is documented. Source: https://docs.langchain.com/langsmith/server-a2a.md . A standalone Agent Server needs a LangSmith license key: https://docs.langchain.com/langsmith/deploy-standalone-server.md
- MCP serving (`/mcp`) is documented on Agent Server; no OSS-library endpoint is documented (research file docs/superpowers/research/2026-10-07-stack-catalog/langchain-family.md; the page only implies it): https://docs.langchain.com/langsmith/server-mcp.md
- mcp_client: the `langchain.mcp` namespace (`MCPAdapter`) needs `langchain[mcp]>=1.4.0` and is in beta; importing it raises a beta warning. Source: https://docs.langchain.com/oss/python/langchain/mcp
- deploy_constraints, "free in your own container": the reading in docs/superpowers/research/2026-10-07-stack-catalog/langchain-family.md is that the MIT library runs inside your own FastAPI container with your own checkpointer (inference); the pages above show only the licensed paths.
- stability: breaking changes only in major versions, 1.0 is LTS and active until 2.0. Source: https://docs.langchain.com/oss/python/release-policy

## 3. Seam mapping
| Seam | Support | How | Source |
|---|---|---|---|
| sessions | native | Runs on LangGraph checkpointers: pass `checkpointer=` to `create_agent` and a `thread_id` in the config; Postgres for production, stores and durability settings are in the binding (see the langgraph card) | https://docs.langchain.com/oss/python/langchain/short-term-memory |
| hitl_gate | native | `HumanInTheLoopMiddleware(interrupt_on={tool: True/False/config})` with `allowed_decisions` approve/edit/reject; needs a checkpointer; resume with `Command(resume={"decisions": [...]})` | https://docs.langchain.com/oss/python/langchain/human-in-the-loop |
| step_cap | custom | own TurnCaps middleware on the documented hook API (the built-in ModelCallLimit/ToolCallLimit counters restart on a HITL resume, see trap) | https://docs.langchain.com/oss/python/langchain/middleware/built-in |
| tool_call_cap | custom | own TurnCaps middleware on the documented hook API (the built-in ModelCallLimit/ToolCallLimit counters restart on a HITL resume, see trap) | https://docs.langchain.com/oss/python/langchain/middleware/built-in |
| model_provider | native | `init_chat_model("provider:model")` or the same string in `create_agent`; LiteLLM via `ChatLiteLLM` from langchain-litellm (maintainer unverified) | https://docs.langchain.com/oss/python/langchain/models |
| telemetry | adapter | Same LangSmith OTel path as the langgraph card: `langsmith[otel]` + `LANGSMITH_OTEL_ENABLED` / `LANGSMITH_OTEL_ONLY=true`; whether the SDK emits GenAI semconv is unverified | https://docs.langchain.com/langsmith/trace-with-opentelemetry.md |
| eval_runner | adapter | As the langgraph card: InMemorySaver per test, GenericFakeChatModel scripts tool calls, agentevals trajectory match strict/unordered/subset/superset (no IN_ORDER mode) | https://docs.langchain.com/oss/python/langchain/test/evals.md |
| deploy | custom | The build writes its own container (worker or FastAPI) around the agent with your own checkpointer (inference: no cited page documents library-only hosting); the standalone Agent Server needs a license key | https://docs.langchain.com/langsmith/deploy-standalone-server.md |

Further sources for the rows above:
- version 1.4.3 (released 2026-09-28), MIT license, requires langgraph>=1.2.11 and <1.3.0: https://pypi.org/project/langchain/ and https://pypi.org/pypi/langchain/1.4.3/json
- hitl_gate (payload shapes, `when` predicate needs langchain>=1.3.3): https://docs.langchain.com/oss/python/langchain/human-in-the-loop
- tool_call_cap (run counter is untracked state and counted in the after_model hook; read in source on master, not on the 1.4.3 tag): https://github.com/langchain-ai/langchain/blob/master/libs/langchain_v1/langchain/agents/middleware/tool_call_limit.py
- step_cap (check before each model call): https://github.com/langchain-ai/langchain/blob/master/libs/langchain_v1/langchain/agents/middleware/model_call_limit.py
- eval_runner (GenericFakeChatModel, InMemorySaver): https://docs.langchain.com/oss/python/langchain/test/unit-testing.md
- sessions (DynamoDB, Firestore, thread_id limit): https://docs.langchain.com/oss/python/integrations/checkpointers/index.md and https://docs.langchain.com/oss/python/langgraph/persistence

## 4. Known traps
- [ops] HITL resume re-runs the interrupted node (LangGraph semantics): anything before the interrupt in that node must be idempotent. Source: https://docs.langchain.com/oss/python/langgraph/interrupts
- [ops] The built-in ModelCallLimit and ToolCallLimit run counters are per invocation (docs: run_limit is per single invocation) and are private untracked state in the library source on master, so inference: they restart when a HITL pause is resumed and one spec turn can get a second budget; the binding therefore uses its own counter middleware. Source: https://github.com/langchain-ai/langchain/blob/master/libs/langchain_v1/langchain/agents/middleware/tool_call_limit.py and https://docs.langchain.com/oss/python/langchain/middleware/built-in
- [ops] `ToolCallLimitMiddleware` with `exit_behavior="end"` works only when limiting a single tool and raises NotImplementedError if other tools have pending calls; a global cap needs error or continue. Source: https://docs.langchain.com/oss/python/langchain/middleware/built-in
- [ops] No per-thread locking in the OSS library; double-texting strategies are a LangSmith Deployment feature. Source: https://docs.langchain.com/langsmith/double-texting.md
- [data] LangSmith tracing sends traces to LangSmith: when tracing is enabled, the default mode is hybrid (LangSmith plus OTel; the docs pair LANGSMITH_TRACING with the api.smith.langchain.com endpoint); set LANGSMITH_TRACING=true only together with LANGSMITH_OTEL_ONLY=true when the backend is not LangSmith, and verify no request reaches api.smith.langchain.com. Source: https://docs.langchain.com/langsmith/trace-with-opentelemetry.md
- [churn] `langchain.mcp` (beta) is the documented MCP path for langchain>=1.4.0; that it supersedes langchain-mcp-adapters is inference (research file docs/superpowers/research/2026-10-07-stack-catalog/langchain-family.md; the page points older versions to a migration guide). Source: https://docs.langchain.com/oss/python/langchain/mcp
- [churn] Legacy chains, retrievers and the indexing API moved to langchain-classic in v1. Source: https://docs.langchain.com/oss/python/migrate/langchain-v1.md

## 5. Pick when / avoid when
Pick when the agent is the typical client tool agent that needs HITL with v1 stability: create_agent is described as a minimal, highly configurable harness for a customizable agent (https://docs.langchain.com/oss/python/langchain/overview ) and the docs point to LangChain for straightforward applications without complex orchestration (https://docs.langchain.com/oss/python/concepts/products ).
Avoid when the orchestration needs explicit graph control or mixed deterministic and agentic steps: the overview points those to LangGraph (https://docs.langchain.com/oss/python/langchain/overview ).
Avoid when A2A serving is required and no paid license is acceptable: A2A is documented on Agent Server (no OSS-library endpoint is documented) and a standalone server needs a license key, so the index filter eliminates this card in that case (https://docs.langchain.com/langsmith/server-a2a.md , https://docs.langchain.com/langsmith/deploy-standalone-server.md ). An own a2a-sdk server is a build option only when a license is acceptable or A2A is not a hard filter (inference).

## 6. Build binding
`skills/build/references/bindings/langchain-create-agent.md`
