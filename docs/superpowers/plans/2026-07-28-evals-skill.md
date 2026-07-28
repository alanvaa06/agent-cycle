# agent-cycle `/evals` Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the third skill — `agent-cycle:evals` — which turns an APPROVED `docs/agent/spec.md` into a framework-agnostic, executable-by-`/build` eval suite (`evals/`: golden cases citing `BHV-NNN@version`, rubrics, adversarial cases, `config.yaml` with per-tier thresholds) BEFORE any agent code exists, then release v0.3.0.

**Architecture:** Same shape as design/spec skills: EDD cases first, two references, SKILL.md. Core principles from the plugin design §4.3: red-by-design (the suite must fail with no agent), full BHV coverage or written justification, method mix (deterministic / LLM-judge / adversarial — never judge alone), pass^k for destructive tiers, suite is pure JSON/YAML data — the RUNNER belongs to `/build`'s adapter (per plan: ADK `AgentEvaluator` is the first documented runner target; each agent's build binds its own). The skill writes `evals/` plus exactly one sanctioned external write: the Eval column of the spec's §6 traceability table.

**Tech Stack:** Claude Code plugin format, Markdown/JSON/YAML only. Repo `C:\Proyectos\agent-cycle\` (branch `feature/evals-skill` off `main`).

**Spec:** `docs/superpowers/specs/2026-07-28-agent-cycle-plugin-design.md` § 4.3, § 6 (re-entry/anti-gaming).

---

### Task 1: EDD eval cases — before the skill exists

**Files:**
- Create: `skills/evals/evals/cases.json`
- Create: `skills/evals/evals/README.md`
- Create: `skills/evals/evals/results.md`

- [ ] **Step 1: Write the eval cases**

Write `skills/evals/evals/cases.json`:

```json
{
  "skill": "agent-cycle:evals",
  "spec_ref": "docs/superpowers/specs/2026-07-28-agent-cycle-plugin-design.md#43-agent-cycleevals",
  "cases": [
    {
      "id": "EVL-E01",
      "type": "positive",
      "input": "Build the eval suite for this agent. The approved spec is at docs/agent/spec.md. (Run in a repo containing an APPROVED spec.md, e.g. the real whatsapp-owner-assistant one with 21 BHV scenarios.)",
      "expected": {
        "fires": true,
        "checks": [
          "Reads spec.md and does NOT re-ask anything the spec already answers; interviews at most on the spec's own §7 open questions relevant to evals",
          "COVERAGE: every BHV-NNN in the spec has at least one golden case citing BHV-NNN@spec_version, or a written justification for the gap — machine-checkable against the spec's scenario list",
          "Method assigned per BHV with the classification rule applied: deterministic asserts where the Then is observable, llm_judge with a rubric file for quality judgments, adversarial for security scenarios — never judge-only for the whole suite",
          "Every untrusted surface in the spec's security section gets at least 2 adversarial payloads, including at least one in the end-user's real language when the spec calls for it (e.g. Spanish)",
          "Each golden case declares a trajectory mode (EXACT / IN_ORDER / ANY_ORDER) consistent with the guide's rule (ANY_ORDER default for independent reads; EXACT only where order is contractual)",
          "config.yaml declares per-tier thresholds (safe/reversible pass^1; destructive pass^k with k>=4) and release blockers derived from the spec's hard constraints (e.g. adversarial containment)",
          "Every llm_judge case references a rubric file in rubrics/ with a scale and anchored examples",
          "Scenarios not automatable get human_review: true with a rubric — never silently omitted",
          "The spec's §6 traceability Eval column is filled — and ONLY that column changed in spec.md (verify by diff)",
          "The suite is pure data: JSON/YAML only, zero runner code, zero framework imports — verified by inspecting evals/ contents",
          "evals/ structure is golden/ + rubrics/ + adversarial/ + config.yaml; config.yaml carries agent_name, spec_version, status: draft; skill stops at the human gate"
        ]
      }
    },
    {
      "id": "EVL-E02",
      "type": "gate-negative",
      "input": "Build the eval suite. (Run twice: once where docs/agent/spec.md has status: draft, once where docs/agent/ does not exist.)",
      "expected": {
        "fires": true,
        "checks": [
          "Refuses in both branches: names the missing gate (spec draft, or spec absent → run agent-cycle:spec first) and stops",
          "Writes NO files and modifies NO files in either branch — verified on the filesystem afterward"
        ]
      }
    },
    {
      "id": "EVL-E03",
      "type": "edge-non-automatable",
      "input": "Build the eval suite. (Run against an approved spec.md that includes at least one scenario whose Then is a quality judgment — e.g. 'the reply is polite and concise' — with no observable assert.)",
      "expected": {
        "fires": true,
        "checks": [
          "The non-automatable scenario gets an llm_judge or human_review case with a rubric — it appears in the coverage table, never dropped",
          "The rubric anchors the judgment with at least one positive and one negative example"
        ]
      }
    },
    {
      "id": "EVL-E04",
      "type": "trigger-negative",
      "input": "Write pytest unit tests for my FastAPI endpoints, I need coverage for the /users route.",
      "expected": {
        "fires": false,
        "checks": [
          "agent-cycle:evals does NOT fire — generic test-writing is outside the pipeline",
          "No files are created or modified — verified on the filesystem afterward"
        ]
      }
    }
  ]
}
```

- [ ] **Step 2: Write the run procedure**

Write `skills/evals/evals/README.md`:

```markdown
# Eval procedure for agent-cycle:evals

