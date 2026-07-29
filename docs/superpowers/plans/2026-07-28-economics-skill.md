# agent-cycle `/economics` Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first transversal skill — `agent-cycle:economics` — which produces a monthly cost analysis of running an agent (`docs/agent/<agent_name>-economics.md`): dated unit prices, per-scenario cost model, sensitivity, break-even, cost controls with a token-spend alarm threshold for `/ship`, and a post-build calibration plan. Then release v0.4.0.

**Architecture:** Same shape: EDD cases first, two references, SKILL.md. Transversal per plugin design §5.1: invokable at two moments — post-spec (band estimate, viability-gate role) and post-build (recalibration from real telemetry, `basis: calibrated`). Minimum gate: an approved design.md (nothing to cost without one); an approved spec.md sharpens turn/tool assumptions. Core discipline: every unit price carries a source and a date (compiled workspace sources first — e.g. the user's vault — else current web/provider docs); tokens-first modeling (they dominate 70–90%); bands, never cent-precision; explicit auditable formulas. CFA-grade = explicit assumptions + dated sources + sensitivity + honest uncertainty.

**Tech Stack:** Claude Code plugin format, Markdown/JSON only. Repo `C:\Proyectos\agent-cycle\` (branch `feature/economics-skill` off `main`).

**Spec:** `docs/superpowers/specs/2026-07-28-agent-cycle-plugin-design.md` § 5.1.

---

### Task 1: EDD eval cases — before the skill exists

**Files:**
- Create: `skills/economics/evals/cases.json`
- Create: `skills/economics/evals/README.md`
- Create: `skills/economics/evals/results.md`

- [ ] **Step 1: Write the eval cases**

Write `skills/economics/evals/cases.json`:

```json
{
  "skill": "agent-cycle:economics",
  "spec_ref": "docs/superpowers/specs/2026-07-28-agent-cycle-plugin-design.md#51-agent-cycleeconomics",
  "cases": [
    {
      "id": "ECO-E01",
      "type": "positive",
      "input": "What will it cost to run this agent monthly? (Run in a repo with approved design.md + spec.md, e.g. the real whatsapp-owner-assistant.)",
      "expected": {
        "fires": true,
        "checks": [
          "Gate: requires an approved design.md; consumes spec.md when present and does NOT re-ask anything design/spec already answer (model choice, deployment target, tool set, telemetry fields)",
          "Volume scenarios (low/medium/high) defined with explicit, auditable assumptions — conversations/month, turns/conversation, tool calls and tokens in/out per turn — each with a stated basis, and the arithmetic shown as formulas",
          "EVERY unit price row carries a source and an as-of date; compiled workspace sources (e.g. a vault article) are used and cited first when present; a price with no source does not appear",
          "Monthly cost model: scenario x component table (model tokens, infra for the design's target, channel fees, third-party tools) with totals expressed as bands — no cent-precision totals",
          "The design's deployment target is the base case; other targets appear only if the design names them or the user asks",
          "Sensitivity section covers at least: model-tier swap and volume swing; prompt-caching effect when the provider supports it",
          "Break-even section present: against a client price when the agent is client-facing, or against internal value (the design's own Performance metric, e.g. owner hours saved) when internal",
          "Cost controls are actionable and include an explicit token-spend alarm threshold derived from the estimate (stated as the input /ship will calibrate against)",
          "Calibration plan: names which spec telemetry fields (e.g. tool_call_count, token counters) recalibrate which assumption post-build",
          "Artifact at docs/agent/<agent_name>-economics.md with frontmatter agent_name, version, status: draft, date, basis: estimate, prices_as_of (+ spec_version when a spec exists); skill stops at the human gate"
        ]
      }
    },
    {
      "id": "ECO-E02",
      "type": "gate-negative",
      "input": "What will this agent cost to run? (Run twice: once in a repo where docs/agent/design.md has status: draft, once with no docs/agent/ at all.)",
      "expected": {
        "fires": true,
        "checks": [
          "Refuses in both branches: names the missing gate (design draft, or design absent → run agent-cycle:design first) and stops",
          "Writes NO files in either branch — verified on the filesystem afterward"
        ]
      }
    },
    {
      "id": "ECO-E03",
      "type": "edge-calibration",
      "input": "Recalibrate the economics with real usage data. (Run in a repo that has an existing <agent_name>-economics.md with basis: estimate AND real telemetry numbers available — e.g. a metrics export or the user pastes real tokens/turn and turns/day.)",
      "expected": {
        "fires": true,
        "checks": [
          "Produces basis: calibrated with version bumped — the estimate is preserved in a delta table (assumption -> estimated -> actual -> delta), never silently overwritten",
          "Assumptions that survived are marked confirmed; those off by a stated threshold are recomputed and the cost model re-derived",
          "The token-spend alarm threshold is recomputed from actuals and flagged if the original alarm would have been wrong"
        ]
      }
    },
    {
      "id": "ECO-E04",
      "type": "trigger-negative",
      "input": "How much does the Claude API cost per million tokens? What's the price difference between Sonnet and Haiku?",
      "expected": {
        "fires": false,
        "checks": [
          "agent-cycle:economics does NOT fire — generic API pricing questions are outside the pipeline",
          "No files are created or modified — verified on the filesystem afterward"
        ]
      }
    }
  ]
}
```

- [ ] **Step 2: Write the run procedure**

Write `skills/economics/evals/README.md`:

```markdown
# Eval procedure for agent-cycle:economics

Same agentic procedure as `skills/design/evals/README.md` (fresh session,
scratch project, per-check PASS/FAIL rows in `results.md`, fix-and-rerun,
dispute — never silently edit — if a case is wrong).

Case-specific setup:

- **ECO-E01** needs approved design.md + spec.md; the real dogfood repo is the
  canonical run. If the workspace has compiled pricing sources (e.g. vault
  articles on cloud/agent deployment costs), the run should cite them — scoring
  covers that they were found and used.
- **ECO-E02** runs twice: design at draft, and no docs/agent/ at all.
- **ECO-E03** needs an existing economics artifact with basis: estimate plus
  real numbers (paste plausible actuals in the session if no metrics export
  exists — the check is about delta handling, not the numbers' origin).
- **ECO-E04**: filesystem check afterward.

Scoring anchors: the every-price-dated check is scored by scanning the unit
price table — any row without BOTH a source and an as-of date is a FAIL. The
no-cent-precision check applies to TOTALS and scenario bands (unit prices may
carry exact list values). Formula-audit check: a reader must be able to
recompute any total from the stated assumptions without guessing.
```

- [ ] **Step 3: Create the results log**

Write `skills/economics/evals/results.md`:

```markdown
# Eval runs — agent-cycle:economics

One row per check, per run. Verdict: PASS / FAIL. Evidence: one line.

| Date | Case | Check # | Verdict | Evidence |
|---|---|---|---|---|
```

- [ ] **Step 4: Verify JSON**

Run: `python -c "import json; d=json.load(open(r'skills/economics/evals/cases.json')); print(len(d['cases']), 'cases,', len(d['cases'][0]['expected']['checks']), 'checks in E01')"`
Expected: `4 cases, 10 checks in E01`

- [ ] **Step 5: Commit**

```bash
git add skills/economics/evals/
git commit -m "feat(economics): EDD eval cases before SKILL.md (ECO-E01..E04)"
```

---

### Task 2: Artifact template

**Files:**
- Create: `skills/economics/references/economics-template.md`

- [ ] **Step 1: Write the template**

Write `skills/economics/references/economics-template.md`:

```markdown
# <agent_name>-economics.md template

Written to `docs/agent/<agent_name>-economics.md` in the TARGET AGENT'S repo.
Bands over precision: totals are ranges, unit prices may be exact list values.

---
agent_name: <same-as-design>
version: 1
status: draft            # draft | approved — human gate only
date: <YYYY-MM-DD>
basis: estimate          # estimate | calibrated
prices_as_of: <YYYY-MM-DD>
spec_version: <version, when a spec exists>
---

# <Agent Name> — Economics

## 1. Assumptions

| Scenario | Conversations/mo | Turns/conv | Tool calls/turn | Tokens in/turn | Tokens out/turn | Basis |
|---|---|---|---|---|---|---|
| Low | ... | ... | ... | ... | ... | <where each number comes from: spec scenario, comparable, guess-flagged> |
| Medium | ... | | | | | |
| High | ... | | | | | |

- Model: <from design/spec — e.g. Sonnet-class via LiteLLM>; alternatives priced in §4.
- Formulas (auditable):
  `tokens_in/mo = convs x turns x tokens_in/turn` · `model_cost = tokens_in/mo x price_in + tokens_out/mo x price_out` · state every derived number's formula once.

## 2. Unit prices (every row dated + sourced)

| Item | Price | Source | As of |
|---|---|---|---|
| <model> input / output per Mtok | ... | <vault article / provider page> | <date> |
| <infra: VPS node / serverless unit> | ... | ... | <date> |
| <channel fees, e.g. WhatsApp conversation> | ... | ... | <date> |
| <third-party tools> | ... | ... | <date> |

Prices are dated inputs, not truths — stale rows invalidate totals, not the method.

## 3. Monthly cost model (base case: <design's deployment target>)

| Component | Low | Medium | High |
|---|---|---|---|
| Model tokens (dominant) | $A–B | ... | ... |
| Infra (<target>) | ... | ... | ... |
| Channel fees | ... | ... | ... |
| Third-party | ... | ... | ... |
| **Total (band)** | **$X–Y** | ... | ... |

Tokens are modeled FIRST — they are 70–90% of any agent bill; infra follows.

## 4. Sensitivity

- Model tier swap: <e.g. Haiku-class vs Sonnet-class — factor and new bands>.
- Volume swing: ±50% on Medium.
- Prompt caching / history truncation effect where the provider supports it.

## 5. Break-even

- Client-facing: monthly price to client → margin per scenario, floor price.
- Internal: cost vs the design's own Performance metric monetized
  (e.g. owner hours saved x hourly value) → cost per hour saved.

## 6. Cost controls

Actionable levers (model routing, caching, history truncation, max-token caps)
plus: **token-spend alarm threshold = <Medium estimate x 1.5, stated
explicitly>** — this number is the input `/ship` calibrates the billing alarm
against.

## 7. Calibration plan (post-build)

| Assumption | Telemetry field that measures it (from the spec) | Recalibrate when |
|---|---|---|
| tokens/turn | <e.g. token counters per span> | after N real turns |
| turns/conv | <e.g. session turn count> | ... |
| tool calls/turn | tool_call_count | ... |

On calibration: bump version, set basis: calibrated, keep a delta table
(assumption → estimated → actual → delta) — estimates are preserved, never
silently overwritten.
```

- [ ] **Step 2: Commit**

```bash
git add skills/economics/references/economics-template.md
git commit -m "feat(economics): artifact template (dated prices, bands, calibration plan)"
```

---

### Task 3: Costing guide

**Files:**
- Create: `skills/economics/references/costing-guide.md`

- [ ] **Step 1: Write the guide**

Write `skills/economics/references/costing-guide.md`:

```markdown
# Costing guide — agent-cycle:economics

## Step 0 — Gate check

Read `docs/agent/design.md`. Hard-fail (write nothing) if missing ("run
agent-cycle:design first") or not approved. Read `docs/agent/spec.md` when
present and approved — it sharpens turns/tools/telemetry assumptions; record
spec_version. Never re-ask what design/spec answer (model, target, tools,
telemetry fields). Determine mode: no prior economics artifact → basis:
estimate; existing artifact + real usage numbers offered → calibration mode
(step 7).

## Step 1 — Volume scenarios

Three scenarios (low/medium/high). Sources in priority order: the spec's own
fixtures/expectations, the user's stated expectations (one question if truly
absent), comparables. Every number gets a Basis cell; a guess is written
"guess" — hiding uncertainty is the cardinal sin here.

## Step 2 — Unit prices, dated

Priority order: (1) compiled sources already in the workspace — a knowledge
vault, pricing docs the user maintains — cite article + date; (2) provider
pricing pages via web, cite URL + retrieval date; (3) nothing found → the row
enters as UNKNOWN with a note, and totals become conditional. NEVER quote a
price from model memory without a dated source. Tokens first: model input/
output per Mtok for the design's chosen model AND one cheaper + one stronger
alternative (feeds §4). Then infra for the design's target only, channel fees,
third-party tools the spec names.

## Step 3 — Cost model

Tokens/mo per scenario from the §1 formulas; model cost; then infra, channel,
third-party. Totals as BANDS (round to honest figures — $80–150, never
$83.47). Base case = the design's deployment target. Other targets only if the
design names alternatives or the user asks — this is an agent costing, not a
cloud comparison shootout.

## Step 4 — Sensitivity

Mandatory: model-tier swap (recompute §3's dominant line with the two
alternatives priced in step 2) and volume swing (±50% on Medium). Add prompt
caching / history truncation effect when the provider supports it — cite the
mechanism, don't invent discount factors.

## Step 5 — Break-even

Client-facing agent: margin table vs the client's monthly price (ask for the
price if unknown — one question) and the floor price. Internal agent: monetize
the design's own Performance metric (e.g. hours of owner lookup time saved x
the owner's hourly value — ask for the hourly value if needed, one question)
→ cost per unit of value; state the utilization at which the agent pays for
itself.

## Step 6 — Controls + alarm

Levers that actually move THIS agent's bill (routing, caching, truncation,
caps — tied to its model and loop limits, not generic advice). Then the alarm:
token-spend threshold = Medium-scenario estimate x 1.5, stated as an explicit
number with its formula. Flag it as /ship's calibration input.

