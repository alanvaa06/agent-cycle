# agent-cycle `/spec` Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the second skill of the agent-cycle plugin — `agent-cycle:spec` — which turns an APPROVED `docs/agent/design.md` into an executable `docs/agent/spec.md` (Gherkin behavior scenarios with `BHV-NNN` ids, final tool contracts with action tiers, conversation flows, security policy, data schemas, traceability table), then release v0.2.0.

**Architecture:** Same shape as the `design` skill: EDD cases first, then two reference files, then SKILL.md. Process-only markdown. The skill consumes the design artifact (hard-fails on missing/draft/stale), interviews ONLY on the design's open questions, and never reopens approved decisions — changes to the design go through the re-entry ladder, not through spec edits. DoD = dogfood: the real `whatsapp-owner-assistant` spec, approved by Alan without manual rework.

**Tech Stack:** Claude Code plugin format, Markdown/JSON only. Repo `C:\Proyectos\agent-cycle\` (branch `feature/spec-skill` off `main`).

**Spec:** `docs/superpowers/specs/2026-07-28-agent-cycle-plugin-design.md` § 4.2 (spec skill), § 6 (re-entry ladder / anti-gaming).

---

### Task 1: EDD eval cases — before the skill exists

**Files:**
- Create: `skills/spec/evals/cases.json`
- Create: `skills/spec/evals/README.md`
- Create: `skills/spec/evals/results.md`

- [ ] **Step 1: Write the eval cases**

Write `skills/spec/evals/cases.json`:

```json
{
  "skill": "agent-cycle:spec",
  "spec_ref": "docs/superpowers/specs/2026-07-28-agent-cycle-plugin-design.md#42-agent-cyclespec",
  "cases": [
    {
      "id": "SPC-E01",
      "type": "positive",
      "input": "Write the spec for this agent. The approved design is at docs/agent/design.md. (Run in a repo containing an APPROVED design.md, e.g. the real whatsapp-owner-assistant one.)",
      "expected": {
        "fires": true,
        "checks": [
          "Reads design.md and does NOT re-ask anything already resolved there (scope, tools, deployment target, NO-goals)",
          "Interviews ONLY on the design's open questions, one question at a time",
          "Every capability implied by the design has Gherkin scenarios with unique sequential BHV-NNN ids",
          "Each capability covers happy + wrong + edge (at least 3 scenarios per capability)",
          "Every tool from design §4 gets a contract: docstring-for-LLM, input/output schema with extra=forbid semantics, errors returned as observations (never raised)",
          "Every tool gets a FINAL action tier; any tier that differs from the design's guess carries a one-line justification",
          "Conversation section covers 24h-window handling, fallback replies, and the non-owner / out-of-scope drop behavior from the design's NO-goals",
          "Security section lists EVERY untrusted surface named in the design (e.g. inbound WhatsApp text, Notion content, calendar event text) with per-surface handling",
          "Data section defines session/dedupe/state schemas behind a repository interface",
          "Format tax respected: clean Markdown headers; YAML only for schemas nested >3 deep; no giant inline JSON blobs in prose",
          "Traceability table maps every BHV-NNN to a future eval slot (empty eval column allowed; the row must exist)",
          "Artifact written to docs/agent/spec.md with frontmatter agent_name, version, status: draft, date, design_version; skill stops at the human gate — approved only on explicit user approval"
        ]
      }
    },
    {
      "id": "SPC-E02",
      "type": "gate-negative",
      "input": "Write the spec for this agent. (Run in a repo where docs/agent/design.md has status: draft.)",
      "expected": {
        "fires": true,
        "checks": [
          "Refuses to proceed: names the missing gate (design.md is draft, not approved) and instructs running/approving agent-cycle:design first",
          "Writes NO spec.md and modifies NO files — verified on the filesystem afterward"
        ]
      }
    },
    {
      "id": "SPC-E03",
      "type": "edge-trivial-agent",
      "input": "Write the spec. (Run in a repo with an APPROVED design.md for a trivial agent: one safe read-only tool, two capabilities, no conversation channel constraints.)",
      "expected": {
        "fires": true,
        "checks": [
          "Produces ONE spec.md file — no folder split, no ceremony",
          "Scenario count proportional to the agent (roughly 6-8 BHV ids for two capabilities, not dozens)",
          "Sections that don't apply (e.g. channel-specific conversation rules) are collapsed to a one-line 'not applicable because X', never padded with invented content"
        ]
      }
    }
  ]
}
```

- [ ] **Step 2: Write the run procedure**

Write `skills/spec/evals/README.md`:

```markdown
# Eval procedure for agent-cycle:spec

