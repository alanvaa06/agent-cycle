# Stack card: Claude Agent SDK (as of 2026-10-07)

Legend: every claim cites a URL read on 2026-10-07. **unverified** = not confirmed on a page. **inference** = my reasoning.

Source keys:
[OV] https://code.claude.com/docs/en/agent-sdk/overview ·
[HOST] https://code.claude.com/docs/en/agent-sdk/hosting ·
[STORE] https://code.claude.com/docs/en/agent-sdk/session-storage ·
[SESS] https://code.claude.com/docs/en/agent-sdk/sessions ·
[PERM] https://code.claude.com/docs/en/agent-sdk/permissions ·
[INPUT] https://code.claude.com/docs/en/agent-sdk/user-input ·
[HOOKS] https://code.claude.com/docs/en/agent-sdk/hooks ·
[CCHOOKS] https://code.claude.com/docs/en/hooks ·
[LOOP] https://code.claude.com/docs/en/agent-sdk/agent-loop ·
[PY] https://code.claude.com/docs/en/agent-sdk/python ·
[TS] https://code.claude.com/docs/en/agent-sdk/typescript ·
[TOOLS] https://code.claude.com/docs/en/agent-sdk/custom-tools ·
[SUB] https://code.claude.com/docs/en/agent-sdk/subagents ·
[OBS] https://code.claude.com/docs/en/agent-sdk/observability ·
[MON] https://code.claude.com/docs/en/monitoring-usage ·
[QS] https://code.claude.com/docs/en/agent-sdk/quickstart ·
[GW] https://code.claude.com/docs/en/llm-gateway ·
[COST] https://code.claude.com/docs/en/agent-sdk/cost-tracking ·
[SYS] https://code.claude.com/docs/en/agent-sdk/modifying-system-prompts ·
[MA] https://platform.claude.com/docs/en/managed-agents/overview ·
[PYPI] https://pypi.org/project/claude-agent-sdk/ (+ /pypi/claude-agent-sdk/json) ·
[NPM] https://registry.npmjs.org/@anthropic-ai/claude-agent-sdk ·
[CHLOG] https://github.com/anthropics/claude-agent-sdk-python/blob/main/CHANGELOG.md

---

## 1. Identity

| Item | Python | TypeScript |
|---|---|---|
| Package | `claude-agent-sdk` [PYPI] | `@anthropic-ai/claude-agent-sdk` [NPM] |
| Latest | 0.2.164, released 2026-10-06 [PYPI] | 0.3.293, published 2026-10-07 [NPM] |
| Runtime | Python >= 3.10 [PYPI] | Node >= 18 (`engines`) [NPM]; peer deps `zod ^4`, `@anthropic-ai/sdk`, `@modelcontextprotocol/sdk` [NPM] |
| License field | MIT [PYPI] | "SEE LICENSE IN README.md" [NPM] |
| Maturity | PyPI classifier "Development Status :: 3 - Alpha" [PYPI] | 0.x |

- **Terms:** use is governed by Anthropic's Commercial Terms of Service, including when powering products for your own customers [OV].
- **Versioning:** "The SDK follows semver: take patch releases continuously and review the ... changelog before taking a minor" [HOST]. Both packages are still 0.x, and breaking changes have landed in minors, e.g. 0.2.137 widened the `Message` union [CHLOG].
- **Subprocess architecture:** the SDK spawns and supervises a `claude` CLI subprocess over stdio. That subprocess owns the shell, the working directory, and the JSONL transcripts [HOST]. Both SDKs bundle a native Claude Code binary pinned to the SDK version, and the spawned CLI needs no separate Node.js install [HOST]. Each Python release bumps the bundled CLI version (0.2.164 bundles CLI 2.1.292) [CHLOG]. Edge cases: ARM64 Windows sdists and `npm ci --omit=optional` ship no binary [QS].
- **Branding:** you may not call your product "Claude Code" [OV].

## 2. Core abstractions and the agent loop