## Step 7 — Calibration mode (basis: calibrated)

Requires an existing economics artifact + real numbers (telemetry export or
user-pasted actuals). Build the delta table (assumption → estimated → actual →
delta). Confirmed assumptions marked; assumptions off by >25% recomputed and
§3 re-derived. Recompute the alarm from actuals; flag if the original would
have misfired. Bump version, set basis: calibrated, preserve the estimate
columns — never silently overwrite.

## Step 8 — Gate

Present: scenario table, total bands, dominant cost line, break-even headline,
alarm threshold. Explicit approval → status: approved. Hand off: "/ship reads
the alarm threshold; /blueprint embeds this artifact."
```

- [ ] **Step 2: Commit**

```bash
git add skills/economics/references/costing-guide.md
git commit -m "feat(economics): costing guide (dated sources, tokens-first, calibration mode)"
```

---

### Task 4: SKILL.md

**Files:**
- Create: `skills/economics/SKILL.md`

- [ ] **Step 1: Write the skill**

Write `skills/economics/SKILL.md`:

```markdown
---
name: economics
description: "Transversal skill of the agent-cycle pipeline: monthly cost analysis of running a designed agent — dated unit prices, scenario cost model (tokens-first), sensitivity, break-even, token-spend alarm threshold for /ship, post-build calibration. Produces docs/agent/<agent_name>-economics.md. Use when the user asks what an agent will cost to run, to quote/price an agent for a client, for the agent's economics, or to recalibrate costs with real usage — 'cuánto costará correr este agente', 'economics del agente', 'cotiza el agente'. Requires an approved design.md. Do NOT use for generic API pricing questions, provider price comparisons outside an agent project, or billing questions about existing accounts."
---

