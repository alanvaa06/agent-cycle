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

---

## Build-binding observations (2026-10-08)

Method. `claude-agent-sdk==0.2.164` (bundled CLI 2.1.292, `claude_agent_sdk/_cli_version.py`) installed in a scratch venv outside the repo (Python 3.12.10, Windows 11; resolved `mcp` 2.3.0, `anyio` 4.15.1, `opentelemetry-*` 1.45.1, `pydantic` 2.14.0). No real model was called and no real credential was used: the CLI ran with a dummy `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL=http://127.0.0.1:<port>` against a stdlib scripted Messages API double (SSE streaming; every request logged; one scripted response per main request). Every "observed" in the card and binding is a run of that setup on CLI 2.1.292 (the heading of each group names the binding spike that repeats it against the real provider). Values below are copied from the run output. The scripts live in the session scratchpad and are not part of the repo.

Sources added in this pass (all fetched 2026-10-08): the hooks reference https://code.claude.com/docs/en/hooks (PreToolUse `defer`, `continue`, `PostToolBatch`), the SDK pages hooks, permissions, user-input, session-storage, sessions, hosting, agent-loop, observability, custom-tools, tool-search and modifying-system-prompts (all under https://code.claude.com/docs/en/agent-sdk/), https://code.claude.com/docs/en/data-usage, https://code.claude.com/docs/en/llm-gateway, PyPI https://pypi.org/pypi/claude-agent-sdk/json, and files at the tag v0.2.164 of https://github.com/anthropics/claude-agent-sdk-python (`src/claude_agent_sdk/types.py`, `_internal/query.py`, `_internal/transport/subprocess_cli.py`, `_internal/transcript_mirror_batcher.py`, `testing/session_store_conformance.py`, `examples/session_stores/postgres_session_store.py`, `README.md`, `CHANGELOG.md`, `LICENSE`). Page text addressed to AI agents: none beyond the navigation note every docs page opens with ("Fetch the complete documentation index at https://code.claude.com/docs/llms.txt"), which was not acted on. PyPI: 0.2.164 is the latest release (2026-10-06, rechecked 2026-10-08).

### Version, license, terms
- PyPI metadata: License field "MIT", classifier "License :: OSI Approved :: MIT License", "Development Status :: 3 - Alpha", Python >=3.10, `mcp>=1.23.0,<3`. The repo `LICENSE` at the tag is MIT (Anthropic, PBC, 2025). The README (the PyPI long description) ends with "License and terms": use is governed by Anthropic's Commercial Terms of Service, including when the SDK powers products for the user's own customers, "except to the extent a specific component or dependency is covered by a different license". The card uses `LicenseRef-Anthropic-Commercial` as the plan instructs for commercial terms and records the MIT file and metadata in prose.
- Release cadence: 0.2.158 to 0.2.164 in September and October 2026 (changelog); most releases only bump the bundled CLI (0.2.164 bundles 2.1.292, 0.2.163 2.1.286, 0.2.162 2.1.285). 0.2.158 added `verbatim_prompts`; 0.2.160 changed when stdin closes after background subagents.