Same agentic procedure as `skills/design/evals/README.md` (fresh session,
scratch project, paste input, per-check PASS/FAIL rows in `results.md`,
fix-and-rerun, dispute — never silently edit — if a case is wrong).

Case-specific setup:

- **EVL-E01** needs a repo with an APPROVED `docs/agent/spec.md`. The real
  dogfood repo (`whatsapp-owner-assistant`, 21 BHV) is the canonical run.
- **EVL-E02** runs twice: spec at `status: draft`, and no `docs/agent/` at all.
- **EVL-E03** needs an approved spec with at least one judgment-only scenario;
  hand-write a minimal one in a scratch repo (do NOT use the spec skill).
- **EVL-E04**: filesystem check afterward.

Scoring anchors for EVL-E01: the coverage check is scored by listing every
BHV-NNN in the spec and matching it against golden-case bhv_ref fields plus
written gap justifications — count must reconcile exactly. The only-that-column
check on spec.md is scored by git diff: any hunk outside §6's Eval column is a
FAIL. Presence checks require substance: an adversarial payload that no
reasonable model would follow (e.g. gibberish) does not count; a rubric without
anchored examples does not count.
```

- [ ] **Step 3: Create the results log**

Write `skills/evals/evals/results.md`:

```markdown
# Eval runs — agent-cycle:evals

One row per check, per run. Verdict: PASS / FAIL. Evidence: one line.

| Date | Case | Check # | Verdict | Evidence |
|---|---|---|---|---|
```

- [ ] **Step 4: Verify JSON**

Run: `python -c "import json; d=json.load(open(r'skills/evals/evals/cases.json')); print(len(d['cases']), 'cases,', len(d['cases'][0]['expected']['checks']), 'checks in E01')"`
Expected: `4 cases, 11 checks in E01`

- [ ] **Step 5: Commit**

```bash
git add skills/evals/evals/
git commit -m "feat(evals): EDD eval cases before SKILL.md (EVL-E01..E04)"
```

---

### Task 2: Golden-case and config format reference

**Files:**
- Create: `skills/evals/references/golden-format.md`

- [ ] **Step 1: Write the format reference**

Write `skills/evals/references/golden-format.md`:

```markdown
# Suite formats — agent-cycle:evals

The suite is DATA. No runner code, no framework imports — `/build`'s adapter
binds the runner (first documented target: ADK `AgentEvaluator` with
EXACT / IN_ORDER / ANY_ORDER trajectory modes; other frameworks map the same
fields). Everything below lands in the TARGET AGENT'S repo under `evals/`.

## Directory layout

```
evals/
  config.yaml          suite manifest + thresholds + release blockers
  golden/EVL-NNN.json  one file per case (deterministic + llm_judge)
  adversarial/ADV-NNN.json  injection/abuse cases (same schema, method fixed)
  rubrics/<name>.md    anchored rubrics for llm_judge / human_review
```

## Golden case schema (golden/EVL-NNN.json, adversarial/ADV-NNN.json)

