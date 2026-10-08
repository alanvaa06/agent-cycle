# Stack card: CrewAI (researched 2026-10-07)

Conventions: every claim cites a source key (URL list at the bottom). **unverified** = not confirmed on a page I read. **inference** = my reasoning, not a doc statement. Docs read were the versioned `docs.crewai.com/v1.15.24/...` pages.

## 1. Identity
- Package `crewai`. Latest is **1.15.24, released 2026-10-07**. The previous releases were 1.15.23 (Sep 28), 1.15.22 (Sep 16) and 1.15.21 (Sep 9) [PYPI][GHREL].
- License is MIT. Requires Python >=3.10,<3.14. The author is Joao Moura, and the maintainers are joaomdmoura and lorenzec [PYPI]. The repo is crewAIInc/crewAI [GHREL]. The only language is Python; I found no TS SDK (**unverified**).
- **It is independent of LangChain.** PyPI says it is "completely independent of LangChain or other agent frameworks" [PYPI], and `pyproject.toml` lists no langchain dependency [PYPROJ].
- Versioning: I found no published stability policy (**unverified**). Release cadence is very high: 24 stable patch releases between 1.15.0 (2026-06-25) and 1.15.24, about one every 4-5 days [PYPI-HIST]. Recent patches change behavior: CLI flags moved to kebab-case (1.15.15), conversational flows were "promoted to stable" (1.15.18), and replay is now rejected when stored tasks differ (1.15.22) [GHREL]. `A2AConfig` is "deprecated and will be removed in v2.0.0", so a 2.0 with removals is planned [A2A].

## 2. Core abstractions and execution loop
- **Agent** (role/goal/backstory, tools, llm), **Task**, **Crew** (agents + tasks + process), **Process** (sequential or hierarchical), **Flow** (an event-driven state machine built from `@start`/`@listen`/`@router`/`and_`/`or_`, with Pydantic state) [FLOWS][PROC].
- Agent loop: a ReAct-style iteration capped by `max_iter` (default 20). After the cap the agent "must give its best answer" [AGENTS]. `Agent.kickoff(messages=...)` runs a single agent without a crew, through a `LiteAgent` [AGENTS].
- The docs advise: "we recommend starting with a Flow". The Flow is the orchestrator, and Crews are focused units of work inside it [PRODARCH].
- **Conversational / multi-turn chat is now first-class.** Apply `@ConversationConfig` to a `Flow[ConversationState]`. Each user message is one `handle_turn(message, session_id=...)` (or `stream_turn`) call that restores the latest `@persist` snapshot, appends the message to `state.messages`, optionally routes by intent, and then runs a handler [CONVO]. Serving it over HTTP is left to you: the page documents no REST endpoints [CONVO]. Rule: "Never run two turns concurrently on one Flow instance" [CONVO]. Crews themselves remain batch- and task-oriented (inference from [PROC][TEST]).

## 3. State and sessions
- `@persist` (on a class or a method) defaults to `SQLiteFlowPersistence`, a local SQLite database [FLOWS][HFF]. Resume with `kickoff(inputs={"id": ...})`. Fork with `restore_from_state_id` [STATE].
- **There is no built-in Postgres, Supabase, DynamoDB or Firestore persistence** (only SQLite is named) [FLOWS]. The `FlowPersistence` ABC is small: `init_db`, `save_state(flow_uuid, method_name, state_data)` and `load_state(flow_uuid)`, plus optional `save/load/clear_pending_feedback` for HITL pauses [PERSIST-SRC]. A Postgres/Dynamo/Firestore adapter fits behind the pipeline's repository interface in roughly 100 lines (**inference**).
- Checkpointing is a separate system with `JsonProvider` and `SqliteProvider` (WAL). It saves crew, flow or agent state per event and supports resume or fork. It cannot be combined with `restore_from_state_id` [CKPT][STATE].
- **Memory** is one unified `Memory` class that replaced short-term, long-term, entity and external memory. Its default store is LanceDB at `./.crewai/memory`. A custom `StorageBackend` protocol is available, but no Postgres or pgvector backend is documented [MEM]. The default embedder is OpenAI `text-embedding-3-large` [MEM]. LanceDB locking covers a single process only, and multi-process access is not addressed [MEM]. `chromadb` and `lancedb` are both core dependencies, which makes the install heavy [PYPROJ].

