---
id: deep-agents
name: Deep Agents
level: harness
nests_on: langchain-create-agent
package: deepagents
version_verified: 0.7.23
license: MIT
ts_sdk: partial
verified_on: 2026-10-07
status: active
---

# Deep Agents

## 1. What it is
An open source agent harness from LangChain for long-running, multi-step work: `create_deep_agent` returns a compiled LangGraph agent with a virtual filesystem, a `task` tool that spawns subagents, context summarization and optional memory, skills and planning. It is built on LangChain `create_agent` (so its middleware model applies) and runs on the LangGraph runtime. Sources: https://docs.langchain.com/oss/python/deepagents/overview and https://docs.langchain.com/oss/python/concepts/products . MIT licensed, version 0.7.23 released 2026-10-07 (PyPI classifier "4 - Beta"): https://pypi.org/project/deepagents/ . The project 'follows a "trust the LLM" model': boundaries are enforced at tool or sandbox level, not by the model: https://github.com/langchain-ai/deepagents

## 2. Filter attributes
| Attribute | Value | Source |
|---|---|---|
| model_portability | any | https://docs.langchain.com/oss/python/deepagents/customization |
| a2a | licensed-server | https://docs.langchain.com/langsmith/server-a2a.md |
| mcp_client | beta | https://docs.langchain.com/oss/python/langchain/mcp |
| deploy_constraints | FilesystemBackend and LocalShellBackend must not be used in deployed agents (sandbox + HITL instead); A2A via licensed Agent Server; Managed Deep Agents is US-only beta | https://docs.langchain.com/oss/python/deepagents/going-to-production |
| default_egress | none (LangSmith tracing only when enabled) | https://docs.langchain.com/langsmith/trace-with-opentelemetry.md |
| stability | pre-1.0 | https://pypi.org/project/deepagents/ |

Notes on the filter values (each with its own source):
- model_portability: `model=` takes a `provider:model` string or an initialized chat model instance. Source: https://docs.langchain.com/oss/python/deepagents/customization
- a2a: the A2A endpoint `/a2a/{assistant_id}` is documented on Agent Server (no OSS-library A2A page found), and a standalone Agent Server needs a LangSmith license key. Source: https://docs.langchain.com/langsmith/server-a2a.md and https://docs.langchain.com/langsmith/deploy-standalone-server.md . That a Deep Agent graph has the required `messages` state key is inference (it is built on `create_agent`).
- mcp_client: Deep Agents takes plain LangChain tools, so the `langchain.mcp` MCPAdapter (beta) is the path (inference); the README lists "MCP tool support" without naming the mechanism (unverified). Sources: https://docs.langchain.com/oss/python/langchain/mcp and https://github.com/langchain-ai/deepagents
- deploy_constraints: FilesystemBackend and LocalShellBackend access the host and the production page says not to use them in deployed agents: https://docs.langchain.com/oss/python/deepagents/going-to-production and https://docs.langchain.com/oss/python/deepagents/backends . "Managed Deep Agents is US-only beta" comes from the research file docs/superpowers/research/2026-10-07-stack-catalog/langchain-family.md only; the Managed Deep Agents overview does not state region or beta (unverified on the page): https://docs.langchain.com/oss/python/deepagents/deploy
- default_egress: no default network call is documented for the library; the egress risks are LangSmith tracing when enabled and, by choice, hosted sandboxes or the LangSmith Context Hub backend (needs LANGSMITH_API_KEY). Source: https://docs.langchain.com/oss/python/deepagents/backends
- stability: 0.x; the research file quotes "APIs may change between minor versions" (docs/superpowers/research/2026-10-07-stack-catalog/langchain-family.md). Source for the beta classifier: https://pypi.org/project/deepagents/

## 3. Seam mapping
| Seam | Support | How | Source |
|---|---|---|---|
| sessions | native | LangGraph checkpointers and stores: `checkpointer=` and `store=` on `create_deep_agent`, `thread_id` in the config; StateBackend files persist per thread through the checkpointer; Postgres for production (see the langgraph card) | https://docs.langchain.com/oss/python/deepagents/going-to-production |
| hitl_gate | native | `interrupt_on={tool: True/False/{allowed_decisions}}`, optional `when` predicate; needs a checkpointer; resume with `Command(resume={"decisions": [...]})`; each subagent can set its own `interrupt_on` | https://docs.langchain.com/oss/python/deepagents/human-in-the-loop |
| step_cap | custom | own TurnCaps middleware passed via `middleware=` (accepted by `create_deep_agent`); the built-in ModelCallLimit counters restart on a HITL resume (inference, same reason as the langchain-create-agent card); graph.py has neither | https://docs.langchain.com/oss/python/deepagents/customization |
| tool_call_cap | custom | own TurnCaps middleware passed via `middleware=` (same reason as step_cap, ToolCallLimit); subagent calls are not counted by the main agent middleware (inference) | https://docs.langchain.com/oss/python/deepagents/customization |
| model_provider | native | any provider via `model="provider:model"` or a chat model instance (LiteLLM via `ChatLiteLLM`, maintainer unverified); pass `model=` explicitly | https://docs.langchain.com/oss/python/deepagents/customization |
| telemetry | adapter | LangSmith by default; OTel via `langsmith[otel]` + `LANGSMITH_OTEL_ENABLED` / `LANGSMITH_OTEL_ONLY=true`; Deep Agents docs do not cover OTel (inference: same SDK path as LangChain) | https://docs.langchain.com/langsmith/trace-with-opentelemetry.md |
| eval_runner | adapter | pytest + LangSmith pytest integration per LangChain's evaluating-deep-agents post; for the pipeline: InMemorySaver per test and a fake chat model, as the langgraph card | https://www.langchain.com/blog/evaluating-deep-agents-our-learnings |
| deploy | custom | The build writes its own container (worker or FastAPI) around the compiled agent with your own checkpointer: the Managed Deep Agents page says `create_deep_agent` is for running the agent yourself with your own backend, store, checkpointer and server and gives no steps; the production page gives no `langgraph build` or Docker steps for self-hosting (inference: no page documents library-only hosting) | https://docs.langchain.com/oss/python/deepagents/going-to-production |

