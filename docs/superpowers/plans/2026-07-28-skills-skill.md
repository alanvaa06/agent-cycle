# agent-cycle `/skills` Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship phase 5 — `agent-cycle:skills` — the conditional phase that decides whether the TARGET agent needs skills (on-demand procedural know-how) and, when yes, authors them EDD-first with routing-grade descriptions, ≥90% trigger accuracy, co-loaded regression, and a draft→action authority ladder. "No skills needed" is a successful outcome, recorded and justified. Then release v0.6.0.

**Architecture:** Same shape (EDD cases → two references → SKILL.md). Core stances from plugin design §4.5: entry test per capability (procedural on-demand know-how vs tool + static instruction); zero ceremony skills — badly built skills subtract capability (SkillsBench: 19% performed worse with a skill); every authored skill gets its own eval cases BEFORE its SKILL.md; never evaluate in isolation (production co-loads); authority ladder gates action-allowed behind pass^k + human approval. Runtime-agnostic: harness-native skills (Claude Code-style) or a custom loader the build implemented — the binding is declared, not assumed. Artifact: `docs/agent/skills.md` (the decision record) + the skills themselves in the target repo when authored.

**Tech Stack:** Claude Code plugin format, Markdown/JSON only.

**Spec:** `docs/superpowers/specs/2026-07-28-agent-cycle-plugin-design.md` § 4.5.

---

### Task 1: EDD eval cases — before the skill exists

**Files:**
- Create: `skills/skills/evals/cases.json`
- Create: `skills/skills/evals/README.md`
- Create: `skills/skills/evals/results.md`

- [ ] **Step 1: Write the eval cases**

Write `skills/skills/evals/cases.json`:

```json
{
  "skill": "agent-cycle:skills",
  "spec_ref": "docs/superpowers/specs/2026-07-28-agent-cycle-plugin-design.md#45-agent-cycleskills-conditional",
  "cases": [
    {
      "id": "SKL-E01",
      "type": "positive-none",
      "input": "Does this agent need skills? Run the skills phase. (Run in a repo with approved design+spec+build where every capability is covered by tools + static instructions, e.g. the real whatsapp-owner-assistant.)",
      "expected": {
        "fires": true,
        "checks": [
          "Gate: design.md, spec.md AND docs/agent/build.md all approved; version chain consistent (spec.design_version, build's spec_version links)",
          "Entry test applied PER CAPABILITY: a table mapping each capability to its verdict (tool+static suffices / skill warranted) with a one-line reason each — never a global gut call",
          "Verdict 'none' is delivered as a successful outcome: zero ceremony skills authored, and the record says WHY none qualifies (no on-demand procedural variants, no per-client policies, static instructions within budget)",
          "Re-visit triggers documented: the concrete changes that would reopen this phase (e.g. a second client with different policies, process variants exceeding N, static instruction bloat past a stated token budget)",
          "Artifact docs/agent/skills.md written with frontmatter (agent_name, version, status: draft, date, spec_version, build_version) and decision: none; skill stops at the human gate"
        ]
      }
    },
    {
      "id": "SKL-E02",
      "type": "positive-authored",
      "input": "Run the skills phase. (Run against a scratch agent whose approved spec includes genuine on-demand procedural variants — e.g. 12 per-client return policies that cannot live in static instructions.)",
      "expected": {
        "fires": true,
        "checks": [
          "Entry test identifies the skill-warranted capabilities and ONLY those become skills — capabilities covered by tools/static instructions are left alone",
          "Per authored skill, eval cases exist BEFORE its SKILL.md: at least trigger-positive, trigger-negative, and one execution case",
          "Every description is a routing algorithm: what it does + when to use + when NOT to use; no 'helpful skill for...' phrasing; one skill = one job",
          "Trigger accuracy target >=90% declared AND measured: routing runs with paraphrased/variant trigger phrases recorded per skill",
          "Regression is co-loaded: the trigger/execution runs happen with ALL the agent's skills loaded together, never in isolation",
          "Authority ladder enforced: every new skill enters at draft; action-allowed requires pass^k evidence plus explicit human approval, recorded in skills.md",
          "Runtime binding declared in skills.md: HOW this agent loads skills (harness-native discovery or the build's loader mechanism) — not assumed"
        ]
      }
    },
    {
      "id": "SKL-E03",
      "type": "gate-negative",
      "input": "Run the skills phase. (Run twice: once with no docs/agent/build.md, once where spec.md was version-bumped after build.md was approved — stale chain.)",
      "expected": {
        "fires": true,
        "checks": [
          "Refuses in both branches: names the missing/stale gate (no build → run agent-cycle:build first; stale chain → re-entry ladder) and stops",
          "Writes NO files in either branch — verified on the filesystem afterward"
        ]
      }
    },
    {
      "id": "SKL-E04",
      "type": "trigger-negative",
      "input": "Help me write a Claude Code skill that formats my git commit messages nicely.",
      "expected": {
        "fires": false,
        "checks": [
          "agent-cycle:skills does NOT fire — generic skill authoring outside the pipeline belongs to skill-creator-type tooling",
          "No files are created or modified — verified on the filesystem afterward"
        ]
      }
    }
  ]
}
```