## 4. HITL / approval gate
- **Tool hooks are the right seam.** A `PRE_TOOL_CALL` hook (or `@before_tool_call`) can block a call by returning `False` or raising `HookAborted`. The hook receives `tool_name`, a mutable `tool_input`, `agent`, `task` and `crew`, and can be global or crew-scoped. The docs include an approval-gate example for `send_email`, `make_purchase` and `delete_file` [HOOKS]. Its `request_human_input` is console-only [HOOKS], so a headless webhook bot needs its own pause mechanism (**inference**).
- Flow-level `@human_feedback(emit=[...], llm=..., provider=...)`: a custom `HumanFeedbackProvider` raises `HumanFeedbackPending`, state is auto-persisted, and the flow resumes later with `Flow.from_pending(id).resume(feedback)` or `resume_async` [HFF]. This gives durable async approval with Slack or webhook providers [HFF].
- Webhook HITL (`humanInputWebhook` + `/resume`) is labelled **Enterprise** [HITL].
- Mapping (**inference**): put the tier check in a global PRE_TOOL_CALL hook, so safe tools pass and reversible or destructive tools are blocked. Wrap destructive actions as a dedicated Flow step decorated with `@human_feedback` and an async provider, so the pause survives restarts.

## 5. Caps
- Native caps: `max_iter` (20), `max_rpm` (None), `max_execution_time` in seconds (None), `max_retry_limit` (2) [AGENTS]. A2A has `max_turns` (10) [A2A]. Tasks have `guardrail` [PRODARCH].
- **There is no native per-run tool-call cap.** `max_usage_count` appears only as a failure trigger, and the docs don't say how to set it (**unverified**) [TOOLS]. The docs do show a hook that blocks a tool after 10 calls per minute [HOOKS], so a run-level tool-call counter would be a custom PRE_TOOL_CALL hook (**inference**).
- `tool_failure_policy` can be ignore, warn (the default) or raise [TOOLS].

## 6. Model providers
- **Not LiteLLM-based by default any more.** Native providers are OpenAI, Anthropic, Gemini, Azure, Bedrock and Snowflake Cortex [LLMS]. LiteLLM is an optional `crewai[litellm]` extra used as a fallback for more than 100 providers. The docs note that `litellm` "was quarantined on PyPI" and recommend native integrations [LITELLM].
- Model strings use the form `provider/model-id`, for example `anthropic/...`, set through `MODEL` in the environment, YAML, or `LLM(...)`. `custom_openai=True` + `base_url` works for vLLM, Ollama and gateways [LLMS][LITELLM]. The fallback default is `gpt-4` [AGENTS]. This matches the pipeline's swappable-provider seam well (**inference**).

## 7. Tools
- Tools are built with `BaseTool` or `@tool`, can be async, have caching on by default, and can return typed Pydantic outputs [TOOLS]. Extra tools ship in `crewai[tools]` [TOOLS].
- MCP is supported as a **client only**: an agent-level `mcps=[...]` DSL or `MCPServerAdapter`, over stdio, SSE or streamable HTTP. Static and dynamic tool allow/block filters are a least-privilege lever. Only MCP tools are supported, not prompts or resources [MCP]. Exposing a crew as an MCP server is not documented (**unverified**) [MCP].
- Code execution: `allow_code_execution=False` by default and deprecated. `CodeInterpreterTool` has been "removed from crewai-tools". The docs recommend E2B or Modal. The old tool defaulted to Docker, and unsafe mode was "NOT RECOMMENDED FOR PRODUCTION" [CODE].
- Least privilege: tools are scoped per agent (`tools=[]`, default empty) [AGENTS]. CrewAI has no built-in safe/reversible/destructive tier concept (**unverified**, none found), so hooks are needed.

