---
id: no-framework
name: No framework (own loop)
level: none
nests_on: none
package: none
version_verified: n/a
license: n/a
ts_sdk: full
verified_on: 2026-10-07
status: active
---

# No framework (own loop)

## 1. What it is
The build writes the model-tool loop itself on a provider API: call the model with `tools`, run each `tool_use` block, send the results back in one user message, repeat until no call remains. Anthropic's advice is to "start by using LLM APIs directly" and to understand the code under any framework you adopt: https://www.anthropic.com/engineering/building-effective-agents . The loop, history store, approval gate and caps are the build's code (roughly 500-1,500 lines, inference, research file docs/superpowers/research/2026-10-07-stack-catalog/no-framework.md); the Anthropic SDK ships a beta Tool Runner that is unsuitable here once approval is required: https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-runner . There is no package to version: SDK pins (anthropic, openai, litellm, mcp, a2a-sdk) are in the binding. TypeScript SDKs exist for the provider APIs, so ts_sdk is full (inference).

## 2. Filter attributes
| Attribute | Value | Source |
|---|---|---|
| model_portability | any | https://docs.litellm.ai/docs/ |
| a2a | client+server | https://pypi.org/pypi/a2a-sdk/json |
| mcp_client | native | https://py.sdk.modelcontextprotocol.io/whats-new/ |
| deploy_constraints | none | https://docs.litellm.ai/docs/ |
| default_egress | none | https://pypi.org/pypi/opentelemetry-instrumentation-genai-anthropic/json |
| stability | own-code | https://www.anthropic.com/engineering/building-effective-agents |