- [ ] **Step 2: Write the run procedure**

Write `skills/skills/evals/README.md`:

```markdown
# Eval procedure for agent-cycle:skills

Same agentic procedure as `skills/design/evals/README.md` (fresh session,
per-check PASS/FAIL rows in `results.md`, fix-and-rerun, dispute — never
silently edit — if a case is wrong).

Case-specific setup:

- **SKL-E01** is the real dogfood run: the whatsapp-owner-assistant's v1
  surface (read-only, 5 capabilities, 7 tools) is expected to produce
  decision: none. Scoring the entry-test check requires the per-capability
  table — a bare "doesn't need skills" is a FAIL even if the conclusion is
  right.
- **SKL-E02** needs a hand-written scratch pipeline (design+spec+build.md,
  minimal but approved) whose spec names genuine per-client process variants.
  Budget ~45 min to author the fixture; do NOT use the pipeline skills.
- **SKL-E03** branch 2: copy the real repo, bump spec.md to version 2 leaving
  build.md's spec_version at 1.
- **SKL-E04**: filesystem check afterward.

Scoring anchors: trigger-accuracy (E02 check 4) is scored from recorded
routing runs — at least 5 paraphrase variants per skill, >=90% correct
routing, misses listed. Co-loaded (E02 check 5) means the transcript shows the
full skill set present during the runs, not one-skill-at-a-time sessions.
```

- [ ] **Step 3: Create the results log**

Write `skills/skills/evals/results.md`:

```markdown
# Eval runs — agent-cycle:skills

One row per check, per run. Verdict: PASS / FAIL. Evidence: one line.

| Date | Case | Check # | Verdict | Evidence |
|---|---|---|---|---|
```

- [ ] **Step 4: Verify JSON**

Run: `python -c "import json; d=json.load(open(r'skills/skills/evals/cases.json')); print(len(d['cases']), 'cases,', len(d['cases'][0]['expected']['checks']), 'checks in E01')"`
Expected: `4 cases, 5 checks in E01`

- [ ] **Step 5: Commit**

```bash
git add skills/skills/evals/
git commit -m "feat(skills): EDD eval cases before SKILL.md (SKL-E01..E04)"
```

---

### Task 2: Entry test reference

**Files:**
- Create: `skills/skills/references/entry-test.md`

- [ ] **Step 1: Write the reference**

Write `skills/skills/references/entry-test.md`:

