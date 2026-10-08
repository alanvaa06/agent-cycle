# Stack catalog index

Read by design Phase E, step 1 (hard filters). One row per ACTIVE card; draft
cards never appear here. Values are copied from each card's frontmatter and
§2 — `scripts/check_catalog.py` fails on any mismatch.

Filter mapping used by design Phase E:
- "must switch model provider" → eliminate rows whose model_portability is `vendor-only (...)`.
- "talks to other agents" → no a2a elimination. `licensed-server`, `none` and `server-only` all mean the build adds its own a2a-sdk server in front of the ingress queue: cite it as a con of the candidate (for `licensed-server` add "the licensed Agent Server path is not used").
- "telemetry may not leave to third parties" → every candidate whose default_egress is not `none` carries a mandatory spec security row to switch it off (not an elimination unless it cannot be switched off).
- Python only (all cards are Python).

## Filter table
| id | level | nests_on | model_portability | a2a | mcp_client | stability | default_egress | verified_on |
|---|---|---|---|---|---|---|---|---|
| langgraph | runtime | none | any | licensed-server | beta | semver-stable | none (LangSmith tracing only when enabled) | 2026-10-07 |
| langchain-create-agent | framework | langgraph | any | licensed-server | beta | semver-stable | none (LangSmith tracing only when enabled) | 2026-10-07 |
| deep-agents | harness | langchain-create-agent | any | licensed-server | beta | pre-1.0 | none (LangSmith tracing only when enabled) | 2026-10-07 |
| pydantic-ai | framework | none | any | server-only | native | semver-stable | none (Logfire optional) | 2026-10-07 |
| google-adk | framework | none | any | client+server | native | fast-moving | none | 2026-10-07 |
| openai-agents-sdk | framework | none | any | none | native | pre-1.0 | tracing to OpenAI ON by default, inputs and outputs included | 2026-10-07 |
| crewai | framework | none | any | client+server | native | fast-moving | anonymous telemetry ON by default; built-in tracing uploads to the CrewAI platform when enabled | 2026-10-07 |
| claude-agent-sdk | harness | none | vendor-only (anthropic) | none | native | alpha | Anthropic usage metrics ON by default on the Claude API; CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 switches off; OTel export opt-in | 2026-10-07 |
| no-framework | none | none | any | client+server | native | own-code | none | 2026-10-07 |
