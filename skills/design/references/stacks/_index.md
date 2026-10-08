# Stack catalog index

Read by design Phase E, step 1 (hard filters). One row per ACTIVE card; draft
cards never appear here. Values are copied from each card's frontmatter and
§2 — `scripts/check_catalog.py` fails on any mismatch.

Filter mapping used by design Phase E:
- "must switch model provider" → eliminate rows whose model_portability is `vendor-only (...)`.
- "talks to other agents, no paid license" → eliminate `licensed-server` and `none` in a2a.
- "talks to other agents, license acceptable" → eliminate `none` in a2a.
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
