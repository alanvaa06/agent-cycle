# LangChain family research digest (2026-10-07, verified against docs.langchain.com by 3 subagents)

## Three nested levels (docs: /oss/python/concepts/products)
- Deep Agents (harness, `deepagents` 0.7.23, 4-Beta, pre-1.0, "APIs may change between minor versions")
  -> built on LangChain `create_agent` (framework/harness, v1 semver, LTS)
  -> runs on LangGraph (runtime, `langgraph` 1.2.14, MIT, v1 stability release).
- Docs guidance: Deep Agents for long-running planning/subagent/filesystem work; create_agent for
  straightforward/custom harness; LangGraph for fine-grained control, durable state, mixed deterministic+agentic.
- LangChain 0.3 / LangGraph 0.4 maintenance ends Dec 2026.

## Mapping to agent-cycle seams
- Sessions: checkpointers Postgres (prod), SQLite (local only), Mongo, Redis, Oracle, CosmosDB; DynamoDBSaver via
  AWS `langgraph-checkpoint-aws`; NO Firestore checkpointer (GCP -> Cloud SQL Postgres). thread_id = primary key (<255 chars PG).
  Durability modes exit/async/sync -> pipeline should require "sync".
- Concurrency: OSS has no per-thread locking; double-texting strategies are LangSmith Deployment only.
  agent-cycle adapter already serializes per sender via queue -> covered.
- HITL: interrupt()/Command(resume) needs checkpointer; node restarts from top on resume -> side effects before
  interrupt must be idempotent; static breakpoints not for HITL. create_agent: HumanInTheLoopMiddleware(interrupt_on).
  Deep Agents: interrupt_on + optional `when` predicate.
- Caps: recursion_limit = super-steps (default 1000 since 1.0.6), GraphRecursionError, RemainingSteps.
  Tool-call cap: none in raw LangGraph; create_agent has ToolCallLimitMiddleware + ModelCallLimitMiddleware
  (run/thread limits, exit_behavior). Raw StateGraph -> counter in state.
- Model: init_chat_model("provider:model"); LiteLLM via `langchain-litellm` ChatLiteLLM/Router (maintainer unverified).
- Telemetry: docs default LangSmith; OTel export via langsmith[otel] + LANGSMITH_OTEL_ENABLED / LANGSMITH_OTEL_ONLY.
  GenAI semconv emission UNVERIFIED -> spike needed before promising.
- Evals: agentevals trajectory match strict/unordered/subset/superset (no IN_ORDER-with-extras); GenericFakeChatModel;
  InMemorySaver per test; LangSmith pytest plugin. pass^k not native -> keep agent-cycle runner.
- MCP client: `langchain.mcp` MCPAdapter (langchain[mcp]>=1.4.0, BETA), replaces langchain-mcp-adapters.
- A2A / MCP-serving / double texting / Studio: LangSmith Agent Server ONLY (/a2a/{assistant_id}, A2A v1.0 JSON-RPC,
  no push/SubscribeToTask). Standalone server needs LANGGRAPH_CLOUD_LICENSE_KEY + beacon; self-host/BYOC = Enterprise.
  Free path: MIT library inside own FastAPI container + own checkpointer.
- Multi-agent: docs say single agent + tools often enough; supervisor via tools; langgraph-supervisor ARCHIVED;
  langgraph-swarm legacy (not in current docs); subgraphs node-or-call, checkpointer None/True/False.

## Deep Agents specifics
- Default middleware: Filesystem, SubAgent (general-purpose ON), Summarization, PatchToolCalls, ... HITL if interrupt_on.
- Filesystem/SubAgent/Permission middleware NOT removable (ValueError) — only hide tools via HarnessProfile(excluded_tools).
- FilesystemPermission default PERMISSIVE (unmatched = allow; need catch-all deny); does not cover execute/custom/MCP tools.
- Project "trusts the LLM" -> enforce at tool/sandbox. FilesystemBackend/LocalShellBackend forbidden in prod per docs.
- Heavy prompt (tool schemas every turn). Managed Deep Agents (`mda`) public beta 2026-08-07, US-only LangSmith Cloud.
- No native tier concept -> map tiers to interrupt_on + excluded_tools + own wrappers.

## LangSmith
- Developer $0 (5k traces, 1 seat, no deploy); Plus $39/seat (10k traces, 1 small serverless deploy); Enterprise custom.
- OTel ingest + export. Deployment framework-agnostic (also ADK, Claude Agent SDK, CrewAI...). Self-host/BYOC Enterprise only.