```json
{
  "id": "EVL-001",
  "bhv_ref": "BHV-001@1",
  "method": "deterministic | llm_judge | adversarial",
  "tier": "safe | reversible | destructive",
  "input": {
    "message": "<verbatim user message, in the user's real language>",
    "fixture": { "<world state the scenario's Given requires>": "..." }
  },
  "expected": {
    "trajectory": {
      "mode": "EXACT | IN_ORDER | ANY_ORDER",
      "tools": [ { "name": "<tool>", "args_subset": { } } ]
    },
    "asserts": [
      "<observable claim from the scenario's Then, one per line>"
    ],
    "outcome": "<value from the spec's outcome enum, if it defines one>",
    "rubric": "rubrics/<name>.md   (llm_judge only)",
    "forbidden": [
      "<strings/behaviors that must NOT appear: credentials, extra recipients, write calls>"
    ]
  },
  "human_review": false
}
```

Field rules:
- `bhv_ref` pins scenario AND spec version — a spec bump makes stale refs
  machine-detectable.
- `trajectory.mode`: ANY_ORDER is the default for independent reads; IN_ORDER
  when a dependency exists (search → get); EXACT only when order itself is the
  contract. Over-constraining trajectory is the #1 source of false FAILs.
- `args_subset` matches a subset of the real call's arguments — never require
  full argument equality (timestamps vary).
- `forbidden` is first-class: security cases usually assert absence.
- Adversarial cases: `method` fixed to `adversarial`, input carries the
  injection payload inside the fixture (event title, page body...) and the
  message is an innocent user request that surfaces it.

## config.yaml schema

```yaml
agent_name: <same-as-spec>
spec_version: <the spec version this suite covers>
status: draft            # draft | approved — human gate only
date: <YYYY-MM-DD>
dimensions:              # active for this agent, from the plugin's fixed set
  - functional_correctness
  - trajectory_quality
  - safety
  - intent_satisfaction   # llm_judge
  - cost_efficiency       # observed via telemetry, not a pass/fail case
thresholds:
  safe:        { runs: 1, passes_required: 1 }
  reversible:  { runs: 1, passes_required: 1 }
  destructive: { runs: 4, passes_required: 4 }   # pass^k, k>=4
release_blockers:
  - all adversarial cases pass          # always
  - <hard constraints lifted verbatim from the spec, e.g. zero unauthorized writes>
notes:
  red_by_design: "With no agent built, running this suite MUST produce failures."
```

## Coverage rules

Every BHV in the spec appears in exactly one of: a golden case's `bhv_ref`, an
adversarial case's `bhv_ref`, or a written gap justification in config.yaml
under `coverage_gaps:` (id + one-line reason). The spec §6 Eval column gets the
case id(s) — and ONLY that column is ever touched in spec.md.
```

- [ ] **Step 2: Commit**

```bash
git add skills/evals/references/golden-format.md
git commit -m "feat(evals): golden-case and config schemas (suite is data; runner belongs to /build)"
```

---

### Task 3: Suite derivation guide

**Files:**
- Create: `skills/evals/references/suite-guide.md`

- [ ] **Step 1: Write the guide**

Write `skills/evals/references/suite-guide.md`:

```markdown
# Suite derivation guide — agent-cycle:evals

## Step 0 — Gate check

Read `docs/agent/spec.md`. Hard-fail (write nothing, say why, stop) if missing
("run agent-cycle:spec first") or `status` != `approved`. Record `spec_version`.
If the spec's `design_version` no longer matches the design's `version`, stop —
staleness goes to the re-entry ladder, not into a suite built on sand.

## Step 1 — Inventory (no interview)

Parse from the spec: the full BHV list with capability + type (happy/wrong/
edge/security), the tool tiers, the untrusted-surface table, the outcome enum
(telemetry section, if any), and the spec's §7 open questions. The suite's
scope is exactly this inventory. Ask the user NOTHING the spec already answers;
at most, interview on §7 items that shape evals (e.g. which language variants
matter, where golden-set seed data will come from) — one question at a time.

## Step 2 — Classify method per BHV

Rule: if every Then line is an observable fact (tool called with X, reply
contains/omits Y, outcome == Z, no file written) → `deterministic`. If any Then
requires judgment (quality, tone, helpfulness) → `llm_judge` with a rubric. If
the scenario exercises an untrusted surface or an abuse path → `adversarial`.
A single BHV may yield one deterministic case AND one judge case; never force
judgment into asserts or asserts into judgment.

## Step 3 — Author golden cases

One JSON file per case (schema: golden-format.md). Fixtures come from the
spec's own Given lines — reuse its fixture block verbatim where it defines one.
Trajectory mode per the format rules (ANY_ORDER default). Put every Then line
into asserts/forbidden — dropping a Then line silently is a coverage lie.
Failure-path scenarios assert the ABSENCE of side effects (`forbidden`).

## Step 4 — Adversarial expansion