Further sources for the rows above:
- version 0.7.23 (released 2026-10-07), MIT, Python >=3.11, requires langchain>=1.4.3,<2 and langchain-core>=1.6.7,<2: https://pypi.org/pypi/deepagents/json . Release tag: https://api.github.com/repos/langchain-ai/deepagents/releases
- `create_deep_agent` parameters, middleware stack and `middleware=` placement (user middleware goes after the core stack, HITL is appended after it; recursion_limit set to 9999; neither ModelCallLimit nor ToolCallLimit appears): https://docs.langchain.com/oss/python/deepagents/customization and https://github.com/langchain-ai/deepagents/blob/main/libs/deepagents/deepagents/graph.py (read on main, not on the 0.7.23 tag)
- sessions (DynamoDB, Firestore, thread_id limit): https://docs.langchain.com/oss/python/integrations/checkpointers/index.md and https://docs.langchain.com/oss/python/langgraph/persistence
- ts_sdk partial: a JavaScript/TypeScript version, deepagents.js, exists: https://github.com/langchain-ai/deepagents

## 4. Known traps
- [security] Filesystem, SubAgent and Permission middleware cannot be removed (excluding them raises ValueError): only their tools are hidden with `HarnessProfile(excluded_tools=...)`, and `excluded_tools` is a post-injection filter that can also drop user-supplied tools. Source: https://docs.langchain.com/oss/python/deepagents/profiles
- [security] FilesystemPermission is permissive by default (a call matching no rule is allowed), rules are first-match-wins, and it does not cover `execute`, custom tools or MCP tools, nor sandbox backends: add a catch-all deny last (`operations=["read","write"]`, `paths=["/**"]`, `mode="deny"`). Source: https://docs.langchain.com/oss/python/deepagents/permissions
- [security] The general-purpose subagent is added by default (with filesystem tools); disable it with `GeneralPurposeSubagentProfile(enabled=False)` and pass no synchronous subagents. Source: https://docs.langchain.com/oss/python/deepagents/subagents
- [security] FilesystemBackend and LocalShellBackend read and write the host (LocalShellBackend adds an unrestricted `execute`); the production page says not to use them in deployed agents. Use StateBackend or a sandbox backend. Source: https://docs.langchain.com/oss/python/deepagents/backends
- [ops] Built-in tool schemas are sent on every turn (page) and the system prompt is part of each model request (inference), so token cost is high; hide unused tools with `excluded_tools`. Source: https://docs.langchain.com/oss/python/deepagents/context-engineering
- [ops] The built-in call-limit counters are not used (graph.py has neither), and the langchain-create-agent card explains why they restart on a HITL resume (inference); HITL is appended after user middleware, so an after_model cap hook runs after the approval pause (inference from the hook order). Source: https://github.com/langchain-ai/deepagents/blob/main/libs/deepagents/deepagents/graph.py
- [churn] 0.x: defaults changed in 0.7 (task planning with `write_todos` is opt-in, a `delete` tool was added) and omitting `model=` is deprecated. Source: https://docs.langchain.com/oss/python/deepagents/harness and https://github.com/langchain-ai/deepagents/blob/main/libs/deepagents/deepagents/graph.py

## 5. Pick when / avoid when
Pick when the agent does long-running research or coding work that needs planning, subagents and a filesystem: the docs point Deep Agents at long-running planning, subagent and filesystem work (https://docs.langchain.com/oss/python/concepts/products ).
Avoid when the agent is a small, tightly scoped least-privilege tool agent: create_agent carries less implicit surface (inference stated in docs/superpowers/research/2026-10-07-stack-catalog/langchain-family.md; the built-in filesystem, `task` and permission surface is listed at https://docs.langchain.com/oss/python/deepagents/harness ).
Avoid when A2A serving is required and no paid license is acceptable: A2A is documented on Agent Server and a standalone server needs a license key, so the index filter eliminates this card in that case (https://docs.langchain.com/langsmith/server-a2a.md , https://docs.langchain.com/langsmith/deploy-standalone-server.md ). An own a2a-sdk server is a build option only when a license is acceptable or A2A is not a hard filter (inference).

## 6. Build binding
`skills/build/references/bindings/deep-agents.md`
