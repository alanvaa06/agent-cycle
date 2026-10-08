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
- **Seams (decided now, paid never) — stack-neutral; concrete binding: see §8:**
  - Sessions: a durable store behind the repository interface — never a managed store without an export path
  - Model: a provider route string — provider is a deployment decision
  - Telemetry: OTel GenAI conventions — backend is an exporter setting
- Source: vault article "Multi-Cloud Agent Deployment Patterns"

## 6. NO-goals

<What this agent will NOT do. Non-empty, always. Scope-creep defense.>

## 7. Open questions → /spec

<Non-empty. Anything unresolved. /spec interviews ONLY on these.>

## 8. Stack decision

<!-- Appended last on purpose: /spec cites §4 and §7 by number. -->

**Filter answers:** Q1 provider switch: <answer> · Q2 A2A (and license, if asked): <answer> · Q3 client infrastructure: <answer> · Q4 data egress: <answer>. Mark any assumed answer ("I don't know" → stricter answer) as `assumption` and add a §7 item to confirm it.

- **Chosen:** `<card-id>@<version>` — or `off-catalog:<name>@<version>`. Version rule: the re-checked version when the card was re-verified, else the card's `version_verified`; `no-framework@n/a` (pins per binding).
- **Recommended:** <card-id> — <reason>
- **Why:** <one paragraph tying the pick to this design's facts; if the user picked otherwise or delegated ("go with your recommendation"), say so and give their reason>

| Candidate | Pros (cited) | Cons (cited) |
|---|---|---|
| <card-id> | <card fact + URL / design fact> | <card fact + URL, incl. binding-level costs: custom seams, own a2a server, vendor-only model, egress switch-off> |

| Set aside (judgment) | Reason (card §5 + URL, or design fact) |
|---|---|
| <card-id> | <...> |

| Eliminated | Filter that eliminated it |
|---|---|
| <card-id> | <e.g. model portability required; card is vendor-only (anthropic)> |

**Relaxed filters:** <none, or which and why>

**Mandatory spec security rows:** <e.g. switch off the chosen card's default egress; the card's [security] and [data] traps>

**Concrete per-seam binding** (from the chosen card's §3):

| Seam | Support | How |
|---|---|---|
| sessions / model_provider / telemetry (and the other seams the design needs) | <...> | <...> |

**Verification log:**

| Card | Card verified_on / version_verified | Fact re-verified | Source | Date |
|---|---|---|---|---|
| <card-id> | <YYYY-MM-DD / version> | <fact> | <url> | <YYYY-MM-DD> |

**Catalog drift:**

| Card | Card says | Docs now say | Source | Date |
|---|---|---|---|---|
| <card-id> | <...> | <...> | <url> | <YYYY-MM-DD> |

**Suspicious content seen:** <none, or page URL + short excerpt>