Notes on the filter values (each with its own source):
- model_portability: LiteLLM (SDK in-process, or the self-hosted proxy) routes `completion(tools=...)` across providers in the OpenAI format; when the spec pins one provider the build calls that provider's SDK directly. Sources: https://docs.litellm.ai/docs/ and https://docs.litellm.ai/docs/completion/function_call
- a2a: `a2a-sdk` 1.2.2 (Apache-2.0) implements A2A spec 1.0 with a 0.3 compatibility mode for both client and server, independent of any agent framework; no production-readiness statement was found (unverified). Sources: https://pypi.org/pypi/a2a-sdk/json and https://github.com/a2aproject/a2a-python
- mcp_client: `native` here means the first-party `mcp` 2.3.0 `Client` (URL, stdio or in-memory) used directly; the build itself lists the tools and maps them into the provider tool schemas (inference). Source: https://py.sdk.modelcontextprotocol.io/whats-new/
- deploy_constraints: the loop and the SDKs are in-process Python libraries with no managed runtime (inference); the LiteLLM SDK needs no separate service. Source: https://docs.litellm.ai/docs/
- default_egress: value `none` (the loop sends no telemetry); the qualifier is LiteLLM's price-map fetch from github.com at import unless `LITELLM_LOCAL_MODEL_COST_MAP=true`. The OTel genai instrumentors capture no prompt or completion content unless an environment variable is set (https://pypi.org/pypi/opentelemetry-instrumentation-genai-anthropic/json). Two nuances, both handled in the binding: LiteLLM's OTel callback logs message content by default (https://docs.litellm.ai/docs/observability/opentelemetry_integration), and importing LiteLLM fetches its model price map from github.com unless `LITELLM_LOCAL_MODEL_COST_MAP=true` (a GET that sends no user data, inference: https://raw.githubusercontent.com/BerriAI/litellm/v1.104.1/litellm/litellm_core_utils/get_model_cost_map.py).
- stability: own code, so no framework releases to track; the dependencies are the churn (see traps).

## 3. Seam mapping
| Seam | Support | How | Source |
|---|---|---|---|
| sessions | custom | Own message-history table (session_id, seq, role, content JSON, tool_call_id, created_at) behind the repository interface; the API takes the full message list on every call, so storage and the canonical (provider-neutral) message format are yours | https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls |
| hitl_gate | custom | Own loop pauses before gated calls and persists the pending batch; the SDK tool runner is unsuitable when HITL is required, per its docs ("use the manual loop" for human-in-the-loop approval) | https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-runner |
| step_cap | custom | Counter, small (inference); `max_iterations` is the runner's documented step limit and the runner is not used | https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-runner |
| tool_call_cap | custom | Counter over the requested calls of each response (a response can hold several, run in any order you choose, one result each) | https://platform.claude.com/docs/en/agents-and-tools/tool-use/parallel-tool-use |
| model_provider | adapter | LiteLLM SDK or proxy (1.104.1, MIT outside enterprise/); the provider SDK directly when the spec pins one provider | https://pypi.org/pypi/litellm/json and https://github.com/BerriAI/litellm/blob/main/LICENSE |
| telemetry | adapter | opentelemetry-instrumentation-genai-anthropic and -genai-openai 1.2b0 (Beta), model-call spans only; GenAI semconv status "Development" | https://pypi.org/pypi/opentelemetry-instrumentation-genai-anthropic/json and https://raw.githubusercontent.com/open-telemetry/semantic-conventions-genai/main/docs/gen-ai/gen-ai-agent-spans.md |
| eval_runner | custom | Own requested-call log is the trajectory; the model double is a scripted fake with the adapter's call signature (inference) | https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls |
| deploy | native | Plain Python in any container; no runtime to host (inference) | https://pypi.org/pypi/anthropic/json |

## 4. Known traps
- [security] LiteLLM 1.82.7 and 1.82.8 on PyPI were malicious (published 2026-03-24 from a hijacked maintainer account; 1.82.8 ran from a `.pth` file at interpreter startup): pin exact versions with hashes. Source: https://www.netspi.com/blog/executive-blog/ai-ml-pentesting/litellm-supply-chain-compromise/ and https://www.comet.com/site/blog/litellm-supply-chain-attack/
- [ops] Tool-call ids differ across providers: Gemini 3.5+ requires `functionResponse.id` to match the call id exactly and the id embeds a thought signature (`__thought__<signature>`) that must be passed back unchanged; this needs litellm >= 1.87.0.dev1. Anthropic rejects history where `tool_result` blocks do not come first in the user message. Source: https://docs.litellm.ai/blog/gemini_3_5_flash and https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls
- [ops] Agent and tool spans are hand-written: the genai instrumentors cover model calls only, so `invoke_agent` and `execute_tool` are the build's code. Source: https://pypi.org/pypi/opentelemetry-instrumentation-genai-anthropic/json and https://raw.githubusercontent.com/open-telemetry/semantic-conventions-genai/main/docs/gen-ai/gen-ai-agent-spans.md
- [churn] OTel GenAI conventions are Development status (the page lives in a repo with no tagged release), so span and attribute names can change. Source: https://raw.githubusercontent.com/open-telemetry/semantic-conventions-genai/main/docs/gen-ai/gen-ai-agent-spans.md and https://github.com/open-telemetry/semantic-conventions-genai
- [ops] litellm 1.104.1 requires `openai>=2.20.0,<3.0.0` (observed with `uv pip compile` on 2026-10-08), so an image that installs LiteLLM cannot also carry openai 3.x; use the openai version the lock resolves, or keep LiteLLM out of a direct-OpenAI image. Source: https://pypi.org/pypi/litellm/json and https://pypi.org/pypi/openai/json
- [data] LiteLLM's OTel callback logs message content by default (`turn_off_message_logging` defaults to logging) and the SDK fetches its price map from github.com on import; both need explicit settings (the price-map fetch is a GET that sends no user data, inference). Source: https://docs.litellm.ai/docs/observability/opentelemetry_integration and https://raw.githubusercontent.com/BerriAI/litellm/v1.104.1/litellm/litellm_core_utils/get_model_cost_map.py
- [ops] LiteLLM tool arguments may come back as invalid JSON; the loop must handle parse errors without running the tool. Source: https://docs.litellm.ai/docs/completion/function_call

## 5. Pick when / avoid when
Pick as the baseline for simple or linear tool loops: Anthropic recommends starting with the LLM APIs directly and warns that frameworks "create extra layers of abstraction" (https://www.anthropic.com/engineering/building-effective-agents). Pick when the pipeline already defines the seams (repository, gate, caps, OTel, evals), so nothing fights them, and when a security review must read every line that can trigger a destructive tool (inference, research file). MCP 2.x and a2a-sdk 1.x are standalone, so interop costs no more than in a framework (https://py.sdk.modelcontextprotocol.io/whats-new/ , https://pypi.org/pypi/a2a-sdk/json).
Avoid when the team should not own cross-provider message conversion and every provider edge case (parallel tool results, `pause_turn` and `max_tokens` stops, thinking blocks, id formats: https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls and https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons ). Avoid when the agent needs complex multi-agent graphs, branching or checkpoint replay (inference), or when time-to-first-demo dominates.

## 6. Build binding
`skills/build/references/bindings/no-framework.md`