```markdown
# Entry test — agent-cycle:skills

Skills are on-demand procedural memory: know-how loaded only when a matching
task appears. They are NOT the place for global context, tool reach, or
always-on rules. Badly built skills subtract capability — the burden of proof
is on adding one, never on skipping it.

## The test, per capability

For EVERY capability in the spec, answer in order; first "yes" that holds
decides:

1. **Static suffices?** Can this live in the agent's always-on instructions
   within budget (rule of thumb: the static block stays under ~2k tokens total
   and under ~10 always-on rules)? → tool + static instruction. No skill.
2. **Tool suffices?** Is it an action against a system with fixed semantics?
   → it is a tool contract (spec §Tools), not know-how. No skill.
3. **On-demand procedural?** Is it a multi-step procedure that (a) applies
   only when a specific task type appears, (b) varies by case/client/process,
   and (c) would bloat static instructions if always loaded? → SKILL
   candidate.
4. **Multi-agent instead?** Does it need different permissions, systems, or
   true parallelism? → that is an architecture change (re-entry to design),
   not a skill.

Record the table: capability → verdict → one-line reason. The table IS the
deliverable of the test — a bare conclusion fails the phase's own eval.

## Decision: none

A clean "none" is a SUCCESS. Record in docs/agent/skills.md:
- the per-capability table;
- why nothing qualifies (typical for v1 single-purpose agents: semantics live
  in tools, behavior in a small static block);
- **re-visit triggers** — the concrete changes that reopen this phase:
  a new client with different policies, process variants exceeding ~5,
  the static instruction block crossing its token budget, or a capability
  addition that is procedural by nature (via spec re-entry first).

## Decision: author

Only the capabilities the test flagged. Proceed to
`references/authoring-guide.md`. Never author "while we're at it" skills for
capabilities the test cleared.
```

- [ ] **Step 2: Commit**

```bash
git add skills/skills/references/entry-test.md
git commit -m "feat(skills): entry test reference (per-capability table, none-is-success, re-visit triggers)"
```

---

### Task 3: Authoring guide

**Files:**
- Create: `skills/skills/references/authoring-guide.md`

- [ ] **Step 1: Write the guide**

Write `skills/skills/references/authoring-guide.md`:

```markdown
# Authoring guide — agent-cycle:skills

Only reached when the entry test flagged capabilities. Per skill, in order:

## Step 1 — EDD first

Before the skill's SKILL.md exists, write its eval cases: at least one
trigger-positive (a realistic task phrase that MUST route here), one
trigger-negative (an adjacent phrase that must NOT), one execution case
(input → expected procedure outcome). Store them next to the skill
(`<skill>/evals/cases.json`, same schema family as this plugin's own).

## Step 2 — Description as routing

The description is the routing algorithm — the only thing the router sees:
- WHAT it does (one clause), WHEN to use (concrete trigger phrases, the
  task-type vocabulary users actually say), when NOT to use (the adjacent
  cases that belong elsewhere).
- One skill = one job. If the description needs "and", split it.
- Ban "helpful skill for...", vendor prefixes, and vague nouns (utils/helper).

## Step 3 — Body and disclosure

Body carries the procedure only — steps, decision points, failure handling.
Depth goes to references the skill loads only when needed (progressive
disclosure). Smells: a body over ~500 lines; an ever-growing edge-case
section; content two teams could own; anything the STATIC instructions
already say (duplication drifts).

## Step 4 — Runtime binding

Declare in docs/agent/skills.md HOW this agent loads skills:
- **Harness-native** (Claude Code-class): folder discovery, description-based
  routing by the harness itself.
- **Custom loader** (built agents, e.g. a Pydantic AI service): the build's
  router/classifier selects by task type and injects the skill body into
  context for that turn only. If the build has no such mechanism, adding one
  is a BUILD change (re-entry to build), not something this phase improvises.

## Step 5 — Trigger accuracy

Target >=90%. Measure: at least 5 paraphrase variants per skill (include the
user's real language(s)), routed with ALL skills co-loaded; record hits and
misses per skill. Under 90% → sharpen the description (front-load trigger
vocabulary, tighten when-NOT), re-run fresh.

## Step 6 — Co-loaded regression

Never evaluate in isolation. Production loads every skill's metadata every
turn: run the full trigger suite and the agent's OWN eval suite (the phase-3
runner) with all skills present. A skill that degrades unrelated turns
(token budget, routing collisions) fails regression even if it works alone.

## Step 7 — Authority ladder

Every skill enters at **draft** (advisory: procedure available, no new
privileges). Promotion to **action-allowed** (the skill's procedure includes
gated/destructive actions) requires: pass^k on its execution cases at the
tier the actions demand + explicit human approval, recorded per skill in
docs/agent/skills.md. Skills never expand the TOOL surface — tools are the
spec's; a skill teaches procedure over existing tools.

## Step 8 — Record and gate

docs/agent/skills.md: frontmatter (agent_name, version, status: draft, date,
spec_version, build_version), the entry-test table, per-skill: description,
eval results (trigger %, execution, regression), ladder status. Human gate →
status: approved. Hand off: "/ship audits this record; the agent's eval suite
now runs with skills co-loaded."
```