## 8. Multi-agent and A2A
- Processes are sequential, or hierarchical with a `manager_llm` or `manager_agent` that plans, delegates and validates [PROC]. `allow_delegation` defaults to False [AGENTS].
- **A2A is native, as both client and server**, via `crewai[a2a]` (`a2a-sdk~=0.3.10`) [PYPROJ]. `A2AClientConfig` takes an endpoint (agent card), auth (bearer, API key, OAuth2, basic), `max_turns` and streaming/polling/push. `A2AServerConfig` serves a per-agent card with JWS signing and `AUTH_TOKEN` auth. The protocol version is 0.3.0 [A2A]. Distributed state, gRPC and horizontal scaling are pointed to AMP [A2A].

## 9. Observability
- **Anonymous telemetry is ON by default.** Disable it with `CREWAI_DISABLE_TELEMETRY=true` (or `OTEL_SDK_DISABLED=true`). It sends no prompts or outputs unless `share_crew=True` [TEL][PYPI].
- CrewAI uses a **private TracerProvider** and never registers as the global one, so your own OTel setup is unaffected [TEL]. OTel SDK and OTLP-HTTP are core dependencies [PYPROJ].
- Built-in "tracing" is opt-in (`tracing=True` / `CREWAI_TRACING_ENABLED`) and uploads to CrewAI AMP; the docs warn traces "may contain prompts" [TRACE].
- To send spans to your own backend, use third-party instrumentors: OpenInference `CrewAIInstrumentor` [PHX] or OpenLIT with `OTEL_EXPORTER_OTLP_ENDPOINT` [OPENLIT]. **GenAI semantic conventions are not mentioned in any CrewAI doc page I read (unverified).**
- The event bus (`BaseEventListener`) emits LLM, tool, agent and flow events [EVT]. These are usable for custom spans or trajectory capture (**inference**).

## 10. Testing / evals
- `crewai test -n N -m model` prints 1-10 task scores. "For now, the only provider available is OpenAI" [TEST]. There is no trajectory eval, no LLM mocking, and no golden-case support [TEST].
- **CrewAI's own eval tooling doesn't fit the pipeline harness.** Trajectories would come from event-bus `ToolUsage*` events (**inference**). Model doubles could be a stub OpenAI-compatible server through `custom_openai` + `base_url`, or a custom LLM subclass (**inference, unverified**). `handle_turn()` makes multi-turn pytest straightforward [CONVO].