- **`query()`:** an async iterator, new session by default. **`ClaudeSDKClient`** (Python) reuses one session across exchanges and supports interrupts. Both support hooks and custom tools [PY]. TypeScript has no client object: use `continue: true`/`resume` [SESS], or `streamInput()`, `startup()` and `prewarm()` for warm long-lived sessions [HOST][TS].
- **Options:** `ClaudeAgentOptions` / `Options` carry `tools`, `allowed_tools`, `disallowed_tools`, `permission_mode`, `can_use_tool`, `hooks`, `mcp_servers`, `agents`, `model`, `fallback_model`, `max_turns`, `max_budget_usd`, `task_budget`, `setting_sources`, `env`, `cwd`, `sandbox`, `effort` and `transport` [PY].
- **The loop:** prompt -> Claude answers with text and/or tool calls -> the SDK executes the tools -> results feed back. This repeats until a response has no tool calls. The stream yields `AssistantMessage`/`UserMessage`, then a `ResultMessage` with usage, cost and `session_id` [LOOP].
- **Concurrency inside a turn:** read-only tools run concurrently; state-changing tools run sequentially [LOOP].
- **Default system prompt:** if you set none, the SDK uses a *minimal* system prompt that omits the `claude_code` preset's safety instructions [SYS].

## 3. State and sessions

- **Default storage:** transcripts are JSONL under `~/.claude/projects/` and are lost on container restart [HOST][STORE].
- **Session operations:** continue (most recent session), resume (by ID) and fork (copy history into a new ID) [SESS].
- **Durable storage: the `SessionStore` adapter.** It needs `append` and `load`, with optional `list_sessions`, `list_session_summaries`, `delete` and `list_subkeys` [STORE]. There are reference adapters for **S3, Redis and Postgres** in both repos, plus a conformance suite (`claude_agent_sdk.testing.run_session_store_conformance`) [STORE]. DynamoDB and Firestore need your own adapter (inference: the KV and document patterns map directly).
- **Caveats** [STORE]:
  - The store is a *mirror*, not the primary copy: the CLI writes to local disk first.
  - Mirror writes are best-effort. Failures emit a `mirror_error` system message and the batch is dropped, so dedupe by `entry.uuid`.
  - Only transcripts are mirrored. `CLAUDE.md` and working-directory files are not.
  - `projectKey` encodes the working directory, so resume needs a matching `cwd` or `CLAUDE_CODE_PROJECT_DIR_NAME`.
  - Concurrent `append` calls for the same session can race on the summary sidecar, so you must serialize them.
- **Concurrency per session:** one session maps to one subprocess. For long-running pools, pin each session to one container by consistent hashing on `sessionId` [HOST]. The docs show no locking for two writers on one session (**unverified**). The pipeline's serial-per-user worker covers this (inference).
- **Stateless containers:** the documented "hybrid" pattern runs ephemeral containers that hydrate from the `SessionStore` on resume. The docs say the store "is required for this pattern, not optional" [HOST].

## 4. HITL and the approval gate

- **Evaluation order:** hooks -> deny rules -> ask rules -> permission mode -> allow rules -> `canUseTool` [PERM].
- **Modes:** `default`, `dontAsk`, `acceptEdits`, `bypassPermissions`, `plan`, and `auto` (model-classified) [PERM].
- **Unset mode can start in `auto`:** if you omit the mode, Claude Code may start in auto mode. Pass `default` explicitly [PERM].
- **`canUseTool` is not a reliable gate on its own:** tools approved by allow rules or by the mode never reach the callback [PERM].
- **For a gate that always fires, use a `PreToolUse` hook.** It runs before everything else, and its deny holds even in `bypassPermissions` [PERM]. It returns `allow`, `deny`, `ask` or **`defer`** [HOOKS].
- **The callback can stay pending indefinitely** [INPUT].
- **Async approvals with `defer`:** when the human answers later, `defer` ends the turn with `stop_reason: "tool_deferred"` and a `deferred_tool_use` payload. You resume later and the hook fires again [CCHOOKS][PY]. Limits:
  - No timeout. Sessions are swept after 30 days by default.
  - Works **only when Claude makes a single tool call in that turn**. Otherwise `defer` is ignored [CCHOOKS].