- [ ] **Step 2: Commit**

```bash
git add skills/skills/references/authoring-guide.md
git commit -m "feat(skills): authoring guide (EDD-first, routing descriptions, co-loaded regression, ladder)"
```

---

### Task 4: SKILL.md

**Files:**
- Create: `skills/skills/SKILL.md`

- [ ] **Step 1: Write the skill**

Write `skills/skills/SKILL.md`:

```markdown
---
name: skills
description: "Phase 5 of the agent-cycle pipeline (conditional): decide whether the TARGET agent needs skills — on-demand procedural know-how — and author them EDD-first when warranted. Entry test per capability; 'no skills needed' is a recorded, successful outcome. Use when the user asks whether/which skills the pipelined agent needs — 'does the agent need skills', 'skills phase', 'siguiente fase del pipeline' after build. Do NOT use without approved design+spec+build, nor for authoring Claude Code skills outside the pipeline (that is skill-creator territory), nor for the agent's TOOLS (spec's domain)."
---

# agent-cycle:skills — Procedural Know-How, If Warranted

The burden of proof is on ADDING a skill, never on skipping it. Badly built
skills subtract capability; a clean "none" is a success.

## Hard rules

1. GATE: design.md + spec.md + docs/agent/build.md all approved, version
   chain consistent. Stale → re-entry, not a skills pass.
2. ENTRY TEST FIRST, per capability, table recorded (capability → verdict →
   reason). A bare conclusion — either way — fails the phase.
3. Skills only for on-demand procedural know-how (task-scoped, case/client-
   variant, static-bloating). Global context stays in static instructions;
   actions stay in the spec's tools. Skills never expand the tool surface.
4. "None" is a successful outcome: record why + concrete re-visit triggers.
   Zero ceremony skills.
5. Per authored skill: EDD first (trigger pos/neg + execution cases before
   its SKILL.md); description = routing (what/when/when-NOT, one job).
6. Trigger accuracy >=90%, measured with >=5 paraphrases per skill, ALL
   skills co-loaded. Regression runs the agent's own eval suite with skills
   present — a skill that degrades unrelated turns fails.
7. Authority ladder: every skill enters draft; action-allowed needs pass^k on
   its execution cases + explicit human approval, recorded per skill.
8. Runtime binding declared (harness-native or the build's loader). A missing
   loader is a build re-entry, never improvised here.
9. Writes: the target agent's skill folders + docs/agent/skills.md. status:
   draft until the explicit human gate. Never self-approve.

## Workflow

1. Read `references/entry-test.md`; run the test per capability; record the
   table.
2. Decision none → write skills.md (table, why, re-visit triggers) → gate.
3. Decision author → `references/authoring-guide.md` steps 1-8 for ONLY the
   flagged capabilities → skills.md with per-skill eval results and ladder
   status → gate.
4. Explicit approval → status: approved. Hand off: "/ship audits this record."

## Failure modes to avoid

- Skipping the per-capability table because the answer is obvious (rule 2).
- Ceremony skills authored to look thorough (rule 4).
- A skill whose description needs 'and', or that duplicates static
  instructions (rules 3, 5).
- Trigger accuracy asserted, not measured; or measured one-skill-at-a-time
  (rule 6).
- An action-allowed skill without pass^k + human approval (rule 7).
- Improvising a skill loader the build never implemented (rule 8).
```