# agent-cycle:economics — Agent Cost Analysis

What this agent costs to run monthly, stated the way an analyst would: explicit
assumptions, dated sources, bands, sensitivity, break-even. Two modes:
estimate (post-design/spec) and calibrated (post-build, with real telemetry).

## Hard rules

1. GATE: approved design.md minimum — nothing to cost without one. Consume
   spec.md when present; never re-ask what design/spec answer.
2. EVERY unit price carries a source and an as-of date. Workspace-compiled
   sources first (vault/pricing docs), then provider pages with retrieval date.
   A price with no dated source does not enter the model. Never quote prices
   from model memory.
3. Tokens first — they are 70–90% of any agent bill. Model the dominant line
   before infra.
4. Formulas explicit and auditable: a reader recomputes any total from stated
   assumptions. Guesses are labeled "guess".
5. Totals are BANDS. Cent-precision in a monthly estimate is false precision.
6. Base case = the design's deployment target. Other targets only if the
   design names them or the user asks.
7. Sensitivity (tier swap + volume) and break-even (client price or the
   design's own Performance metric monetized) are mandatory sections.
8. The token-spend alarm threshold (Medium x 1.5, explicit number) is the
   contract with /ship. Calibration mode preserves estimates in a delta table —
   never silently overwritten; version bumps, basis: calibrated.
9. Write ONLY docs/agent/<agent_name>-economics.md. status: draft until the
   explicit human gate. Never self-approve.

## Workflow

1. Read `references/costing-guide.md`; run steps 0→8 (step 7 only in
   calibration mode).
2. Fill `references/economics-template.md`.
3. Present the gate summary: scenario table, total bands, dominant line,
   break-even headline, alarm threshold.
4. Explicit approval → status: approved. Feedback → edit, re-present.
5. Hand off: "/ship calibrates the billing alarm against §6; /blueprint embeds
   this artifact."

## Failure modes to avoid

- Costing without an approved design, or re-asking the model/target the design
  fixed (rules 1, 6).
- A price with no source or date, or quoted from memory (rule 2).
- Infra-first modeling that buries the token line (rule 3).
- $83.47-style totals (rule 5).
- Skipping break-even because the agent is internal — monetize the design's
  metric instead (rule 7).
- Overwriting estimates during calibration instead of building the delta table
  (rule 8).
```

- [ ] **Step 2: Verify frontmatter**

Run: `head -4 skills/economics/SKILL.md`
Expected: `---`, `name: economics`, description present.

- [ ] **Step 3: Commit**

```bash
git add skills/economics/SKILL.md
git commit -m "feat(economics): SKILL.md — dated prices, tokens-first, bands, break-even"
```

---

### Task 5: Release v0.4.0

- [ ] **Step 1:** plugin.json version → `0.4.0`.
- [ ] **Step 2:** README status line → `**Status:** v0.4.0 — \`design\` + \`spec\` + \`evals\` + \`economics\` skills. Built skill-by-skill,\neach dogfooded on a real agent before the next begins.`
- [ ] **Step 3:** CHANGELOG entry before `## [0.3.0]`:

```markdown
## [0.4.0] — 2026-07-28

### Added
- **`economics` skill** (transversal 1 of 2): monthly cost analysis for a
  designed agent. Dated unit prices (workspace sources first, never from model
  memory), tokens-first scenario model with auditable formulas and band totals,
  mandatory sensitivity (tier swap + volume) and break-even (client price or
  monetized internal metric), token-spend alarm threshold as the /ship
  contract, calibration mode with delta tables (estimates never silently
  overwritten). Artifact: docs/agent/<agent_name>-economics.md.
- EDD eval suite (`skills/economics/evals/`): ECO-E01 positive (10-check
  contract), ECO-E02 gate-negative (two branches), ECO-E03 calibration edge,
  ECO-E04 trigger-negative (generic API pricing must not fire).

### Pending graduation
- `economics` skill runs against the real agent — tag `economics-v0.1` when
  the dogfood passes.
```

- [ ] **Step 4:** Verify version prints `0.4.0`; commit `chore: release v0.4.0 (economics skill)`.

---

### Task 6 (Alan, interactive): eval runs + dogfood

- [ ] ECO-E02 ×2, ECO-E03, ECO-E04 in scratch → rows in results.md.
- [ ] ECO-E01 dogfood in `C:\Proyectos\Whatsapp_agent`: internal agent → break-even vs the design's lookup-time metric; VPS base case; vault articles as price sources → approve → tag `economics-v0.1`.
- [ ] Marketplace update + reinstall for v0.4.0.

---

## Self-review (done at planning time)

- **§5.1 coverage:** two invocation moments ✓ (basis estimate/calibrated, guide step 0 mode detection); dated unit prices with vault-first sourcing ✓ (rule 2, guide step 2); scenario × target table ✓ (template §3, base-case rule 6 honors "multi-target only when asked" — refines §5.1's matrix mention toward the design's target, consistent with the dogfood-doesn't-redefine-defaults rule since the design names one target); model sensitivity ✓; break-even vs client price ✓ + internal-metric variant (the real dogfood is internal — §5.1's client-price framing generalized, not dropped); /ship alarm hook ✓ (rule 8, template §6); artifact name `<agent_name>-economics.md` ✓ (Alan's naming decision).
- **Placeholder scan:** none — template placeholders are angle-bracket fills, intended.
- **Consistency:** frontmatter pattern matches prior skills + basis/prices_as_of extensions; gate semantics identical; ECO-E01 check count (10) matches cases.json; trigger-negative mirrors prior skills' pattern.
```