## 11. Deployment and pricing
- The OSS framework is a plain Python library, so you deploy it in your own FastAPI/worker container on a VPS, AWS or GCP (**inference**; the docs don't cover self-host Docker [PRODARCH]). The production page pushes `crewai deploy create` to AMP [PRODARCH].
- **AMP** offers managed deploys, a REST API, traces and webhook streaming [AMP]. The self-hosted "Factory" option requires Kubernetes 1.32+, Helm, external Postgres 16.8+, S3, at least 14Gi/4 CPU, and AMD64 nodes only. It has Terraform guides for AWS, GCP and Azure [FACTORY].
- Pricing: Basic is free with 50 workflow executions per month. Enterprise is custom-priced with VPC or own-infra deployment, SSO, RBAC and PII redaction [PRICING].

## 12. When to pick / when not
- **Pick it** when a role-based multi-agent decomposition (crews) helps, when you want native A2A client and server, native Anthropic/OpenAI/Gemini without LiteLLM, MCP-client tools, tool hooks for gating, and durable HITL pauses through `@human_feedback` [A2A][LLMS][HOOKS][HFF]. The docs themselves steer toward Flows for production structure [PRODARCH].
- **Don't pick it** if you need:
  - **Determinism and thin abstraction.** Role, goal and backstory prompting plus the hierarchical manager add LLM-driven indirection (**inference**).
  - **Low churn.** It ships a release every ~4-5 days, with behavior changes in patch releases and v2.0 removals announced [PYPI-HIST][GHREL][A2A].
  - **Postgres-native state.** That is a custom adapter [FLOWS][PERSIST-SRC].
  - **A lean dependency tree.** Core pulls in chromadb, lancedb, the OTel SDK and the MCP SDK [PYPROJ].
  - **Vendor-neutral tracing out of the box.** Native tracing targets AMP [TRACE].
  - **Many key HITL and production features** are AMP- or Enterprise-gated [HITL][A2A].

## 13. Verdict
**Usable but not lowest-friction for this pipeline (inference).**
- **Fits well:**
  - The provider seam: native SDKs plus an optional LiteLLM extra.
  - MCP tools: client only.
  - A2A: native, both roles.
  - The HITL gate: a PRE_TOOL_CALL hook for tiering plus `@human_feedback` with an async provider and `from_pending().resume()` for durable approvals.
  - Webhook conversational agents: `handle_turn(session_id)` sits naturally behind an ingress -> queue -> per-user serial worker, which also satisfies the docs' "never two concurrent turns" rule.
- **Needs custom work:**
  - Durable sessions need a `FlowPersistence` adapter for Postgres, Supabase, Dynamo or Firestore (small: 3 required methods plus 3 optional pending-feedback ones).
  - The **tool-call cap** has to be a custom hook counter. Only `max_iter` and `max_execution_time` are native.
  - **GenAI-semconv OTel** has to come from OpenInference or OpenLIT, not CrewAI itself, and anonymous telemetry must be switched off explicitly.
  - Evals have to be your own pytest harness, built on event-bus trajectory capture.
- **The real costs:** release churn (pin exact versions and re-run evals on every bump), a heavy dependency footprint, and AMP gravity in the docs.

## Sources
- [PYPI] https://pypi.org/project/crewai/
- [PYPI-HIST] https://pypi.org/project/crewai/#history
- [GHREL] https://github.com/crewAIInc/crewAI/releases
- [PYPROJ] https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/pyproject.toml
- [PERSIST-SRC] https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/flow/persistence/base.py
- [FLOWS] https://docs.crewai.com/v1.15.24/en/concepts/flows.md
- [CONVO] https://docs.crewai.com/v1.15.24/en/guides/flows/conversational-flows.md
- [STATE] https://docs.crewai.com/v1.15.24/en/guides/flows/mastering-flow-state.md
- [CKPT] https://docs.crewai.com/v1.15.24/en/concepts/checkpointing.md
- [MEM] https://docs.crewai.com/v1.15.24/en/concepts/memory.md
- [HFF] https://docs.crewai.com/v1.15.24/en/learn/human-feedback-in-flows.md
- [HITL] https://docs.crewai.com/v1.15.24/en/learn/human-in-the-loop.md
- [HOOKS] https://docs.crewai.com/v1.15.24/en/learn/tool-hooks.md
- [AGENTS] https://docs.crewai.com/v1.15.24/en/concepts/agents.md
- [TOOLS] https://docs.crewai.com/v1.15.24/en/concepts/tools.md
- [CODE] https://docs.crewai.com/v1.15.24/en/tools/ai-ml/codeinterpretertool.md
- [MCP] https://docs.crewai.com/v1.15.24/en/mcp/overview.md
- [LLMS] https://docs.crewai.com/v1.15.24/en/concepts/llms.md
- [LITELLM] https://docs.crewai.com/v1.15.24/en/learn/litellm-removal-guide.md
- [PROC] https://docs.crewai.com/v1.15.24/en/concepts/processes.md
- [A2A] https://docs.crewai.com/v1.15.24/en/learn/a2a-agent-delegation.md
- [TEL] https://docs.crewai.com/v1.15.24/en/telemetry.md
- [TRACE] https://docs.crewai.com/v1.15.24/en/observability/tracing.md
- [PHX] https://docs.crewai.com/v1.15.24/en/observability/arize-phoenix.md
- [OPENLIT] https://docs.crewai.com/v1.15.24/en/observability/openlit.md
- [EVT] https://docs.crewai.com/v1.15.24/en/concepts/event-listener.md
- [TEST] https://docs.crewai.com/v1.15.24/en/concepts/testing.md
- [PRODARCH] https://docs.crewai.com/v1.15.24/en/concepts/production-architecture.md
- [AMP] https://docs-platform.crewai.com/platform/en/introduction
- [FACTORY] https://enterprise-docs.crewai.com/installation/requirements.md
- [PRICING] https://www.crewai.com/pricing
