# agent-cycle `/design` Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first skill of the agent-cycle plugin — `agent-cycle:design` — which interviews the user and produces an approvable `docs/agent/design.md` (PEAS + environment classification + harness + deployment intent), plus the plugin manifest it debuts in.

**Architecture:** Claude Code plugin at `C:\Proyectos\agent-cycle\` with skills auto-discovered from `skills/`. The design skill is process-only markdown (no code): a SKILL.md workflow + two reference files + an EDD eval-case file written BEFORE the SKILL.md (per the design doc's EDD rule). The skill loads the user's personal `agent-design` skill as knowledge base and never copies it. Definition of done = the dogfood run: the real WhatsApp-on-AWS agent's design.md, approved by Alan without manual rework.

**Tech Stack:** Claude Code plugin format (`.claude-plugin/plugin.json`, `skills/*/SKILL.md`), Markdown/JSON only. Git repo already initialized at `C:\Proyectos\agent-cycle\`.

**Spec:** `docs/superpowers/specs/2026-07-28-agent-cycle-plugin-design.md` § 4.1 (design skill), § 3 (plugin architecture), § 2 (foundational decisions).

**Working directory:** all paths below are relative to `C:\Proyectos\agent-cycle\`.

**Note on testing this plan's "code":** the deliverables are markdown/JSON, so TDD maps to EDD — eval cases are written first (Task 2), the skill is written to satisfy them (Tasks 3–5), and eval runs are the verification (Tasks 6–8). File-existence/JSON-validity checks stand in for unit tests where applicable.

---

### Task 1: Plugin scaffold and manifest

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `README.md`

- [ ] **Step 1: Create the manifest**

Write `.claude-plugin/plugin.json`:

```json
{
  "name": "agent-cycle",
  "description": "Complete construction cycle for AI agents: design, spec, evals-first, build (multi-cloud adapters), skills, interop, ship — plus economics and blueprint transversals. Gated, disk-backed pipeline.",
  "version": "0.1.0",
  "author": {
    "name": "Alan Vazquez"
  }
}
```

- [ ] **Step 2: Create the repo README**

Write `README.md`:

```markdown
# agent-cycle

Claude Code plugin that runs the complete construction cycle of an AI agent —
from idea to shipped, evaluated, observable production agent — as a gated,
disk-backed pipeline of skills.

## Pipeline

| Phase | Skill | Artifact |
|---|---|---|
| 1 Design | `agent-cycle:design` | `docs/agent/design.md` |
| 2 Spec | `agent-cycle:spec` | `docs/agent/spec.md` |
| 3 Evals | `agent-cycle:evals` | `evals/` |
| 4 Build | `agent-cycle:build` | `src/` |
| 5 Skills | `agent-cycle:skills` (conditional) | target agent skills |
| 6 Interop | `agent-cycle:interop` (conditional) | Agent Card + A2A |
| 7 Ship | `agent-cycle:ship` | DoD report |
| — | `agent-cycle:economics` (transversal) | `docs/agent/<name>-economics.md` |
| — | `agent-cycle:blueprint` (transversal) | `docs/agent/blueprint.html` |

Every phase fails hard if its upstream artifact is missing, `draft`, or stale.
Human gate between every phase. See `docs/superpowers/specs/` for the full design.

**Status:** v0.1 — `design` skill only. Built skill-by-skill, each dogfooded on
a real agent before the next begins.
```

- [ ] **Step 3: Verify JSON validity**

Run: `python -c "import json; json.load(open(r'.claude-plugin/plugin.json')); print('valid')"`
Expected: `valid`

- [ ] **Step 4: Commit**

```bash
git add .claude-plugin/plugin.json README.md
git commit -m "feat: plugin scaffold and manifest (v0.1.0)"
```

---

### Task 2: EDD eval cases — written BEFORE the skill exists

**Files:**
- Create: `skills/design/evals/cases.json`
- Create: `skills/design/evals/README.md`
- Create: `skills/design/evals/results.md`

- [ ] **Step 1: Write the eval cases**

Write `skills/design/evals/cases.json`:

```json
{
  "skill": "agent-cycle:design",
  "spec_ref": "docs/superpowers/specs/2026-07-28-agent-cycle-plugin-design.md#41-agent-cycledesign",
  "cases": [
    {
      "id": "DES-E01",
      "type": "positive",
      "input": "Design a WhatsApp appointment-booking agent for a dental clinic, to be deployed on AWS for a client.",
      "expected": {
        "fires": true,
        "checks": [
          "Interviews one question at a time — never a battery of questions in one message",
          "PEAS Performance is a metric of the environment (e.g. booked-appointment rate, no-show reduction), not agent activity (e.g. messages sent)",
          "PEAS table includes at least one Goodhart stress-test note",
          "Environment classified on all 5 dimensions (observable/stochastic/sequential/dynamic/multi-agent), each with its architectural implication",
          "Harness decision defaults to single-agent with written justification",
          "Deployment intent = AWS, with all 3 portability seams declared: sessions (framework-native store), model (LiteLLM config), telemetry (OTel)",
          "NO-goals section is non-empty",
          "Open questions section exists (input to /spec)",
          "Artifact written to docs/agent/design.md with frontmatter: agent_name, version, status: draft, date",
          "Skill stops at the human gate — status becomes approved only after explicit user approval"
        ]
      }
    },
    {
      "id": "DES-E02",
      "type": "trigger-negative",
      "input": "Review this orchestration code for agent best practices: [any pasted LangGraph/ADK pipeline code]",
      "expected": {
        "fires": false,
        "checks": [
          "agent-cycle:design does NOT fire — review tasks belong to the personal agent-design knowledge skill",
          "No docs/agent/design.md is created"
        ]
      }
    },
    {
      "id": "DES-E03",
      "type": "edge-partial-peas",
      "input": "Design an agent. I already have part of PEAS: Performance = at least 80% of appointment requests resolved without a human; Environment = WhatsApp conversations with dental patients in Mexico. I'm missing the rest.",
      "expected": {
        "fires": true,
        "checks": [
          "Does NOT re-ask Performance or Environment",
          "Starts the interview at Actuators/Sensors",
          "Still runs the Goodhart stress-test on the user-provided Performance metric",
          "Completes classification, harness, deployment intent, NO-goals normally"
        ]
      }
    }
  ]
}
```

- [ ] **Step 2: Write the run procedure**

Write `skills/design/evals/README.md`:

```markdown
# Eval procedure for agent-cycle:design

The skill is a human-in-the-loop process, so evals run agentically, not via pytest.

Per case in `cases.json`:

1. Start a FRESH Claude Code session in a scratch project (never this repo).
2. Paste the case's `input` verbatim as the user message.
3. Observe whether the skill fires (`fires` check) and follow the interview to
   completion for positive/edge cases (answer as a plausible dental-clinic owner).
4. Score every item in `expected.checks` as PASS / FAIL with one line of evidence.
5. Record the run in `results.md` (date, case id, per-check verdict, notes).

Gate: all checks PASS on all 3 cases before the skill graduates. A FAIL means
fix the SKILL.md (or the case, if the case itself is wrong — via dispute, not
silent edit) and re-run that case fresh.
```

- [ ] **Step 3: Create the empty results log**

Write `skills/design/evals/results.md`:

```markdown
# Eval runs — agent-cycle:design

| Date | Case | Verdict | Notes |
|---|---|---|---|
```

- [ ] **Step 4: Verify JSON validity**

Run: `python -c "import json; d=json.load(open(r'skills/design/evals/cases.json')); print(len(d['cases']), 'cases')"`
Expected: `3 cases`

- [ ] **Step 5: Commit**

```bash
git add skills/design/evals/
git commit -m "feat(design): EDD eval cases before SKILL.md (DES-E01..E03)"
```

---

### Task 3: Artifact template

**Files:**
- Create: `skills/design/references/artifact-template.md`

- [ ] **Step 1: Write the design.md template**

Write `skills/design/references/artifact-template.md`:

```markdown
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
the balancing factor that prevents it. At least one note, always.>

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

<Anything unresolved. /spec interviews ONLY on these.>
```

- [ ] **Step 2: Commit**

```bash
git add skills/design/references/artifact-template.md
git commit -m "feat(design): design.md artifact template"
```

---

### Task 4: Interview guide

**Files:**
- Create: `skills/design/references/interview-guide.md`

- [ ] **Step 1: Write the interview guide**

Write `skills/design/references/interview-guide.md`:

```markdown
# Interview guide — agent-cycle:design

Rules: ONE question per message. Multiple choice where possible. Skip anything
the user already provided (edge case DES-E03) — but never skip the Goodhart
stress-test, even on user-provided metrics.

## Phase A — PEAS (order: P, E, A, S)

**P (Performance):**
- "What single measurable outcome defines success for this agent?" If the answer
  is agent activity (messages sent, tickets touched), push back once: "That
  measures the agent, not the world. What changes in the business if it works?"
- Goodhart stress-test (always): "If the agent optimized ONLY <metric>, what's
  the worst way it could hit the number?" Record the answer as a Goodhart note
  and add the balancing factor (e.g. call-time metric → agent hangs up on hard
  problems → balance with resolution rate).

**E (Environment):** who talks to it, on what channel, connected to which
systems, in what language/market. For WhatsApp agents: business-initiated or
user-initiated? 24h-window implications land in /spec, but note the mode here.

**A (Actuators):** "What is the agent allowed to DO?" List tools by name +
one-line purpose only. For each, gut-guess the tier (safe read / reversible
write / destructive) — /spec finalizes.

**S (Sensors):** "What can it READ?" Inbound messages, DBs, calendars, APIs.

## Phase B — Environment classification

Ask only the dimensions not already obvious from Phase A answers. Map each to
its implication (table in artifact-template.md). Typical WhatsApp business
agent: partially observable, stochastic, sequential, dynamic, single-agent.

## Phase C — Harness

Default single-agent. Ask: "Is there any part of this job that needs different
permissions, different systems access, or true parallelism?" If no → single.
If yes → name the boundary and justify multi-agent in one paragraph.
Run the 5-part completeness check (model/tools/memory/orchestration/deployment)
and note gaps as open questions.

## Phase D — Deployment intent

"Where will this run — AWS, GCP, or a VPS — and is that the client's constraint
or a choice?" Declare the 3 seams (sessions/model/telemetry) with the concrete
binding for the chosen target. Cite the vault's Multi-Cloud Agent Deployment
Patterns for the adapter surface.

## Phase E — NO-goals and gate

- "Name at least two things this agent must NOT do." (refunds without human?
  medical advice? out-of-scope topics?)
- Present the filled artifact summary in chat. Ask for approval. On explicit
  approval ONLY: set `status: approved`, bump nothing else. On feedback: edit,
  re-present.
```

- [ ] **Step 2: Commit**

```bash
git add skills/design/references/interview-guide.md
git commit -m "feat(design): PEAS interview guide"
```

---

### Task 5: SKILL.md

**Files:**
- Create: `skills/design/SKILL.md`

- [ ] **Step 1: Write the skill**

Write `skills/design/SKILL.md`:

```markdown
---
name: design
description: "Phase 1 of the agent-cycle pipeline: interview the user and produce an approvable docs/agent/design.md (PEAS + environment classification + harness decision + deployment intent + NO-goals) for a NEW agent. Use when the user wants to design, start, or scope a new AI agent from an idea — 'design an agent for X', 'quiero un agente que...', 'new agent for client Y'. Do NOT use for reviewing existing agent code or architectures (that is the agent-design knowledge skill), nor for writing specs/evals/code (later phases)."
---

# agent-cycle:design — Agent Design Interview

Turn an agent idea into an approved `docs/agent/design.md`. This is the layer
where errors are cheapest — everything downstream inherits this artifact.

## Knowledge base

Load the user's `agent-design` skill (personal skills) as the knowledge base
for PEAS rules, environment→architecture mapping, and harness principles.
REFERENCE it — never copy its content into artifacts or this skill.

## Hard rules

1. ONE interview question per message. Multiple choice where possible.
2. Skip questions the user already answered (partial PEAS input) — but ALWAYS
   run the Goodhart stress-test, even on user-provided metrics.
3. Performance = a metric of the ENVIRONMENT, never agent activity.
4. Single-agent by default; multi-agent needs a written, measurable justification.
5. Deployment intent + 3 seams (sessions / model / telemetry) are declared HERE,
   not deferred to build.
6. The artifact is written with `status: draft`. It becomes `approved` ONLY on
   explicit user approval at the final gate. Never self-approve.
7. Write ONLY `docs/agent/design.md` in the target agent's repo. No other files.

## Workflow

1. Read `references/interview-guide.md`. Run phases A→E, one question at a time.
2. Fill `references/artifact-template.md` with the answers.
3. Write to `docs/agent/design.md` (target repo), frontmatter:
   `agent_name, version: 1, status: draft, date`.
4. Present the summary in chat: PEAS table, classification, harness, deployment
   intent, NO-goals. Ask for approval.
5. On explicit approval → set `status: approved` and report done. On feedback →
   edit, re-present (stay at gate).
6. Hand off: "Next phase: `agent-cycle:spec` reads this artifact."

## Failure modes to avoid

- Battery of questions in one message (violates rule 1).
- Accepting "messages responded" as Performance (violates rule 3).
- Inventing tool schemas (that is /spec's job — names + purpose only).
- Writing status: approved without the human gate (violates rule 6).
```

- [ ] **Step 2: Verify frontmatter parses (visual check)**

Run: `head -5 skills/design/SKILL.md`
Expected: frontmatter opens with `---`, `name: design`, description present.

- [ ] **Step 3: Commit**

```bash
git add skills/design/SKILL.md
git commit -m "feat(design): SKILL.md — PEAS interview workflow with human gate"
```

---

### Task 6: Install plugin locally and run trigger-negative eval (DES-E02)

**Files:**
- Modify: `skills/design/evals/results.md`

- [ ] **Step 1: Install the plugin from the local folder**

In Claude Code, register the local repo as a plugin source. Either route works:
- Interactive: run `/plugin marketplace add C:\Proyectos\agent-cycle` then install `agent-cycle` (dialog commands are unavailable inside non-interactive sessions — do this from an interactive `claude` terminal), or
- Config: add the path to the user's plugin configuration per current Claude Code docs.

Verification: in a fresh session, the skills listing shows `agent-cycle:design`.
If it does not appear, stop and debug discovery (folder must contain
`.claude-plugin/plugin.json` and `skills/design/SKILL.md`) before continuing.

- [ ] **Step 2: Run DES-E02 (trigger-negative)**

Fresh session in a scratch project. Paste: `Review this orchestration code for agent best practices:` + any small LangGraph snippet.
Expected: `agent-cycle:design` does NOT fire; no `docs/agent/design.md` created.

- [ ] **Step 3: Record the result**

Append to `skills/design/evals/results.md` the row: date, `DES-E02`, PASS/FAIL, one-line evidence. If FAIL (skill fired): tighten the description's do-NOT-use clause in `skills/design/SKILL.md`, commit, re-run fresh.

- [ ] **Step 4: Commit**

```bash
git add skills/design/evals/results.md
git commit -m "test(design): DES-E02 trigger-negative eval run"
```

---

### Task 7: Run edge eval (DES-E03, partial PEAS)

**Files:**
- Modify: `skills/design/evals/results.md`

- [ ] **Step 1: Run DES-E03**

Fresh session in a scratch project. Paste the DES-E03 input verbatim from `cases.json`. Answer the interview as a plausible dental-clinic owner.
Expected per checks: no re-asking P/E; starts at Actuators; Goodhart test still runs on the provided metric; completes normally to the gate.

- [ ] **Step 2: Record the result**

Append the `DES-E03` row to `results.md` with per-check verdicts. On any FAIL: fix `SKILL.md`/`interview-guide.md`, commit the fix, re-run fresh.

- [ ] **Step 3: Commit**

```bash
git add skills/design/evals/results.md
git commit -m "test(design): DES-E03 edge eval run (partial PEAS)"
```

---

### Task 8: Dogfood — DES-E01 on the real WhatsApp agent (DoD)

**Files:**
- Modify: `skills/design/evals/results.md`
- Create (in the AGENT's repo, not this one): `docs/agent/design.md`

- [ ] **Step 1: Create/choose the agent repo**

Alan creates the WhatsApp agent's project folder (e.g. `C:\Proyectos\<client-agent-name>\`). The dogfood runs THERE — the plugin repo never contains agent artifacts.

- [ ] **Step 2: Run the real design session**

In the agent repo, Alan invokes the skill with the real brief ("agente de citas por WhatsApp para <cliente>, deploy AWS"). Full interview, real answers. Output: that repo's `docs/agent/design.md`, `status: draft`.

- [ ] **Step 3: Gate**

Alan reviews the artifact. DoD bar: **approved without manual rework** — Alan edits nothing by hand; any deficiency is feedback the skill must incorporate at the gate (or a SKILL.md fix + re-run).

- [ ] **Step 4: Record DES-E01 and close**

Append the `DES-E01` row to `results.md` with per-check verdicts against the real run.

- [ ] **Step 5: Commit and tag**

```bash
git add skills/design/evals/results.md
git commit -m "test(design): DES-E01 dogfood run on real WhatsApp agent - skill graduated"
git tag design-v0.1
```

---

## Self-review (done at planning time)

- **Spec coverage (§4.1):** interview→artifact→gate = Tasks 4–5; EDD-before-SKILL = Task 2 precedes 5; knowledge-base reference rule = SKILL.md "Knowledge base" section; deployment intent + seams = template §5 + guide Phase D; DoD dogfood = Task 8. Manifest debut (§3) = Task 1. No gaps found.
- **Placeholder scan:** all file contents are complete inline; no TBDs.
- **Consistency:** artifact sections (7) match between template, SKILL.md workflow, and DES-E01 checks; case IDs match between cases.json and Tasks 6–8; `status: draft|approved` semantics identical in template, SKILL.md rule 6, and DES-E01 final check.
```
