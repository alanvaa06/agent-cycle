# Stack card: "No framework" (own tool-use loop on a provider API)

Researched 2026-10-07. Every factual claim cites a page read today. **unverified** = not confirmed on a primary page. **inference** = my reasoning.

## 1. The minimal loop and what SDKs give you for free

**Loop (Anthropic Messages API):** call `messages.create` with `tools`. If `stop_reason == "tool_use"`, run each `tool_use` block (`id`, `name`, `input`). Send back one `user` message with `tool_result` blocks (`tool_use_id`, `content`, optional `is_error`) and repeat until no tool call remains. Rules that are easy to get wrong: results must immediately follow the tool-use message, and `tool_result` blocks must come FIRST in the content array, before any text. Getting this wrong returns a 400. (https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls)

**Loop (OpenAI Responses API):** the output contains `function_call` items (`call_id`, `name`, JSON `arguments`). You append a `function_call_output` with the same `call_id` and call again. `parallel_tool_calls=false` limits a turn to zero or one call. `strict: true` requires `additionalProperties: false` and every field listed in `required`. The guide has you write the loop yourself and does not document an SDK auto-loop helper. It points to the Agents SDK when you want a framework. (https://developers.openai.com/api/docs/guides/function-calling)

**Free helper: the Anthropic Tool Runner (beta).** `client.beta.messages.tool_runner(...)` with the `@beta_tool` decorator, which derives the schema from type hints and the docstring. It "handles the agentic loop, error wrapping, and type safety", supports `max_iterations`, and lets you `break` out of any iteration. `generate_tool_call_response()` and `append_messages()` let you inspect a result or take over history yourself. It ships in the Python, TS, C#, Go, Java, PHP and Ruby SDKs. The docs say to use the **manual loop** "when you need human-in-the-loop approval, custom logging, or conditional execution". (https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-runner)

**Versions:** `anthropic` 1.12.0, released 2026-10-07 (https://pypi.org/project/anthropic/). `openai` 3.26.0, Apache-2.0, release date unverified (https://pypi.org/pypi/openai/json).

## 2. State and sessions (inference)

You build all of it. The minimum is a `sessions` table (id, user_id, status, step_count, tool_call_count, created/updated) and a `messages` table (session_id, seq, role, content JSONB holding the provider-native blocks, plus a provider/model tag), behind a `SessionRepository` interface. This maps directly onto Postgres or Supabase. On DynamoDB or Firestore, use a `session_id` partition key with `seq` as the sort key. The tricky part is not the storage but **canonical format**: if the provider can change, store one neutral shape (e.g. OpenAI-style `tool_calls`, which is what LiteLLM uses) and convert at the edge. Otherwise histories cannot be replayed across providers.

## 3. HITL gate (inference)

Keep a tool registry where each tool has a tier (`safe | reversible | destructive`). In the loop, before running a `tool_use` block whose tier is gated:

1. Save the pending call (session_id, tool_use_id, name, input, tier) and set the session to `awaiting_approval`.
2. Return or notify, and end the worker turn. No thread blocks while waiting.
3. When the approval webhook arrives, load the session, then run the tool (approved) or synthesize a `tool_result` with `is_error: true, content: "Denied by operator: <reason>"` (rejected), and resume the loop.

The provider API needs no special support for this, because a rejection is just a `tool_result` (handle-tool-calls URL above). This is exactly the case where Anthropic tells you to drop the Tool Runner (tool-runner URL above). About 50-100 LOC plus a table.

## 4. Two caps (inference)

Trivial to write: increment `step_count` per model call and `tool_call_count` per executed tool block, check both before each model call and each tool run, and persist both counters on the session so they survive a resume. One subtlety: a single parallel turn can hold N tool calls, so check the tool-call cap per block, not per turn. On cap you stop and either return a final message or inject an `is_error` result (a design choice). The Tool Runner's `max_iterations` covers only the step cap (tool-runner URL above).

## 5. Model portability: LiteLLM

- **Version and license:** `litellm` 1.104.1. The license is MIT except the `enterprise/` directory, which has its own license. (https://pypi.org/pypi/litellm/json, https://github.com/BerriAI/litellm/blob/main/LICENSE)
- **SDK vs proxy:** the SDK is an in-process library ("no separate service"). The proxy/AI Gateway is a self-hosted, OpenAI-compatible container with virtual keys, budgets, spend tracking and an admin UI. SSO, audit logs and guardrails are listed as enterprise features. (https://docs.litellm.ai/docs/)
- **Tools:** `completion(tools=...)` uses the OpenAI format. `supports_function_calling()` and `supports_parallel_function_calling()` check a model's capabilities. `add_function_to_prompt` is a prompt-injection fallback for models without native tool calling (reliability unverified). Arguments may come back as invalid JSON, so handle parse errors. (https://docs.litellm.ai/docs/completion/function_call)
- **Cross-provider pitfalls:** Gemini 3.5+ requires `functionResponse.id` to match the call id exactly, and the ids embed `__thought__<signature>`, which you must pass back unchanged. This needs litellm >= 1.87.0.dev1. (https://docs.litellm.ai/blog/gemini_3_5_flash) Downstream reports describe Anthropic rejecting tool-id formats and dropping thinking blocks when calls go through LiteLLM in the OpenAI Agents SDK (https://github.com/openai/openai-agents-python/issues/1147, https://github.com/openai/openai-agents-python/issues/1797). Details and current status are unverified.
- **Supply-chain risk:** litellm 1.82.7 and 1.82.8 on PyPI were malicious (credential stealer; 1.82.8 ran from a `.pth` file at interpreter startup). They were published 2026-03-24 from a hijacked maintainer account and later quarantined. The Docker proxy image was not affected. (https://www.netspi.com/blog/executive-blog/ai-ml-pentesting/litellm-supply-chain-compromise/, https://www.comet.com/site/blog/litellm-supply-chain-attack/) Pin exact versions and hashes.

## 6. MCP client and A2A via the official SDKs

- **MCP:** `mcp` 2.3.0, MIT, "Production/Stable", Python >= 3.10 (https://pypi.org/pypi/mcp/json). v2 "is the stable line". There is one `Client` object (URL, stdio subprocess, custom transport, or an in-memory server for tests), with `ClientSession` still underneath. It targets the 2026-07-28 spec and still serves 2025-11-25. (https://py.sdk.modelcontextprotocol.io/whats-new/) v2 renamed or removed v1 APIs (`FastMCP` -> `MCPServer`, `streamablehttp_client` -> `streamable_http_client`). Those renames come from search snippets and are unverified. Wiring MCP into an own loop means: list tools, map them to provider tool schemas, and route matching `tool_use` blocks to `client.call_tool` (inference).
- **A2A:** `a2a-sdk` 1.2.2, Apache-2.0, no Development Status classifier. It implements A2A spec 1.0 with a 0.3 compatibility mode, over JSON-RPC, REST and gRPC on both client and server. Extras include `http-server`, `fastapi`, `grpc`, `telemetry`, and `postgresql`/`sqlite` task stores (https://pypi.org/pypi/a2a-sdk/json). The repo has about 2.2k stars. The 0.3 compatibility scope is still tracked in an open issue (#742). There is no explicit production-readiness statement. (https://github.com/a2aproject/a2a-python) Both SDKs are framework-independent, so going without a framework costs nothing here (inference).

## 7. Observability

- **Semconv status:** GenAI conventions moved to `open-telemetry/semantic-conventions-genai`, and the opentelemetry.io page is "no longer maintained" (https://opentelemetry.io/docs/specs/semconv/gen-ai/). The new repo has no tagged release (https://github.com/open-telemetry/semantic-conventions-genai). The agent-spans doc (`create_agent`, `invoke_agent`, `execute_tool`) shows **Status: Development** (https://raw.githubusercontent.com/open-telemetry/semantic-conventions-genai/main/docs/gen-ai/gen-ai-agent-spans.md). A secondary source says nothing in the `gen_ai.*` namespace is Stable as of July 2026 (https://dev.to/azena-ai/opentelemetrys-genai-semantic-conventions-are-not-stable-yet-heres-what-actually-shipped-in-2026-3mke).
- **Instrumentation for raw SDK calls:**
  - **OTel official:** these now live in `opentelemetry-python-genai`. `opentelemetry-instrumentation-genai-anthropic` and `-genai-openai` are both at 1.2b0 and Beta (https://github.com/open-telemetry/opentelemetry-python-genai, https://pypi.org/pypi/opentelemetry-instrumentation-genai-anthropic/json). The older `opentelemetry-instrumentation-openai-v2` (2.4b0, Beta) defaults to semconv v1.30.0 unless `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` is set. Its description mentions chat completions and embeddings; Responses API coverage is unverified. (https://pypi.org/pypi/opentelemetry-instrumentation-openai-v2/json)
  - **OpenLLMetry (Traceloop, Apache-2.0):** `opentelemetry-instrumentation-anthropic` 0.62.4, plus OpenAI, LiteLLM and MCP instrumentations (https://pypi.org/pypi/opentelemetry-instrumentation-anthropic/json, https://github.com/traceloop/openllmetry).
  - **OpenInference (Arize, Apache-2.0):** OpenAI, Anthropic, LiteLLM and MCP instrumentors. It is OTel-based, but whether it emits `gen_ai.*` or its own attributes is unverified on the README (https://github.com/Arize-ai/openinference).
  - **LiteLLM itself:** `litellm.callbacks=["otel"]` emits `gen_ai.*`, with an opt-in latest-experimental mode (https://docs.litellm.ai/docs/observability/opentelemetry_integration).
- **The gap (inference):** these libraries emit the `chat` spans. The `invoke_agent` and `execute_tool` spans that wrap your loop are yours to create by hand, which is about 20 lines with the OTel API.

## 8. Testing (inference)

The model double is a fake client that returns scripted responses (`tool_use` blocks, then `end_turn`), injected through the same interface as the real provider or LiteLLM adapter. The trajectory is your own persisted tool-call log (name, args, tier, approved/denied), and the EXACT, IN_ORDER and ANY_ORDER matchers become plain list comparisons in pytest. For pass^k, run the live model k times through the same harness. No framework adapter is needed, because the loop's own log is the ground truth.

## 9. What Anthropic says about frameworks

"We suggest that developers start by using LLM APIs directly." Frameworks "create extra layers of abstraction that can obscure the underlying prompts" and can "make it tempting to add complexity when a simpler setup would suffice". If you use one, "ensure you understand the underlying code". Agents are "typically just LLMs using tools based on environmental feedback in a loop", and they commonly include "stopping conditions (such as a maximum number of iterations)". (https://www.anthropic.com/engineering/building-effective-agents)

## 10. When to pick it and when not (inference)

**Pick it when:**
- the agent is a single loop with a handful of tools;
- the pipeline already defines the seams (repository, HITL, caps, OTel, evals);
- you want auditable control flow, and a security review must read every line that can trigger a destructive tool.

**Avoid it when:**
- you need complex multi-agent graphs, branching or checkpoint-replay;
- the team lacks the discipline to maintain history-format, retry, streaming and cross-provider conversion code;
- time-to-first-demo dominates.

**Costs you pay:**
- the most code (roughly 500-1,500 LOC for loop, repo, HITL, caps, OTel spans and MCP bridge);
- you own every provider edge case: parallel tool results, `pause_turn` and `max_tokens` stops, thinking blocks, id formats;
- no ecosystem of ready-made memory or orchestration components.

**What you gain:**
- the least abstraction;
- zero framework churn;
- each seam is a plain interface you can swap.

## 11. Verdict (inference)

The fit with the pipeline seams is strong. Every fixed seam (repository-backed sessions, LiteLLM-style provider config, OTel GenAI telemetry, tiered HITL, two independent caps, a trajectory log for EXACT, IN_ORDER and ANY_ORDER, a per-user serial worker, MCP and A2A) is something you would build anyway, and here nothing fights you. MCP 2.x and a2a-sdk 1.x are standalone, so interop costs no more than in a framework. The real costs are concentrated in three places:

1. **Cross-provider history conversion.** LiteLLM covers it with known tool-id and thinking-block sharp edges. Pin and hash-lock it after the March 2026 compromise.
2. **Hand-made agent and tool spans** on top of semconv that is still Development and beta-grade instrumentors.
3. **Not using the Tool Runner** once HITL is required (Anthropic says so itself).

Recommend it as the **default baseline card**: the simplest option that satisfies all seams. Choose a framework only when a concrete need (graph orchestration, durable replay) names what it buys.
