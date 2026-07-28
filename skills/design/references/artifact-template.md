# design.md template

The skill fills this template and writes it to `docs/agent/design.md` in the
TARGET AGENT'S repo (not the plugin repo). Frontmatter is mandatory.

---
agent_name: <kebab-case-name>
version: 1
status: draft            # draft | approved — approved ONLY via explicit human gate
date: <YYYY-MM-DD>
---

# <Agent Name> — Design

## 1. PEAS

| Element | Definition |
|---|---|
| **Performance** | <metric of the ENVIRONMENT, measurable, with target. Never agent activity.> |
| **Environment** | <the operating world: who, where, what systems> |
| **Actuators** | <actions/tools the agent can take, names only> |
| **Sensors** | <inputs the agent can read> |

**Goodhart notes:** <how the Performance metric could be gamed if targeted, and
the balancing factor that prevents it. At least one substantive note, always.>

## 2. Environment classification

| Dimension | Value | Architectural implication |
|---|---|---|
| Observable | fully / partially | partially → agent needs memory / belief state |
| Deterministic | deterministic / stochastic | stochastic → contingency plans, never one fixed plan |
| Episodic | episodic / sequential | sequential → plan ahead; actions constrain future options |
| Static | static / dynamic | dynamic → time-bound decisions |
| Agents | single / multi-agent | multi-agent → model other agents |

## 3. Harness decision

- **Topology:** single-agent (default) | multi-agent (requires measurable justification)
- **Justification:** <why this topology; what specialization would have to buy to change it>
- **5-part completeness check:** Model <which/tier> · Tools <count, from §4> ·
  Memory <what persists> · Orchestration <loop type, step limits> · Deployment <see §5>

## 4. Preliminary tool inventory

| Tool | Purpose | Likely tier (safe/reversible/destructive) |
|---|---|---|
| <name> | <one line> | <tier guess — /spec finalizes> |

No schemas here — /spec owns contracts.

## 5. Deployment intent

- **Target:** AWS | GCP | VPS — <why, per the client's constraint>
- **Seams (decided now, paid never):**
  - Sessions: framework-native store (<e.g. DatabaseSessionService → Postgres/DynamoDB behind repository interface>) — never a managed store without an export path
  - Model: LiteLLM config string — provider is a deployment decision
  - Telemetry: OTel GenAI conventions — backend is an exporter setting
- Source: vault article "Multi-Cloud Agent Deployment Patterns"

## 6. NO-goals

<What this agent will NOT do. Non-empty, always. Scope-creep defense.>

## 7. Open questions → /spec

<Non-empty. Anything unresolved. /spec interviews ONLY on these.>