Same agentic procedure as `skills/design/evals/README.md` (fresh session in a
scratch project, paste input, score every check PASS/FAIL with one line of
evidence, record per-check rows in `results.md`, fix-and-rerun on FAIL, dispute
— never silently edit — if a case itself is wrong).

Case-specific setup:

- **SPC-E01** needs a repo with an APPROVED `docs/agent/design.md`. The real
  dogfood repo (`whatsapp-owner-assistant`) is the canonical run.
- **SPC-E02** needs a repo whose `design.md` frontmatter says `status: draft`
  (copy the real one and flip the field in the copy).
- **SPC-E03** needs a minimal approved design.md: one safe read-only tool, two
  capabilities. Write it by hand in a scratch repo (5 minutes); do NOT use the
  design skill for it.

Presence checks require judgment on substance — a Gherkin scenario that cannot
fail, or a docstring that just restates the tool name, does NOT pass. For
SPC-E02, always check the filesystem afterward.

Gate: all checks PASS on all 3 cases before the skill graduates.
```

- [ ] **Step 3: Create the results log**

Write `skills/spec/evals/results.md`:

```markdown
# Eval runs — agent-cycle:spec

One row per check, per run. Verdict: PASS / FAIL. Evidence: one line.

| Date | Case | Check # | Verdict | Evidence |
|---|---|---|---|---|
```

- [ ] **Step 4: Verify JSON**

Run: `python -c "import json; d=json.load(open(r'skills/spec/evals/cases.json')); print(len(d['cases']), 'cases,', len(d['cases'][0]['expected']['checks']), 'checks in E01')"`
Expected: `3 cases, 12 checks in E01`

- [ ] **Step 5: Commit**

```bash
git add skills/spec/evals/
git commit -m "feat(spec): EDD eval cases before SKILL.md (SPC-E01..E03)"
```

---

### Task 2: Spec artifact template

**Files:**
- Create: `skills/spec/references/spec-template.md`

- [ ] **Step 1: Write the template**

Write `skills/spec/references/spec-template.md`:

```markdown
# spec.md template