- [ ] **Step 2: Verify frontmatter**

Run: `head -4 skills/skills/SKILL.md`
Expected: `---`, `name: skills`, description present.

- [ ] **Step 3: Commit**

```bash
git add skills/skills/SKILL.md
git commit -m "feat(skills): SKILL.md — entry test first, none-is-success, EDD-per-skill, ladder"
```

---

### Task 5: Release v0.6.0

- [ ] **Step 1:** plugin.json version → `0.6.0`.
- [ ] **Step 2:** README status line → `**Status:** v0.6.0 — phases 1-5 (\`design\` \`spec\` \`evals\` \`build\` \`skills\`) + \`economics\`.\nBuilt skill-by-skill, each dogfooded on a real agent before the next begins.`
- [ ] **Step 3:** CHANGELOG entry before `## [0.5.0]`:

```markdown
## [0.6.0] — 2026-07-28

### Added
- **`skills` skill** (phase 5 of 7, conditional): entry test per capability
  (procedural on-demand vs tool+static), "none" as a recorded successful
  outcome with re-visit triggers, EDD-first authoring for warranted skills
  (routing-grade descriptions, >=90% measured trigger accuracy, co-loaded
  regression against the agent's own eval suite), draft→action authority
  ladder (pass^k + human approval), declared runtime binding (harness-native
  or build's loader — never improvised). Artifact: docs/agent/skills.md.
- EDD eval suite (`skills/skills/evals/`): SKL-E01 positive-none (real
  dogfood expectation), SKL-E02 positive-authored (7-check contract),
  SKL-E03 gate-negative (two branches), SKL-E04 trigger-negative (generic
  skill authoring must not fire).

### Pending graduation
- `skills` skill run against the real agent — tag `skills-v0.1` when the
  dogfood passes (expected outcome: decision none, justified).
```

- [ ] **Step 4:** Verify version prints `0.6.0`; commit `chore: release v0.6.0 (skills skill)`.

---

### Task 6 (Alan, interactive): eval runs + dogfood

- [ ] SKL-E03 ×2, SKL-E04 in scratch; SKL-E02 with the hand-written variant-rich fixture → rows in results.md.
- [ ] SKL-E01 dogfood in `C:\Proyectos\Whatsapp_agent` (post-build): expected decision none with the per-capability table → tag `skills-v0.1`.
- [ ] Marketplace update + reinstall for v0.6.0.

---

## Self-review (done at planning time)

- **§4.5 coverage:** entry test ✓ (per-capability, first-yes-decides); no-ceremony/19% stance ✓ (rules 2/4); EDD-per-skill ✓; description-as-routing + when-NOT ✓; ≥90% trigger + co-loaded regression ✓ (rule 6, guide steps 5-6); draft→action ladder with pass^k + human ✓ (rule 7); tools-vs-skills boundary ✓ (rule 3: skills never expand tool surface — spec owns tools).
- **Gate position:** phase 5 follows build in the design doc's pipeline; gate requires build.md so trigger/regression runs can use the real runner and co-loaded context. SKL-E01 dogfood depends on BLD-E01 having run — sequencing noted in Task 6.
- **Cross-skill:** frontmatter chain extends (spec_version + build_version); gate/status semantics identical; SKL-E04 disambiguates against skill-creator the way ECO-E04 did against claude-api.
- **Check counts:** E01=5, E02=7, E03=2, E04=2 — match cases.json.
```