- **Mapping to the pipeline's tiers (inference):** `safe` maps to `allowed_tools`. `reversible` and `destructive` map to a `PreToolUse` hook that checks a tier registry and returns `defer` or `ask`, combined with `dontAsk` for everything unlisted.

## 5. Caps

- **Steps:** `max_turns` counts tool-use round trips; the result subtype is `error_max_turns` [LOOP].
- **Spend:** `max_budget_usd` stops on a *client-side estimate* [PY][COST], and the cost fields are "not authoritative billing data" [COST]. `task_budget` is an API-side token budget (beta) [PY].
- **Tool calls:** no separate tool-call cap exists. None is documented in [PY]/[TS]/[LOOP] (**unverified absence**). Build it as a `PreToolUse` hook counter that denies past N calls (inference).
- **Subagents:** `maxTurns` per `AgentDefinition`. There is no session timeout and no per-subagent wall-clock deadline [HOST][SUB].

## 6. Model providers

- **Supported:** Anthropic API, Amazon Bedrock (`CLAUDE_CODE_USE_BEDROCK`), Claude Platform on AWS, Google Cloud's Agent Platform/Vertex (`CLAUDE_CODE_USE_VERTEX`) and Microsoft Foundry (`CLAUDE_CODE_USE_FOUNDRY`) [QS].
- **Gateways:** supported via `ANTHROPIC_BASE_URL`. Anthropic "doesn't support routing Claude Code to non-Claude models through any gateway" [GW].
- **Implication:** Claude-only. LiteLLM can sit in front as a proxy for Claude models, but you cannot use it to swap to GPT or Gemini (inference, from [GW]).

## 7. Tools and least privilege

- **Built-ins:** reading, writing and editing files, running commands, and web search [OV]. Hook matchers list Bash, Read, Write, Edit, Glob, Grep, WebFetch, Agent and others [HOOKS].
- **Availability:** `tools: [...]` whitelists built-ins and `tools: []` removes them all. A bare name in `disallowed_tools` removes that tool from context [TOOLS][PERM].
- **Permission:** `allowed_tools` only *auto-approves* the listed tools; it does not restrict the tool set. `allowed_tools` does not constrain `bypassPermissions` [PERM].
- **Custom tools:** in-process MCP servers built with `@tool` and `create_sdk_mcp_server`, which run inside your app process [TOOLS]. MCP annotations like `destructiveHint` are "informational only" [TOOLS]. External MCP servers are also supported, and `strict_mcp_config` ignores ambient MCP config [PY].
- **Multi-tenant hardening:** `setting_sources=[]`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, a per-tenant `CLAUDE_CONFIG_DIR` and `cwd`, and egress proxy rules [HOST].

## 8. Multi-agent

- **Subagents:** defined via `agents` / `AgentDefinition` (tools, model, `maxTurns`, `permissionMode`, MCP servers). Subagents run in the background by default and can nest. A built-in `general-purpose` subagent is always available unless disabled [SUB].
- **A2A:** no native support found in the official docs. Only third-party bridges exist (a2claude, a2acode, a2a-adapter) per a web search on 2026-10-07 (**unverified**). You would wrap the agent in an A2A server yourself (inference).

## 9. Observability

- **Who emits telemetry:** the CLI, not the SDK. You configure it through env vars: `CLAUDE_CODE_ENABLE_TELEMETRY=1`, `OTEL_*_EXPORTER=otlp`, and `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1` for traces [OBS].
- **Traces are beta.** Span names are `claude_code.interaction`, `claude_code.llm_request` and `claude_code.tool` [OBS].
- **Trace context:** W3C context propagates from your span into the subprocess [OBS].
- **GenAI semantic conventions are partial:** some attributes follow them (`gen_ai.system`, `gen_ai.request.model`, `gen_ai.response.id`, `gen_ai.tool.call.id`) [MON], but span names are vendor-specific (inference: not the semconv `chat`/`execute_tool` names).
- **Backend:** backend-agnostic OTLP [OBS]. Prompts and tool inputs are excluded unless you opt in [OBS].

## 10. Testing and evals

