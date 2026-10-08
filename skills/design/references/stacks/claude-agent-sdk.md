---
id: claude-agent-sdk
name: Claude Agent SDK
level: harness
nests_on: none
package: claude-agent-sdk
version_verified: 0.2.164
license: MIT
ts_sdk: full
verified_on: 2026-10-07
status: active
---

# Claude Agent SDK

## 1. What it is
A Python package that spawns and supervises a `claude` CLI subprocess (a native binary bundled in the wheel, 2.1.292 for this version) over stdio; the agent loop, the built-in tools (shell, files, web), hooks, permissions and the JSONL session transcripts all live in that subprocess, and the SDK adds `query()`, `ClaudeSDKClient`, in-process MCP tools and a `SessionStore` mirror. Sources: https://code.claude.com/docs/en/agent-sdk/hosting and https://code.claude.com/docs/en/agent-sdk/agent-loop . Version 0.2.164 (released 2026-10-06, still the latest on 2026-10-08), classifier "Development Status :: 3 - Alpha", Python >=3.10: https://pypi.org/project/claude-agent-sdk/ . License: MIT per the PyPI License field and the repo LICENSE file (https://github.com/anthropics/claude-agent-sdk-python/blob/v0.2.164/LICENSE ); use of the Claude Code CLI and Claude models through the SDK is governed by Anthropic's Commercial Terms of Service, also when it powers products for the user's own customers (https://github.com/anthropics/claude-agent-sdk-python/blob/v0.2.164/README.md ). A TypeScript SDK exists (`@anthropic-ai/claude-agent-sdk`, 0.3.293 on 2026-10-07): https://registry.npmjs.org/@anthropic-ai/claude-agent-sdk .

## 2. Filter attributes
| Attribute | Value | Source |
|---|---|---|
| model_portability | vendor-only (anthropic) | https://code.claude.com/docs/en/llm-gateway |
| a2a | none | https://code.claude.com/docs/en/agent-sdk/overview |
| mcp_client | native | https://code.claude.com/docs/en/agent-sdk/custom-tools |
| deploy_constraints | one Claude Code process per running turn (paused and idle sessions hold none), about 1 GiB until measured; local transcript files first | https://code.claude.com/docs/en/agent-sdk/hosting |
| default_egress | Anthropic usage metrics ON by default on the Claude API; CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 switches off; OTel export opt-in | https://code.claude.com/docs/en/data-usage |
| stability | alpha | https://pypi.org/project/claude-agent-sdk/ |