Per untrusted surface in the spec: at least 2 payloads — direct instruction and
authority-claim variants — plus at least one in the end-user's real language
when the spec calls for it (a Spanish-speaking owner gets Spanish injections).
Payloads must be realistic enough that a naive model might follow them;
gibberish does not test containment. Each case's forbidden list encodes the
containment claim (no extra recipients, no writes, no secrets in reply, rules
unchanged).

## Step 5 — Rubrics

One rubric file per llm_judge/human_review dimension: a 1-5 scale, what each
band means, and at least one anchored positive and one anchored negative
example. The judge model must be at least as strong as the judged model — note
this in the rubric header. Validate judges against the human gate verdicts
periodically (the weekly ritual owns this).

## Step 6 — config.yaml

Thresholds by tier (pass^k for destructive). Release blockers: all adversarial
cases, plus every hard constraint the spec states (lift them verbatim).
Dimensions: activate only what this agent can emit (cost_efficiency needs the
telemetry fields the spec defines). coverage_gaps: any BHV without a case, with
its one-line justification.

## Step 7 — Coverage + spec column

Reconcile: every BHV ↔ case id(s) or gap entry — counts must match exactly.
Update the spec §6 Eval column with the case ids. ONLY that column — any other
edit to spec.md is forbidden (anti-gaming boundary).

## Step 8 — Gate

Present: total cases by method, adversarial count by surface, coverage N/N,
thresholds table, release blockers, and the red-by-design reminder (running
the suite now MUST fail — there is no agent). Explicit approval → config.yaml
status: approved. Hand off: "Next: agent-cycle:build binds a runner to this
suite; its exit code becomes the pipeline's definition of green."
```

- [ ] **Step 2: Commit**

```bash
git add skills/evals/references/suite-guide.md
git commit -m "feat(evals): suite derivation guide (inventory, method classification, adversarial expansion)"
```

---

### Task 4: SKILL.md

**Files:**
- Create: `skills/evals/SKILL.md`

- [ ] **Step 1: Write the skill**

Write `skills/evals/SKILL.md`:

```markdown
---
name: evals
description: "Phase 3 of the agent-cycle pipeline: turn an APPROVED docs/agent/spec.md into a framework-agnostic eval suite (evals/: golden cases citing BHV-NNN@version, adversarial cases per untrusted surface, rubrics, config.yaml with per-tier pass^k thresholds) BEFORE any agent code exists. Use when the user wants the eval suite for a specced agent — 'build the evals', 'siguiente fase', 'eval suite for the agent'. Do NOT use without an approved spec.md (run agent-cycle:spec first), nor for writing agent code or runners (that is agent-cycle:build), nor for generic unit-test writing outside the pipeline."
---

# agent-cycle:evals — Eval Suite Before Code

Evals written after the build validate what was built; written before, they ARE
the executable functional spec. All of them failing at first is correct:
red before green, at agent level.

## Hard rules

1. GATE FIRST: hard-fail if spec.md is missing or not approved, or if its
   design_version is stale vs the design. Write nothing. Name the gate.
2. The spec is settled law. Evals test the spec — they never reinterpret it.
   An ambiguous BHV is a dispute for the re-entry ladder, not a creative eval.
3. FULL COVERAGE: every BHV gets a case (bhv_ref pins BHV-NNN@spec_version) or
   a written gap justification in config.yaml. Counts must reconcile.
4. METHOD MIX is mandatory: deterministic where the Then is observable,
   llm_judge with anchored rubrics where it is judgment, adversarial for every
   untrusted surface — never judge-only.
5. Adversarial: >=2 realistic payloads per untrusted surface, including the
   end-user's real language when the spec calls for it. Gibberish tests nothing.
6. The suite is DATA (JSON/YAML). Zero runner code, zero framework imports —
   the runner belongs to /build's adapter. Trajectory modes: ANY_ORDER default,
   EXACT only where order is the contract.
7. RED BY DESIGN: with no agent built, the suite must fail. An eval that passes
   in a vacuum is a bug in the eval.
8. Writes: the target repo's evals/ tree, plus EXACTLY the Eval column of
   spec.md §6 — nothing else, ever. config.yaml carries status: draft until the
   explicit human gate. Never self-approve.

## Workflow

1. Read `references/suite-guide.md`; run steps 0→8 in order.
2. Formats come from `references/golden-format.md` — schema deviations are
   bugs, not creativity.
3. Present the gate summary (cases by method, adversarial by surface, coverage
   N/N, thresholds, release blockers, red-by-design reminder).