### Tool surface and system prompt (binding spike 11; first request seen by the double)
- `tools=[]` + SDK MCP server + `allowed_tools=[mcp__tools__lookup]`: the first request's `tools` was exactly `['mcp__tools__lookup']`.
- Negative control, no `tools=` (only `allowed_tools`): 27 names, 26 built-ins (Agent, Bash, CronCreate, CronDelete, CronList, DesignSync, Edit, EnterWorktree, ExitWorktree, Glob, Grep, ListAgents, Monitor, NotebookEdit, PowerShell, PushNotification, Read, ReportFindings, ScheduleWakeup, SendMessage, Skill, TaskStop, WebFetch, WebSearch, Workflow, Write) plus the MCP tool. `allowed_tools` does not restrict.
- System prompt: with a string `system_prompt` the request carries a billing-header line, the line "You are a Claude agent, built on Anthropic's Claude Agent SDK." and the string. With none set, only the billing header and that identity line: no safety text (matches https://code.claude.com/docs/en/agent-sdk/modifying-system-prompts).
- The init system message carries `permissionMode`, `tools`, `mcp_servers`, `claude_code_version`: an unset mode was reported as `default` in this isolated setup (the docs say the unset mode can be `auto`: https://code.claude.com/docs/en/agent-sdk/permissions); explicit `default` and `dontAsk` were reported as set.
- Tool search: `ENABLE_TOOL_SEARCH` unset or `false` with a non-first-party base URL gave the eager tool list; `true` added a `DeferredToolPlaceholder` entry to the list. The docs say tool search is on by default and is turned off for a non-first-party `ANTHROPIC_BASE_URL` (https://code.claude.com/docs/en/agent-sdk/tool-search), so a double at a local URL hides the production default: unverified for api.anthropic.com (no real call), hence the binding sets `ENABLE_TOOL_SEARCH=false` everywhere.

### PreToolUse `defer`, resume and multi-call turns (binding spikes 4 to 6)
- Single gated call (hook returns `defer`): the result is `subtype=success`, `stop_reason=tool_deferred`, `deferred_tool_use={id,name,input}`, `terminal_reason=tool_deferred`, zero tool bodies run, one model request.
- Resume = a new `query(resume=<session id>)`. The hook fires again for the same `tool_use_id`; `allow` runs the body, then ONE model request follows (its input ends with the `tool_result` plus the CLI's own text "Continue from where you left off."). Any prompt message sent with the resume starts a second turn and a second model request (a one-message stream, a string prompt and an empty string prompt all did). An empty prompt stream closed stdin at once and the result was `tool_deferred_unavailable` (`is_error`, ProcessError). A prompt iterable that sends nothing and waits until the first `ResultMessage` before ending (the "hold stream") gave exactly the deferral continuation: 2 model requests in total, num_turns 1 on both runs.
- `max_turns` after a resume: the first run with `max_turns=1` deferred (turn 1); the resume with `max_turns=1` completed (`success`, turns 1): the count restarts on every `query()`.
- Multi-call turns (one assistant message with 2 or 3 `tool_use` blocks; also with a 1.5 s gap between blocks): the CLI waits for the whole message; hooks ran one after another in block order, each awaited (0.5 s sleeps did not overlap); the deferral WAS honored for a gated call that had a safe sibling (the sibling ran and its `tool_result` was saved; after the resume the request had both `tool_use` ids and both results). That contradicts the docs sentence that defer only works with a single tool call in the turn and is otherwise ignored with a warning (https://code.claude.com/docs/en/hooks). Two gated calls both answered `defer`: the result reported only the LAST one (`deferred_tool_use.id` was the second) and after the resume the first `tool_use` was absent from the request history: silently lost, never executed, never answered. `can_use_tool` was not consulted in any of these runs.
- Sibling guard (first gated call `defer`, any later gated call in the same run `deny` with a reason): the first was deferred, the second got an error `tool_result` ("PreToolUse:mcp__tools__refund hook error: <reason>"), `permission_denials` listed it, and after approval both ids were paired in the history.
- Deny on resume with the hook (`permissionDecision: deny`): `tool_result` error "PreToolUse:... hook error: DENIED...", then the model is called once more. `continue_: False` combined with that deny did NOT stop the run on the resume (the model request was still made).
- Deny-ends-turn on resume: the hook returns `{}` for the call and `can_use_tool` returns `PermissionResultDeny(message=..., interrupt=True)`: the `tool_result` is saved with the message, ZERO model requests, result `error_during_execution`, `terminal_reason=aborted_streaming`, and `query()` raises `ProcessError` (exit 1). A follow-up turn on the same session was valid (the history had the paired denial). With `interrupt=False` there was a model request.
- Unresolved deferral + a new prompt (no decision ever applied): on the next `resume` the hook fired again for the dangling call (the test hook deferred it again and a first `ResultMessage` with `tool_deferred` appeared before the prompt ran); the later request showed that call paired with "[Tool result missing due to internal error]".
- Edit: on the resume the hook returned `allow` + `updatedInput` (changed args): the body ran with the changed args; the history still shows the model's original `tool_use` input, so the tool result must state the args actually used. `updatedInput` with `allow` also overwrote a model-supplied field and reached the in-process tool body (idempotency key channel; the model-supplied value was replaced).
- Resume from the store after the local transcripts were deleted worked with the hold stream.

### Caps (binding spike 7)
- `max_turns=N` with endless safe tool use: exactly N model requests and N tool executions, then `error_max_turns` (`terminal_reason=max_turns`), `ResultMessage.num_turns` = N+1, and `query()` raises `ResultError` ("Reached maximum number of turns (N)"). A follow-up turn on that session worked (all `tool_use` ids paired).
- `if self._options.max_turns:` in `_internal/transport/subprocess_cli.py` (line 610): `max_turns=0` or `None` adds no `--max-turns`: no cap.
- Tool cap with a hook counter on every PreToolUse call: batch of 3, cap 2: 2 bodies ran, the 3rd was denied; with a deny alone the model was called again (2 requests, `success`, `end_turn`); with the deny plus `continue_: False` there was NO further model request and the result was `subtype=success`, `stop_reason=tool_use`, `terminal_reason=hook_stopped`. Both leave the history valid for a follow-up turn (the denied call paired with "PreToolUse:... hook error: tool-call cap reached"). `continue_: False` also took effect inside a resumed run, for the calls after the deferred one.
- The re-fired hook of a deferred call is a second invocation for the same `tool_use_id`: a counter must dedupe by id.
- Python hooks: the hooks page lists `PostToolBatch` as TypeScript only; the Python SDK has no hook that sees a whole batch.
- Pause at the last allowed step (STEP_CAP 1): the resume with `max_turns=1` ran the approved body, made one model request, a hook that denied every tool (frozen flag) denied the model's new `tool_use`, and the run ended `error_max_turns`.

### Sessions, mirror and crash (binding spikes 1, 2 and 8)
- A user message in streaming input may carry `uuid`; the transcript's `user` entry kept it (also in the store copy). Entry types seen in the store for one turn: queue-operation, user, attachment, file-history-snapshot, atis-latch, assistant, last-prompt, cost-state.
- A fresh session leaves the local JSONL under `CLAUDE_CONFIG_DIR/projects/<encoded cwd>/<session id>.jsonl` and the store gets a copy; a run resumed from the store (local file deleted) wrote its entries to the store and left NO local file afterwards (matches https://code.claude.com/docs/en/agent-sdk/session-storage).
- Mirror failures: an `append` that failed 2 times then succeeded produced no error message (3 attempts); failing 3 times produced a `MirrorErrorMessage` (`subtype=mirror_error`) and the run still ended `success`. The flush happens before the `ResultMessage` is yielded (source: `_internal/query.py`, `await self._transcript_mirror_batcher.flush()` in the result branch).
- Resume with a different `cwd` and no local copy: "No conversation found with session ID" (ResultError); with the original `cwd` it worked.
- Kill of the CLI process during a tool body: the store (flushed by the SDK's close) held the `assistant` `tool_use` and no result; the next resume sent that call paired with "[Tool call interrupted: the session ended before this call's result was recorded, so its outcome is unknown. Check whether it took effect before relying on it or running it again.]" and did NOT re-fire the hook.
- Wall clock: `asyncio.timeout(8)` around the stream during a 30 s tool: after the cancel no `claude` process remained; the next resume sent the dangling call paired with "The user doesn't want to take this action right now. STOP what you are doing and wait for the user to tell you how to proceed.": a rejection text for a tool that may have run (the binding corrects it with a notice).
- Observed CLI process RSS in a one-tool session on Windows: 190 MiB peak over about twenty samples; the docs' starting point is 1 GiB RAM per agent.
- Conformance: `run_session_store_conformance` ("14 behavioral contracts", `testing/session_store_conformance.py`) passed against a delegating `DurableStore` wrapper (retry with backoff until a deadline, then a failure flag and re-raise) around `InMemorySessionStore`; the wrapper recovered after 2 injected failures and set the flag after a hard failure. The Postgres reference adapter was read (`append` is one multi-row INSERT, no dedupe by `uuid`, `create_schema()` is called by the app) and NOT run: there is no Postgres in the scratch environment. Its README says each adapter passes the suite; the live tests skip unless env vars are set.

### Egress and OpenTelemetry (binding spike 10)
- Default egress: with the dummy key and a local base URL, behind an `HTTPS_PROXY`/`HTTP_PROXY` that logged and refused everything (with `NO_PROXY=127.0.0.1,localhost`), the CLI sent `CONNECT api.anthropic.com:443` although no model traffic went there. With `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` alone: no CONNECT; with `DISABLE_TELEMETRY=1` alone: still the CONNECT; with the six variables (`DISABLE_TELEMETRY`, `DISABLE_ERROR_REPORTING`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`, `DISABLE_AUTOUPDATER`, `DISABLE_FEEDBACK_COMMAND`, `CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY`): none. The purpose of that connection is not stated on a page read (unverified). The double then only ever received `POST /v1/messages?beta=true`.
- Docs (https://code.claude.com/docs/en/data-usage): metrics (latency, reliability, usage; never code, prompts or file paths) are default on for the Claude API and off for Bedrock, Vertex, Foundry and Claude Platform on AWS; error reports apply to Pro and Max sign-ins on v2.1.198+; session quality surveys are default on for every provider; `/feedback` is default on for the Claude API.
- OTel (http/json to a local receiver, `CLAUDE_CODE_ENABLE_TELEMETRY=1`, `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1`, the three `OTEL_*_EXPORTER=otlp`, intervals 1000, together with `DISABLE_TELEMETRY=1` and `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`): traces, metrics and logs arrived at the local receiver, zero proxy lines. Span names: `claude_code.interaction`, `claude_code.llm_request`, `claude_code.tool`, `claude_code.tool.blocked_on_user`, `claude_code.tool.execution`; all in the trace of an app span that was active in the Python process (`TRACEPARENT` injected by the SDK; trace ids equal). `llm_request` attributes: `gen_ai.system`, `gen_ai.request.model`, `gen_ai.response.finish_reasons`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens`, `model`, `stop_reason`, `session.id`, `user.id`; tool spans: `gen_ai.tool.call.id`, `tool_name`, `tool_use_id`. No `gen_ai.usage.*`. Metrics: `claude_code.token.usage`, `claude_code.cost.usage`, `claude_code.session.count`. Log events include `user_prompt`, `assistant_response`, `tool_result`, `api_request`: the prompt and response text fields were `<REDACTED>` by default; `tool_result` carried sizes only.
- `ResultMessage.usage` is cumulative for the run (input 323 = 123 + 200 and output 54 = 45 + 9 over the double's two responses) and `model_usage` carries `costUSD`; each model response is one `AssistantMessage` with a distinct `message_id` (used for the step count).

### Prompt hygiene (binding spike 4)
- `@secret.txt` in the user text with `tools=[]` and everything locked: the file content (a file in `cwd`) reached the model request. With `verbatim_prompts=True` it did not. (`verbatim_prompts` since 0.2.158: https://github.com/anthropics/claude-agent-sdk-python/blob/v0.2.164/CHANGELOG.md.)

### Not run / unverified
- A live Postgres, DynamoDB or Firestore store; any real model call (so real usage numbers, real streaming timing of multi-block responses and the production tool-search default are unverified); a real external MCP server through the hook; A2A; Bedrock, Vertex or Foundry routes; Linux memory figures.