Notes on the filter values (each with its own source):
- model_portability: Claude models on the Anthropic API, Amazon Bedrock, Google Cloud's Agent Platform (Vertex), Microsoft Foundry and Claude Platform on AWS; gateways are supported but Anthropic "doesn't support routing Claude Code to non-Claude models through any gateway". Sources: https://code.claude.com/docs/en/agent-sdk/quickstart and https://code.claude.com/docs/en/llm-gateway
- a2a: no A2A support in the official docs read; third-party bridges exist (unverified, a web search on 2026-10-07 in the research file). Source: https://code.claude.com/docs/en/agent-sdk/overview
- mcp_client: in-process SDK MCP servers (`@tool`, `create_sdk_mcp_server`) and external MCP servers in `mcp_servers`. Source: https://code.claude.com/docs/en/agent-sdk/custom-tools
- deploy_constraints: each running turn maps to one subprocess and a paused or idle session holds none (observed); 1 GiB RAM, 5 GiB disk and 1 CPU per agent is the documented starting point (observed peak on a trivial one-tool session was 190 MiB on Windows, so the 1 GiB is a starting point from the docs, not a measurement of this build); transcripts are local JSONL files under `CLAUDE_CONFIG_DIR/projects/` and are lost with the container. Source: https://code.claude.com/docs/en/agent-sdk/hosting
- default_egress: the docs say metrics are default on for the Claude API and default off on Bedrock, Vertex, Foundry and Claude Platform on AWS; error reports apply to Pro and Max sign-ins; session surveys and the WebFetch domain check run on every provider. Observed (CLI 2.1.292, local model double, dummy key): a bare process opened `CONNECT api.anthropic.com:443`; `DISABLE_TELEMETRY=1` alone left it, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` removed it (purpose of that connection unverified). OTel export to an own collector works with metrics, traces (beta) and logs, prompts redacted by default. Sources: https://code.claude.com/docs/en/data-usage and https://code.claude.com/docs/en/agent-sdk/observability
- stability: Alpha classifier, six releases from 0.2.159 (2026-09-23) to 0.2.164 (2026-10-06), most of them bundling a new CLI; the docs ask to take patches continuously and read the changelog before a minor. Sources: https://pypi.org/project/claude-agent-sdk/ and https://github.com/anthropics/claude-agent-sdk-python/blob/v0.2.164/CHANGELOG.md

## 3. Seam mapping
(observed) in this card means seen in a scratch run on SDK 0.2.164 with the bundled CLI 2.1.292 against a scripted model double, not stated on a cited page.

| Seam | Support | How | Source |
|---|---|---|---|
| sessions | adapter | `SessionStore` protocol (`append`, `load`, optional list/delete); example Postgres, S3 and Redis adapters live in the repo (copy them, they are not packaged) with a conformance suite; the CLI writes the local JSONL first and the store is a mirror flushed before the result; a failed append is retried 3 times and then DROPPED with a `mirror_error` message while the run still succeeds (observed), so the build wraps the store to persist or fail the turn; DynamoDB and Firestore need a custom adapter | https://code.claude.com/docs/en/agent-sdk/session-storage and https://github.com/anthropics/claude-agent-sdk-python/blob/v0.2.164/examples/session_stores/postgres_session_store.py |
| hitl_gate | native | A PreToolUse hook returning `defer` ends the run with `stop_reason` tool_deferred and a `deferred_tool_use` payload; a later `query(resume=...)` fires the hook again for the same call; the docs say it works only when the turn has a single tool call, but on CLI 2.1.292 it was honored beside safe siblings and with two deferrals the earlier call was silently lost (observed), so the build adds a sibling guard, a `can_use_tool` fallback and an explicit permission mode; gated calls are then approved one at a time (N gated actions = N prompts and extra model requests), and the requested-call trajectory lists a retried call twice, so EXACT goldens recorded on other stacks fail here while IN_ORDER passes | https://code.claude.com/docs/en/hooks and https://code.claude.com/docs/en/agent-sdk/permissions |
| step_cap | native | `max_turns` allows N model requests then returns `error_max_turns` (observed); the count restarts on every `query()`, including a resume (observed); 0 or None means no cap (source) | https://code.claude.com/docs/en/agent-sdk/agent-loop and https://github.com/anthropics/claude-agent-sdk-python/blob/v0.2.164/src/claude_agent_sdk/_internal/transport/subprocess_cli.py |
| tool_call_cap | custom | No tool-call cap found (unverified absence); the build counts every tool_use block of a response at message_stop (partial messages on) before any PreToolUse hook decides, so a batch over the cap runs none, and stops the run with `continue_: False` (observed); the Python SDK has no whole-batch hook, PostToolBatch is TypeScript only | https://code.claude.com/docs/en/agent-sdk/hooks |
| model_provider | native | Anthropic API, Bedrock, Vertex, Foundry and Claude Platform on AWS selected by environment variables; non-Claude models are unsupported by policy | https://code.claude.com/docs/en/agent-sdk/quickstart and https://code.claude.com/docs/en/llm-gateway |
| telemetry | adapter | The CLI exports OTel traces (beta), metrics and logs from environment variables; span names are vendor-specific (`claude_code.interaction`, `llm_request`, `tool`), only some GenAI attributes exist and tokens are `input_tokens` and `output_tokens`, not `gen_ai.usage.*` (observed); W3C trace context from an app span is injected | https://code.claude.com/docs/en/agent-sdk/observability |
| eval_runner | custom | No official fake model or eval tooling found (unverified absence); a scripted Messages API server behind `ANTHROPIC_BASE_URL` gives deterministic trajectories and shows the first request's tool names (observed); the Python `Transport` ABC is a low-level internal API | https://code.claude.com/docs/en/llm-gateway and https://code.claude.com/docs/en/agent-sdk/python |
| deploy | adapter | The hosting guide documents self-hosting: container per task, long-running, hybrid with a SessionStore, plus a cookbook with Dockerfiles and Kubernetes manifests and sandbox options | https://code.claude.com/docs/en/agent-sdk/hosting |

## 4. Known traps
- [security] The 26 built-in tools (Bash, Read, Write, Edit, WebFetch and others) are in the model's tool list by default and `allowed_tools` does not remove them (observed: 26 built-ins beside one MCP tool); remove them with `tools=[]` and restrict permissions with rules. Source: https://code.claude.com/docs/en/agent-sdk/custom-tools and https://code.claude.com/docs/en/agent-sdk/permissions
- [security] Without an explicit permission mode the session can start in the model-judged `auto` mode (the initial mode was `default` in the observed isolated run, so check the init message); `bypassPermissions` ignores `allowed_tools`. Source: https://code.claude.com/docs/en/agent-sdk/permissions
- [security] With no system prompt set the SDK sends a minimal prompt that omits the safety instructions of the `claude_code` preset (observed: the SDK identity line and no safety text). Source: https://code.claude.com/docs/en/agent-sdk/modifying-system-prompts
- [security] User text containing `@file` mentions or slash commands is expanded by the CLI: with every tool removed, a file in the working directory still reached the model request (observed); set `verbatim_prompts=True`. Source: https://github.com/anthropics/claude-agent-sdk-python/blob/v0.2.164/CHANGELOG.md
- [ops] Tool search is on by default on the first-party API and defers MCP tool schemas, so the tool list the model sees differs from a test double at a local URL (unverified for api.anthropic.com); set `ENABLE_TOOL_SEARCH=false`. Source: https://code.claude.com/docs/en/agent-sdk/tool-search
- [ops] About 1 GiB RAM per concurrently running turn until measured (a starting point from the docs; paused and idle sessions hold no process) and one subprocess per run, so concurrency is bounded by container memory, not by the event loop. Source: https://code.claude.com/docs/en/agent-sdk/hosting
- [ops] `defer` in a multi-call turn: a gated call beside safe calls was deferred, and two deferrals kept only the last while the earlier call vanished from the history without a result (observed); a PreToolUse sibling guard is needed. Source: https://code.claude.com/docs/en/hooks
- [ops] Gated calls are approved one at a time: the sibling guard denies a second gated call in the same response, so N gated actions cost N approval prompts plus the model requests that retry them, and the retried call appears twice in the requested trajectory. Source: https://code.claude.com/docs/en/hooks
- [ops] `max_turns` restarts on every `query()`, so a turn that pauses and resumes gets a fresh allowance, and `max_turns=0` is treated as no cap (source). Source: https://github.com/anthropics/claude-agent-sdk-python/blob/v0.2.164/src/claude_agent_sdk/_internal/transport/subprocess_cli.py
- [ops] A wall-clock cancel leaves a dangling tool call that the next resume answers with "The user doesn't want to take this action right now" for a tool that may have run (observed); the build adds an outcome-unknown notice. Source: https://code.claude.com/docs/en/agent-sdk/hosting
- [data] Session persistence to the external store is best effort: after 3 failed attempts the batch is dropped with a `mirror_error` message and the run still reports success, and a run resumed from the store deletes its local copy at the end. Source: https://code.claude.com/docs/en/agent-sdk/session-storage
- [data] Usage metrics are on by default on the Claude API and the bare CLI contacts api.anthropic.com beside the model host (observed); set the kill-switch variables and prove them with a proxy. Source: https://code.claude.com/docs/en/data-usage
- [churn] A resume works by sending no prompt and keeping stdin open until the first result; the docs show resume with `claude -p --resume`, and an empty prompt stream or an extra prompt behaved differently (observed), so the continuation depends on undocumented hold-stdin behavior. Source: https://code.claude.com/docs/en/hooks
- [churn] The Python package is Alpha and 0.x; each release bundles a different native CLI (2.1.292 here), so behavior can change in any release. Source: https://pypi.org/project/claude-agent-sdk/ and https://github.com/anthropics/claude-agent-sdk-python/blob/v0.2.164/CHANGELOG.md

## 5. Pick when / avoid when
Pick when the agent is committed to Claude and needs a shell, files or other coding-agent tools, or Claude Code's hooks and permission rules, because those come with the CLI (https://code.claude.com/docs/en/agent-sdk/overview and https://code.claude.com/docs/en/agent-sdk/hosting ), and when a pause that outlives the process is wanted: a deferred tool call ends the process and resumes from the persisted session, with no memory held while waiting (https://code.claude.com/docs/en/hooks ). The build still owns the Postgres store wrapper, the gate guard, the tool-call cap and the egress switches.
Avoid when the agent is a business chat agent at high concurrency, since every running turn is a process of about 1 GiB until measured (paused and idle sessions hold none) (https://code.claude.com/docs/en/agent-sdk/hosting ), when the model provider must be swappable (https://code.claude.com/docs/en/llm-gateway ), when A2A is required (https://code.claude.com/docs/en/agent-sdk/overview ), or when an API that changes with every weekly CLI bundle cannot be absorbed (https://pypi.org/project/claude-agent-sdk/ ).

## 6. Build binding
`skills/build/references/bindings/claude-agent-sdk.md`