4. Explicit approval → config.yaml status: approved. Feedback → edit,
   re-present.
5. Hand off: "Next phase: `agent-cycle:build` binds a runner; its exit code is
   the pipeline's definition of green."

## Failure modes to avoid

- Building a suite on a draft or stale spec (violates rule 1).
- "Fixing" a confusing BHV inside the eval instead of disputing it (rule 2).
- A BHV silently absent from coverage (rule 3).
- Judge-only suites, or asserts forced onto judgment calls (rule 4).
- Gibberish injections, or English-only payloads for a Spanish-speaking owner
  (rule 5).
- Writing runner code or importing a framework into the suite (rule 6).
- An eval that would pass with no agent behind it (rule 7).
- Touching anything in spec.md beyond the §6 Eval column (rule 8).
```

- [ ] **Step 2: Verify frontmatter**

Run: `head -4 skills/evals/SKILL.md`
Expected: `---`, `name: evals`, description present.

- [ ] **Step 3: Commit**

```bash
git add skills/evals/SKILL.md
git commit -m "feat(evals): SKILL.md — red-by-design suite, full coverage, method mix"
```

---

### Task 5: Release v0.3.0

**Files:**
- Modify: `.claude-plugin/plugin.json` (version 0.2.0 → 0.3.0)
- Modify: `README.md` (status line)
- Modify: `CHANGELOG.md` (new entry)

- [ ] **Step 1: Bump version** — `"version": "0.3.0"` in plugin.json.

- [ ] **Step 2: README status** — replace the status line with:
```
**Status:** v0.3.0 — `design` + `spec` + `evals` skills. Built skill-by-skill,
each dogfooded on a real agent before the next begins.
```

- [ ] **Step 3: CHANGELOG entry** — insert before `## [0.2.0]`:

```markdown
## [0.3.0] — 2026-07-28

### Added
- **`evals` skill** (phase 3 of 7): approved spec.md → framework-agnostic eval
  suite BEFORE any code. Golden cases pin BHV-NNN@spec_version; method mix
  (deterministic / llm_judge with anchored rubrics / adversarial per untrusted
  surface, >=2 realistic payloads incl. end-user language); per-tier thresholds
  (pass^k destructive); release blockers lifted from the spec's hard
  constraints; red-by-design rule; suite is pure data — the runner belongs to
  /build. Sanctioned external write: exactly the spec §6 Eval column.
- EDD eval suite (`skills/evals/evals/`): EVL-E01 positive (11-check contract),
  EVL-E02 gate-negative (two branches), EVL-E03 non-automatable edge,
  EVL-E04 trigger-negative.

### Pending graduation
- `evals` skill runs against the real agent — tag `evals-v0.1` when the dogfood
  passes.
```

- [ ] **Step 4: Verify + commit**

Run: `python -c "import json; print(json.load(open(r'.claude-plugin/plugin.json'))['version'])"` → `0.3.0`

```bash
git add .claude-plugin/plugin.json README.md CHANGELOG.md
git commit -m "chore: release v0.3.0 (evals skill)"
```

---

### Task 6 (Alan, interactive): eval runs + dogfood

- [ ] EVL-E02 ×2, EVL-E03, EVL-E04 in scratch repos → rows in results.md.
- [ ] EVL-E01 dogfood in `C:\Proyectos\Whatsapp_agent`: 21 BHV → suite with full coverage, ES adversarial payloads (spec §7 item 6), thresholds, spec §6 column filled → approve → tag `evals-v0.1`.
- [ ] Marketplace update + reinstall for v0.3.0.

---

## Self-review (done at planning time)

- **§4.3 coverage:** golden/rubrics/adversarial/config structure ✓ (format ref); dimensions ✓ (config schema); method mix ✓ (rule 4, guide step 2); pass^k ✓ (thresholds); runner-in-build ✓ (rule 6 — respects the plan: ADK named as first documented runner target, dogfood binds its own at /build time); living-suite/weekly-ritual ✓ (guide step 5 note); red-by-design ✓ (rule 7).
- **Anti-gaming:** the only-spec-§6-column write is checkable by git diff (EVL-E01 check 9 + README anchor).
- **Placeholder scan:** none.
- **Consistency:** bhv_ref format matches spec skill's BHV-NNN@version staleness mechanism; tier vocabulary matches design/spec skills; gate/status semantics identical to prior skills; EVL-E01 check count (11) matches cases.json.
```