- **Trajectory capture:** the message stream carries `ToolUseBlock`s with `parent_tool_use_id` for subagents [SUB][PY], and `PostToolUse` hooks can log every call [HOOKS]. This is enough to drive EXACT / IN_ORDER / ANY_ORDER assertions in pytest (inference).
- **Model doubles:** no official model-double or offline mode is documented (**unverified absence**). Python exposes a custom `Transport` ABC, marked a "low-level internal API" that may change [PY]. A fake transport replaying recorded stream JSON is possible but brittle (inference). `InMemorySessionStore` exists for tests [STORE].
- **Eval tooling:** none ships with the SDK (unverified absence).

## 11. Deployment and costs

- **Container sizing:** start at 1 GiB RAM, 5 GiB disk and 1 CPU per agent; memory grows with session length [HOST].
- **Hosting:** the cookbook has Docker, Modal and Kubernetes examples [HOST]. Patterns are ephemeral, long-running, hybrid and multi-agent [HOST].
- **Network:** outbound access to the API or to the Bedrock/Vertex endpoint [HOST].
- **Cost:** tokens dominate. A container costs about $0.05/hr, while a long session can cost dollars [HOST].
- **Auth:** API keys only. Third parties may not offer claude.ai login or subscription rate limits without approval [OV].
- **Isolation:** for sandboxing, see secure deployment (gVisor, Firecracker) [HOST].

## 12. When to pick it, and when not to

**Pick it** for agents that need a filesystem or shell, coding or document work, Claude Code's hooks, subagents or skills, and a Claude-only stack [OV][HOST].

**Avoid it, or isolate it, when:**
- **The model must be swappable.** It is Claude-only [GW].
- **Requests must be cheap and stateless.** There is one subprocess per session, about 1 GiB each, and roughly 230-260 MB per warm spare [HOST][TS].
- **You want strict semconv telemetry** [MON].
- **You need a stable API.** It is 0.x/Alpha with a bundled CLI that changes weekly [PYPI][CHLOG].
- **The agent is a thin chat agent.** Coding-agent heritage brings ambient config loading, CLAUDE.md, auto memory, and a possible `auto` default mode that you must actively turn off [HOST][PERM].

**Managed Agents (3 lines).** Claude Managed Agents is a beta (`managed-agents-2026-04-01`) Anthropic-hosted harness: you define Agent, Environment, Session and Events over the API, with SSE streaming and server-side persisted history [MA]. Tools run in an Anthropic cloud sandbox or a self-hosted sandbox. It is not ZDR- or HIPAA-BAA-eligible [MA]. It is the "don't run the loop yourself" sibling of the Agent SDK, which you self-host in your own process [OV][HOST], but it is equally Claude-only and moves session state to Anthropic, which conflicts with a repository-owned session seam (inference).

## 13. Verdict

The fit with the pipeline is **partial** (inference throughout).

**Seams that fit:**
- **HITL gate:** the strongest seam. `PreToolUse` with `defer` gives a real async gate that suits WhatsApp approvals arriving hours later. Limitations: only one tool call per turn, and you must set `dontAsk`/`default` explicitly.
- **Step cap:** native via `max_turns`.
- **MCP tools:** native.
- **Deploy targets:** Docker Compose, AWS and GCP all work if you size for one subprocess per session.

**Seams that need custom work:**
- **Tool-call cap:** a hook counter.
- **Durable sessions:** a `SessionStore` adapter. Postgres has a reference adapter; DynamoDB and Firestore need your own. It is a best-effort mirror tied to `cwd`, not a primary repository.
- **Eval doubles:** no official fake model.
- **A2A:** you must wrap the agent yourself.

**Seams that conflict:**
- **Model swap:** LiteLLM-style swapping fails, because the SDK is Claude-only by policy.
- **Telemetry:** OTel works, but span names are vendor-specific with only partial GenAI attributes.

**Recommendation:** use this card for Claude-committed agents that need shell, files or long tasks. For WhatsApp-style business chat agents, where provider swap and a lightweight stateless worker matter, a thinner loop (the Client SDK tool runner or a provider-agnostic framework) fits the seams better. The Agent SDK is the heavier choice there.