The skill fills this template and writes it to `docs/agent/spec.md` in the
TARGET AGENT'S repo. Default is ONE file; split into a `specs/` folder only if
the single file would exceed ~400 lines. Frontmatter is mandatory —
`design_version` pins which design this spec was derived from (staleness
detection: if design.md's version moves past it, this spec is stale).

---
agent_name: <same-as-design>
version: 1
status: draft            # draft | approved — approved ONLY via explicit human gate
date: <YYYY-MM-DD>
design_version: <version of the design.md consumed>
---

# <Agent Name> — Spec

## 1. Behavior (BHV)

One subsection per capability. Scenario ids are BHV-NNN, unique and sequential
across the whole file. Every capability: at least happy + wrong + edge. A
scenario that cannot fail is not a scenario.

### Capability: <name>

```gherkin
# BHV-001 (happy)
Scenario: <one-line intent>
  Given <precondition — concrete state, not vibes>
  When <the triggering message/event, verbatim-style>
  Then <observable outcome: reply content, tool call, state change>

# BHV-002 (wrong)
Scenario: <what goes wrong — bad input, API failure, ambiguity>
  Given ...
  When ...
  Then <graceful behavior: fallback reply, no partial writes, degraded flag>

# BHV-003 (edge)
Scenario: <boundary: empty result, limit hit, stale data, 24h window edge>
  ...
```

## 2. Tools

One block per tool. The docstring IS the interface — written for the model.
Schemas use extra=forbid semantics: unknown fields are rejected. Errors are
caught inside the tool and returned as observations, never raised.

### `<tool_name>` — tier: <safe | reversible | destructive> <(justification if tier differs from design's guess)>

**Docstring (verbatim, for the LLM):**
> <What it does, when to use it, when NOT to use it, what it returns.>

**Input schema** (YAML only if nested >3 deep, else inline table):

| Field | Type | Required | Constraint |
|---|---|---|---|
| <field> | <type> | yes/no | <bounds/enum/format> |

**Output:** <shape of the JSON returned, including the error-as-observation form>
**Gate implication:** <safe → auto | reversible → per design policy | destructive → HITL approval, never cached>

## 3. Conversation

Channel mechanics the agent must respect. For WhatsApp: 24h service window
behavior (what happens when it expires), fallback reply for unsupported input
types, non-owner / out-of-scope drop behavior (mirror the design's NO-goals),
debounce policy for rapid consecutive messages, language mirroring. For
channel-less agents: one line — "not applicable because <reason>".

## 4. Security

- **Untrusted surfaces** — one row per surface named in the design, no
  omissions:

| Surface | Why untrusted | Handling |
|---|---|---|
| <e.g. inbound WhatsApp text> | <attacker-writable> | <extraction boundary, never in system prompt, sanitized echo> |

- **Least privilege:** scopes per credential, read provisioned separately from
  write.
- **Injection posture:** what happens when embedded instructions are detected
  (per the design's NO-goals); which BHV scenarios cover it.
- **PII / secrets:** what never leaves the agent (mirror design NO-goals);
  outbound sanitization rules.

## 5. Data

Schemas for session/state/dedupe behind a repository interface (the design's
sessions seam). Tables/collections with fields, key strategy, TTLs. YAML for
anything nested >3 deep.

## 6. Traceability

Every BHV row exists here from day one; /evals fills the eval column, /build
fills the test column.

| BHV | Capability | Eval (filled by /evals) | Test (filled by /build) |
|---|---|---|---|
| BHV-001 | <capability> | — | — |

## 7. Open questions → /evals & /build

<Unresolved items for the next phases. Non-empty — if truly nothing is open,
state the single riskiest assumption instead.>
```

- [ ] **Step 2: Commit**

```bash
git add skills/spec/references/spec-template.md
git commit -m "feat(spec): spec.md artifact template"
```

---

### Task 3: Derivation guide

**Files:**
- Create: `skills/spec/references/derivation-guide.md`

- [ ] **Step 1: Write the guide**

Write `skills/spec/references/derivation-guide.md`:

```markdown
# Derivation guide — agent-cycle:spec

How to go from an approved design.md to a spec.md. Order matters.

## Step 0 — Gate check (before anything else)

Read `docs/agent/design.md`. Hard-fail (write nothing, say why, stop) if:
- the file does not exist → "run agent-cycle:design first";
- frontmatter `status` != `approved` → "design is draft; approve it at the
  design gate first";
Record `design_version` = the design's `version` field. If the user asks to
change something the design already decided (scope, tools, deployment,
NO-goals), do NOT fold it in here — that is the re-entry ladder: the design
must be re-opened, bumped, and re-approved first.

## Step 1 — Capability extraction (no interview)

Derive the capability list mechanically from the design: Actuators + Sensors
define what the agent can do; the Performance metric defines what it is FOR.
List capabilities as verb phrases ("answer calendar availability questions",
"find and summarize Notion pages"). Show the list to the user as ONE
confirmation question — "these N capabilities, complete?" — before writing
scenarios.

## Step 2 — Interview: open questions ONLY

The design's §7 open questions are the entire interview agenda. One question
per message, multiple choice where possible. Do not re-ask anything §§1-6 of
the design already answers. Typical open questions land here as: tool tier
finalization (e.g. an irreversible send), session TTL values, secret storage,
baseline measurement protocol. If an answer contradicts the approved design →
stop, name the contradiction, route to the re-entry ladder.

## Step 3 — Behavior scenarios

Per capability, write Gherkin: happy first, then wrong (API failure, ambiguous
request, empty result), then edge (limits, staleness, window boundaries).
Number BHV-NNN sequentially across the file. Quality bar per scenario:
- Given states concrete state (a fixture, not "some events exist");
- When is a realistic user message or event, quotable;
- Then is observable (reply text contains X / tool Y called with Z / no write
  occurred / degraded flag set). A scenario that cannot fail does not count.
Security scenarios are behavior too: every untrusted surface gets at least one
injection-attempt scenario whose Then is "instructions treated as data".

## Step 4 — Tool contracts

One per design §4 tool, no more, no less (a new tool = design change → re-entry
ladder). Docstring written for the model: what/when/when-NOT/returns. Schemas
extra=forbid. Errors as observations. FINAL tier per tool: confront each design
tier guess — if it changes (e.g. a WhatsApp send is irreversible), one-line
justification. Tier → gate implication is mechanical: safe=auto,
destructive=HITL never-cached.

## Step 5 — Conversation, Security, Data

Conversation: channel mechanics from the design's Environment (24h window,
fallbacks, drop rules, debounce, language). Security: every untrusted surface
from the design gets a handling row + a BHV scenario reference. Data: schemas
behind the repository interface named in the design's sessions seam.

## Step 6 — Format tax check

Markdown headers throughout; YAML only for schemas nested >3 deep; tables over
prose for enumerable facts; no giant JSON blobs in prose. This is a performance
lever, not aesthetics.

## Step 7 — Traceability + gate

Fill §6 with one row per BHV (eval/test columns em-dash). Write spec.md with
status: draft. Present in chat: capability list, BHV count per capability,
tier changes vs design, untrusted-surface table, open questions. Ask for
approval. On explicit approval only → status: approved. Hand off:
"Next: agent-cycle:evals reads this artifact."
```

- [ ] **Step 2: Commit**

```bash
git add skills/spec/references/derivation-guide.md
git commit -m "feat(spec): derivation guide (gate check, capability extraction, Gherkin quality bar)"
```

---

### Task 4: SKILL.md

**Files:**
- Create: `skills/spec/SKILL.md`

- [ ] **Step 1: Write the skill**

Write `skills/spec/SKILL.md`:

```markdown
---
name: spec
description: "Phase 2 of the agent-cycle pipeline: turn an APPROVED docs/agent/design.md into an executable docs/agent/spec.md — Gherkin behavior scenarios (BHV-NNN), final tool contracts with action tiers, conversation rules, security policy, data schemas, traceability table. Use when the user wants to spec/specify an agent whose design is approved — 'write the spec', 'siguiente fase del pipeline', 'spec the agent'. Do NOT use without an approved design.md (run agent-cycle:design first), nor for writing evals or code (later phases), nor for general BDD/Gherkin help unrelated to the agent-cycle pipeline."
---

# agent-cycle:spec — Executable Specification

Turn the approved design into the blueprint /evals and /build consume
literally. If the brain gets a vibe instead of a blueprint, it guesses.

## Knowledge base

Load the user's `agent-design` skill as knowledge base for tool-contract and
security rules. REFERENCE it — never copy content into artifacts or this skill.

## Hard rules

1. GATE FIRST: hard-fail if `docs/agent/design.md` is missing or not
   `status: approved`. Write nothing. Name the gate.
2. The design is settled law. Interview ONLY on its §7 open questions, one
   question per message. A request to change an approved design decision goes
   to the re-entry ladder (re-open design, bump version, re-approve) — never
   folded silently into the spec.
3. Every capability gets happy + wrong + edge Gherkin with unique sequential
   BHV-NNN ids. A scenario that cannot fail does not count.
4. Tools: exactly the design's inventory. Docstring is the interface. Schemas
   extra=forbid. Errors as observations. FINAL tier per tool — tier changes vs
   the design's guess carry a one-line justification.
5. Every untrusted surface named in the design appears in §4 with handling AND
   at least one injection-attempt BHV scenario.
6. Format tax: Markdown headers; YAML only for schemas nested >3 deep.
7. ONE spec.md by default; split only if >~400 lines. Sections that don't
   apply collapse to one line with the reason — never padded.
8. Artifact carries frontmatter `agent_name, version, status: draft, date,
   design_version`. Approved ONLY at the explicit human gate. Never
   self-approve. Write ONLY `docs/agent/spec.md`.

## Workflow

1. Read `references/derivation-guide.md`; run steps 0→7 in order.
2. Step 0 gate check → step 1 capability confirmation (one question) → step 2
   open-questions interview → steps 3-6 drafting → step 7 traceability + gate.
3. Fill `references/spec-template.md`. Write `docs/agent/spec.md`
   (`status: draft`, `design_version` pinned).
4. Present summary: capability list, BHV count per capability, tier changes vs
   design (with justifications), untrusted-surface table, open questions.
5. Explicit approval → `status: approved`. Feedback → edit, re-present.
6. Hand off: "Next phase: `agent-cycle:evals` reads this artifact."

## Failure modes to avoid

- Proceeding on a draft or missing design (violates rule 1).
- Re-interviewing settled design decisions (violates rule 2).
- Gherkin that cannot fail — "Then it works correctly" (violates rule 3).
- Inventing tools not in the design, or dropping one (violates rule 4).
- An untrusted surface with handling but no injection scenario (violates rule 5).
- Padding non-applicable sections to look complete (violates rule 7).
- Setting status: approved without the human gate (violates rule 8).
```

- [ ] **Step 2: Verify frontmatter**

Run: `head -4 skills/spec/SKILL.md`
Expected: `---`, `name: spec`, description line present.

- [ ] **Step 3: Commit**

```bash
git add skills/spec/SKILL.md
git commit -m "feat(spec): SKILL.md — gated derivation workflow (design is settled law)"
```

---

### Task 5: Release v0.2.0

**Files:**
- Modify: `.claude-plugin/plugin.json` (version)
- Modify: `README.md` (status line)
- Modify: `CHANGELOG.md` (new entry)

- [ ] **Step 1: Bump manifest version**

In `.claude-plugin/plugin.json` change `"version": "0.1.0"` → `"version": "0.2.0"`.

- [ ] **Step 2: Update README status**

Replace the README status line:
```
**Status:** v0.1.0 — `design` skill only. Built skill-by-skill, each dogfooded on
a real agent before the next begins.
```
with:
```
**Status:** v0.2.0 — `design` + `spec` skills. Built skill-by-skill, each
dogfooded on a real agent before the next begins.
```

- [ ] **Step 3: Add CHANGELOG entry**

Insert at the top of `CHANGELOG.md`, after the intro paragraph:

```markdown
## [0.2.0] — 2026-07-28

### Added
- **`spec` skill** (phase 2 of 7): approved design.md → executable spec.md.
  Gherkin scenarios with BHV-NNN ids (happy/wrong/edge per capability), final
  tool contracts (docstring-as-interface, extra=forbid schemas, action tiers
  with justified changes), conversation rules, per-surface security handling
  with mandatory injection scenarios, data schemas, traceability table.
  Hard gate on design approval; design is settled law (re-entry ladder for
  changes); one-file default with format-tax discipline.
- EDD eval suite (`skills/spec/evals/`): SPC-E01 positive (12-check contract),
  SPC-E02 gate-negative (draft design → refuse, write nothing), SPC-E03
  trivial-agent edge (proportionality, no ceremony).

### Pending graduation
- `spec` skill eval runs against the real agent — tag `spec-v0.1` when the
  dogfood passes.
```

- [ ] **Step 4: Verify JSON + commit**

Run: `python -c "import json; print(json.load(open(r'.claude-plugin/plugin.json'))['version'])"`
Expected: `0.2.0`

```bash
git add .claude-plugin/plugin.json README.md CHANGELOG.md
git commit -m "chore: release v0.2.0 (spec skill)"
```

---

### Task 6 (Alan, interactive): eval runs + dogfood

- [ ] SPC-E02: scratch repo with a draft-status design.md copy → skill must refuse and write nothing → record rows in results.md.
- [ ] SPC-E03: scratch repo with a hand-written trivial approved design.md → proportional one-file spec → record rows.
- [ ] SPC-E01 dogfood: run `spec` in `C:\Proyectos\Whatsapp_agent` — the interview agenda is the design's 9 open questions → `docs/agent/spec.md` approved without manual rework → record rows → tag `spec-v0.1`.
- [ ] Update marketplace + reinstall to pick up v0.2.0.

---

## Self-review (done at planning time)

- **Spec §4.2 coverage:** single-file default + 5 content sections = template §§1-5 (+traceability §6 per §4.2's traceability clause); gate-on-draft = rule 1 + SPC-E02; interview-only-open-questions = rule 2 + guide step 2; BHV→forge ACs pathway preserved via traceability table; format tax = rule 6 + guide step 6. Re-entry ladder integration (§6 of the plugin design) = rule 2 + guide steps 0/2.
- **Placeholder scan:** all file contents literal; no TBDs.
- **Consistency:** frontmatter fields identical in template and SKILL.md rule 8 and SPC-E01 check 12; `design_version` staleness matches the plugin design's surgical-staleness mechanism; tier vocabulary (safe/reversible/destructive) matches design skill's template §4; BHV-NNN format matches plugin design §4.2/§4.3; the injection-scenario rule (rule 5) matches SPC-E01 check 8 and template §4.
```
