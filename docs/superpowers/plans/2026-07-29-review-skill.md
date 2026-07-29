# agent-cycle `/review` Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship transversal 3 — `agent-cycle:review` — the assessment of ANY existing agent (pipeline-born or foreign) against the pipeline's practice frame: eight dimensions, findings with severity + the pipeline route that would fix each, evidence as file:line or explicit "not found". The agency front door: a client's existing bot goes in, a remediation map that doubles as a pipeline proposal comes out. Then release v0.10.0.

**Architecture:** Same shape (EDD cases → two references → SKILL.md). Per design doc §5.3 (added 2026-07-29, explicit owner decision): the ONLY skill with no chain gate — the target is an arbitrary agent; the gate is merely a readable target. Read-only on the reviewed agent; the only write is `docs/agent/review.md` (or a user-directed path for foreign repos). Eight dimensions always — n/a needs a reason. Self-contained audit frame (the distilled successor of the owner's personal agent-design knowledge skill — no workspace reference, per the v0.4.1 lesson). Does NOT replace `/ship` (release audit with live re-run) nor generic code review.

**Tech Stack:** Claude Code plugin format, Markdown/JSON only.

**Spec:** `docs/superpowers/specs/2026-07-28-agent-cycle-plugin-design.md` § 5.3.

---

### Task 1: EDD eval cases — before the skill exists

**Files:**
- Create: `skills/review/evals/cases.json`
- Create: `skills/review/evals/README.md`
- Create: `skills/review/evals/results.md`

- [ ] **Step 1: Write the eval cases**

Write `skills/review/evals/cases.json`:

```json
{
  "skill": "agent-cycle:review",
  "spec_ref": "docs/superpowers/specs/2026-07-28-agent-cycle-plugin-design.md#53-agent-cyclereview-added-2026-07-29--explicit-owner-decision",
  "cases": [
    {
      "id": "REV-E01",
      "type": "positive-foreign",
      "input": "Review this agent — here's the repo. (Run against a FOREIGN agent codebase with no pipeline artifacts: e.g. any open-source bot/orchestration repo, or a hand-written scratch agent with a main loop, a couple of tools, and a README.)",
      "expected": {
        "fires": true,
        "checks": [
          "Gate: a readable target exists (repo/paths/docs identified); no pipeline artifacts are required — this is the one chain-gate-free skill",
          "ALL EIGHT dimensions assessed — specification, contracts & tools, security, loop & harness, evals, observability, economics, ops — each with a verdict (ok / findings / n-a with a stated reason); never a silent subset",
          "Every code-level claim carries file:line evidence; every absence is an explicit 'not found' — architecture is never invented or assumed from genre conventions",
          "Every finding carries a severity (critical / important / minor) AND its pipeline route — which agent-cycle phase would fix it — so the review doubles as a remediation map / entry funnel",
          "The performance-metric dimension applies the environment-not-activity standard and runs a Goodhart probe when any metric exists; 'no success metric found' is itself a finding routed to design",
          "Untrusted surfaces are enumerated from the agent's REAL inputs (its actual channels, retrieved content, third-party text) — not a generic checklist pasted in",
          "Read-only on the reviewed agent: nothing in the target is modified; the only write is the review report (docs/agent/review.md or the user-directed path)",
          "Report carries frontmatter (agent_name or target id, version, status: draft, date, reviewed_commit when git is available) plus an executive summary with the top findings; skill stops at the human gate"
        ]
      }
    },
    {
      "id": "REV-E02",
      "type": "positive-pipeline-born",
      "input": "Review this agent. (Run in a repo that HAS pipeline artifacts — approved design/spec/evals — plus agent source, e.g. the real whatsapp-owner-assistant post-build or a fixture.)",
      "expected": {
        "fires": true,
        "checks": [
          "Artifact-vs-code consistency is assessed: where the code diverges from the approved spec (tool present in code but not in spec, cap value drifted, tier not enforced) each divergence is a finding routed via the re-entry ladder",
          "The review states explicitly that it does NOT re-run the eval suite and does NOT replace agent-cycle:ship — the release audit belongs to ship",
          "Pipeline artifacts are used as the comparison baseline, not re-derived; the eight dimensions still all appear (many will be 'ok — covered by <artifact>')"
        ]
      }
    },
    {
      "id": "REV-E03",
      "type": "gate-negative",
      "input": "Review this agent. (Run with no identifiable target: an empty directory, or no repo/path/docs given and none findable.)",
      "expected": {
        "fires": true,
        "checks": [
          "Refuses: states that no readable target was found and asks for the repo/path — writes nothing",
          "No files are created or modified — verified on the filesystem afterward"
        ]
      }
    },
    {
      "id": "REV-E04",
      "type": "trigger-negative",
      "input": "Review my REST API code for best practices — it's a FastAPI service with a Postgres repository layer, no LLM anywhere.",
      "expected": {
        "fires": false,
        "checks": [
          "agent-cycle:review does NOT fire — non-agent code review is generic code-review territory",
          "No files are created or modified — verified on the filesystem afterward"
        ]
      }
    }
  ]
}
```

- [ ] **Step 2: Write the run procedure**

Write `skills/review/evals/README.md`:

```markdown
# Eval procedure for agent-cycle:review

Same agentic procedure as `skills/design/evals/README.md` (fresh session,
per-check PASS/FAIL rows in `results.md`, fix-and-rerun, dispute — never
silently edit — if a case is wrong).

Case-specific setup:

- **REV-E01** needs a FOREIGN agent target. Cheapest realistic fixture: a
  scratch repo with a hand-written ~200-line agent (a loop calling an LLM,
  2-3 tools incl. one that writes somewhere, retrieved web/text content fed
  into prompts, a README claiming a success metric). Seed it with 3-4
  deliberate defects (e.g. untrusted content concatenated into the system
  prompt, no step cap, an activity metric, no evals) — the review must find
  them WITH file:line. ~30 min; do NOT use pipeline skills to author it.
- **REV-E02**: the real dogfood repo qualifies once build exists; pre-build,
  a fixture with approved design/spec/evals plus divergent source works
  (introduce one deliberate artifact-vs-code divergence).
- **REV-E03**: empty scratch dir; filesystem check afterward.
- **REV-E04**: filesystem check afterward.

Scoring anchors: the eight-dimensions check FAILS if any dimension is absent
from the report (n/a with a reason counts as present). The evidence check
FAILS on any code claim without file:line, and on any 'the agent probably...'
construction — probabilistic architecture is invented architecture. The
seeded defects in E01's fixture are the ground truth: each missed seeded
defect is a FAIL row for the relevant dimension.
```

- [ ] **Step 3: Create the results log**

Write `skills/review/evals/results.md`:

```markdown
# Eval runs — agent-cycle:review

One row per check, per run. Verdict: PASS / FAIL. Evidence: one line.

| Date | Case | Check # | Verdict | Evidence |
|---|---|---|---|---|
```

- [ ] **Step 4: Verify JSON**

Run: `python -c "import json; d=json.load(open(r'skills/review/evals/cases.json')); print(len(d['cases']), 'cases,', len(d['cases'][0]['expected']['checks']), 'checks in E01')"`
Expected: `4 cases, 8 checks in E01`

- [ ] **Step 5: Commit**

```bash
git add skills/review/evals/
git commit -m "feat(review): EDD eval cases before SKILL.md (REV-E01..E04)"
```

---

### Task 2: Audit frame reference

**Files:**
- Create: `skills/review/references/audit-frame.md`

- [ ] **Step 1: Write the reference**

Write `skills/review/references/audit-frame.md`:

```markdown
# Audit frame — agent-cycle:review

Eight dimensions. Each one: what to look for, the concrete probes, and the
pipeline phase that fixes its findings. Assess ALL eight; n/a needs a reason.
Evidence discipline: file:line for what exists, explicit "not found" for what
does not. Never infer architecture from genre conventions.

## 1. Specification → fixes route: agent-cycle:design

- Is there a stated purpose and a SUCCESS METRIC? Is the metric a property of
  the ENVIRONMENT (booked appointments, resolved requests) or of agent
  ACTIVITY (messages sent, tool calls)? Activity metrics are a finding.
- Goodhart probe on any metric found: if the agent optimized ONLY this, what
  is the worst way to hit the number? No counterweight → finding.
- Scope boundaries / NO-goals stated anywhere? Unbounded scope ("handle my
  inbox") is a license to be hijacked — finding, route design.

## 2. Contracts & tools → fixes route: agent-cycle:spec

- Tool interfaces: typed schemas with unknown-field rejection, or loose
  dicts? Docstrings written for the model (what/when/when-NOT), or
  implementation notes?
- Action tiers: are destructive/irreversible actions distinguishable from
  reads in the tool layer at all? Any write path without a tier concept →
  finding.
- Overlap: two tools a human cannot tell apart → routing errors — finding.
- Errors: raised into the loop (crash/retry chaos) or returned as
  observations?

## 3. Security → fixes route: agent-cycle:spec (posture) / agent-cycle:build (enforcement)

- Enumerate the REAL untrusted inputs: channels, retrieved documents/pages,
  third-party text, other agents. For each: does it reach the system prompt
  (finding: critical), or is it enveloped/quarantined?
- Least privilege: credential scopes vs what the code actually needs; one
  god-token → finding.
- Secrets: in code, in prompts, in logs? Approval gates: do dangerous actions
  ship with HITL, and are approvals per-action (cached approval = finding)?
- Extraction pattern: does untrusted content meet tool-bearing context
  directly, or is there a no-tools extraction boundary?

## 4. Loop & harness → fixes route: agent-cycle:build

- Caps: max steps, max tool calls, wall clock — in CODE or absent? Absent →
  finding (runaway loops are a cost and safety issue).
- Exits: explicit termination (answer / cap / unrecoverable error), or
  implicit "hope the model stops"?
- Topology: single agent unless a measurable reason exists; unexplained
  multi-agent → finding routed to design.
- State: durable sessions behind an interface, or in-memory only / coupled
  to one vendor store with no export path?

## 5. Evals → fixes route: agent-cycle:evals

- Do evals exist AT ALL beyond demo transcripts? None → finding (critical
  for anything with write actions): "an agent without evals is a hope."
- Coverage: behavior scenarios? adversarial/injection cases for each
  untrusted surface? Reliability: single-run or repeated (pass^k) for
  dangerous paths?
- Are they runnable (a runner, an exit code) or prose?

## 6. Observability → fixes route: agent-cycle:build (emit) / agent-cycle:ship (verify)

- Traces: any per-turn record of tool calls, outcomes, errors? Token
  counters emitted (cost calibration impossible without them)?
- Outcome taxonomy: can success/failure/refusal be told apart in telemetry,
  or does everything look like HTTP 200?

## 7. Economics → fixes route: agent-cycle:economics

- Is the monthly cost KNOWN (any model of tokens/infra/channel), or
  discovered on the invoice? No spend alarm → finding.
- Model tier chosen deliberately (cost/quality trade stated) or by default?

## 8. Ops → fixes route: agent-cycle:ship

- Kill switch: can the owner stop the agent NOW, documented? Rollback path?
- Queue/backlog handling documented? Any alarm wired to a human?
- Post-launch loop: does anything feed real failures back into tests/evals?

## Verdict discipline

Per dimension: ok / findings / n-a (+reason). Per finding: severity
(critical = exploitable or unbounded harm; important = will bite at scale or
on drift; minor = friction) + the pipeline route. The remediation map at the
end groups findings BY PHASE in pipeline order — that map is the proposal.
```

- [ ] **Step 2: Commit**

```bash
git add skills/review/references/audit-frame.md
git commit -m "feat(review): audit frame (8 dimensions, probes, pipeline routes, verdict discipline)"
```

---

### Task 3: Report template

**Files:**
- Create: `skills/review/references/report-template.md`

- [ ] **Step 1: Write the template**

Write `skills/review/references/report-template.md`:

```markdown
# review.md template

Written to `docs/agent/review.md` in the reviewed repo, or the user-directed
path for foreign targets. Read-only review: this file is the ONLY write.

---
agent_name: <name or target identifier>
version: 1
status: draft            # draft | approved — human gate only
date: <YYYY-MM-DD>
reviewed_commit: <git SHA when available, else "no-git">
pipeline_artifacts_present: <none | list>
---

# <Agent> — Review

## Executive summary

Three to six sentences: what this agent is (from evidence, not assumption),
its strongest aspect, the top findings by severity, and the one-line
bottom line. A non-technical client should understand this section alone.

## Dimension verdicts

| # | Dimension | Verdict | Findings | Fix route |
|---|---|---|---|---|
| 1 | Specification | ok / findings / n-a | <count or reason> | design |
| 2 | Contracts & tools | ... | ... | spec |
| 3 | Security | ... | ... | spec / build |
| 4 | Loop & harness | ... | ... | build |
| 5 | Evals | ... | ... | evals |
| 6 | Observability | ... | ... | build / ship |
| 7 | Economics | ... | ... | economics |
| 8 | Ops | ... | ... | ship |

## Findings

One block per finding, ordered by severity:

### <SEV-severity> <short title>
- **Evidence:** `<file:line>` — <what is there> · or **not found:** <what
  was looked for and where>
- **Why it matters:** <one or two sentences, concrete failure scenario>
- **Fix route:** agent-cycle:<phase> — <what that phase would produce>

## Remediation map (the proposal)

Findings grouped by phase, in pipeline order — this is the entry plan if the
owner adopts the cycle:

| Phase | Findings it resolves | What gets produced |
|---|---|---|
| design | ... | approved design.md with metric + NO-goals |
| spec | ... | tool contracts, tiers, security posture |
| evals | ... | runnable suite incl. adversarial cases |
| build | ... | caps, envelopes, telemetry, runner |
| economics | ... | cost model + spend alarm |
| ship | ... | release audit + runbook |

## Scope notes

- This review did not execute the agent or its tests; it is a static
  assessment with file:line evidence.
- It does not replace agent-cycle:ship (release audit with a live suite
  re-run) for pipeline-born agents.
- Reviewed at <reviewed_commit>; findings age as the code moves.
```

- [ ] **Step 2: Commit**

```bash
git add skills/review/references/report-template.md
git commit -m "feat(review): report template (executive summary, dimension verdicts, remediation map)"
```

---

### Task 4: SKILL.md

**Files:**
- Create: `skills/review/SKILL.md`

- [ ] **Step 1: Write the skill**

Write `skills/review/SKILL.md`:

```markdown
---
name: review
description: "Transversal skill of the agent-cycle pipeline: assess ANY existing AI agent — pipeline-born or foreign — against the pipeline's practice frame: eight dimensions (specification, contracts/tools, security, loop/harness, evals, observability, economics, ops), findings with severity + the pipeline phase that fixes each, evidence as file:line or explicit not-found. Produces docs/agent/review.md — a remediation map that doubles as the pipeline entry proposal. Use when the user asks to review/audit an existing agent, bot, or orchestration code — 'review this agent', 'audita este bot', 'revisa este código de orquestación'. The one agent-cycle skill needing NO pipeline artifacts. Do NOT use for non-agent code review (generic code-review territory), nor as the release audit of a pipeline-born agent (that is agent-cycle:ship), nor to fix anything (read-only)."
---

# agent-cycle:review — Any Agent, Assessed

The agency front door: an existing agent goes in, an evidence-backed
remediation map comes out — and the map is the pipeline proposal.

## Hard rules

1. GATE: a readable target (repo/paths/docs). Nothing else — this is the one
   chain-gate-free skill. No target findable → refuse, ask, write nothing.
2. READ-ONLY on the reviewed agent. The only write is the review report
   (docs/agent/review.md, or the user-directed path). Review reports; it
   never fixes, refactors, or "quickly patches".
3. ALL EIGHT dimensions, always — ok / findings / n-a with a stated reason.
   Never a silent subset. The frame lives in references/audit-frame.md and
   is self-contained: no external knowledge skill required.
4. EVIDENCE DISCIPLINE: every code claim carries file:line; every absence is
   an explicit "not found". Architecture is never invented from genre
   conventions — "the agent probably..." is a banned construction.
5. Every finding = severity (critical/important/minor) + pipeline route (the
   agent-cycle phase that fixes it). The remediation map grouped by phase IS
   the deliverable's spine.
6. Untrusted surfaces are enumerated from the agent's REAL inputs, not a
   pasted checklist. A metric found gets the environment-not-activity test
   and a Goodhart probe; no metric found is itself a design-routed finding.
7. Pipeline-born targets: artifacts are the comparison baseline (divergence
   = finding routed via re-entry); the review states it does NOT re-run the
   suite and does NOT replace agent-cycle:ship.
8. Report carries frontmatter (target, version, status: draft, date,
   reviewed_commit) and an executive summary a non-technical client can
   read. Approved only at the explicit human gate. Never self-approve.

## Workflow

1. Identify and read the target (gate). Note reviewed_commit.
2. Walk `references/audit-frame.md` — all eight dimensions, probes as
   listed, evidence as found.
3. Fill `references/report-template.md`: summary, verdict table, findings
   by severity, remediation map by phase, scope notes.
4. Write the report (the only write). Present: top findings + the map.
5. Explicit approval → status: approved. The map is the natural handoff:
   "adopting the cycle starts at the first phase in the map."

## Failure modes to avoid

- Reviewing without reading — genre-based assumptions (rule 4).
- A seven-dimension report because one "obviously" doesn't apply (rule 3).
- A finding without a route, or a route without a finding (rule 5).
- Fixing the one-line bug while in there (rule 2).
- Running it on a pipeline-born agent as if it were the release audit
  (rule 7 — that is ship's job).
- A security section that lists generic risks instead of THIS agent's
  actual input surfaces (rule 6).
```

- [ ] **Step 2: Verify frontmatter**

Run: `head -4 skills/review/SKILL.md`
Expected: `---`, `name: review`, description present.

- [ ] **Step 3: Commit**

```bash
git add skills/review/SKILL.md
git commit -m "feat(review): SKILL.md — any agent assessed, evidence discipline, remediation map as funnel"
```

---

### Task 5: Release v0.10.0

- [ ] **Step 1:** plugin.json version → `0.10.0`; also update the plugin description in BOTH `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` from "— plus economics and blueprint transversals." to "— plus economics, blueprint and review transversals." (keep the rest of the description identical).
- [ ] **Step 2:** README status line → `**Status:** v0.10.0 — all 7 phases + 3 transversals (\`economics\`, \`blueprint\`, \`review\`).\n10 skills. Built skill-by-skill, each dogfooded on a real agent.` AND add the review row to the README pipeline table after the blueprint row: `| — | \`agent-cycle:review\` (transversal) | \`docs/agent/review.md\` |`
- [ ] **Step 3:** CHANGELOG entry before `## [0.9.0]`:

```markdown
## [0.10.0] — 2026-07-29

### Added
- **`review` skill** (transversal 3 of 3 — added to the plan by explicit
  owner decision 2026-07-29): assess ANY existing agent, pipeline-born or
  foreign, against the pipeline's practice frame. Eight dimensions with
  concrete probes (specification/Goodhart, contracts & tiers, security
  surfaces from REAL inputs, loop caps, evals-or-hope, observability,
  economics, ops), evidence discipline (file:line or explicit not-found —
  invented architecture banned), findings with severity + the pipeline phase
  that fixes each, and a remediation map grouped by phase that doubles as
  the pipeline entry proposal. The one chain-gate-free skill; read-only on
  the target; only write: docs/agent/review.md. Distilled, self-contained
  successor of the author's personal agent-design knowledge skill.
- EDD eval suite (`skills/review/evals/`): REV-E01 positive-foreign (8-check
  contract with seeded-defect ground truth), REV-E02 pipeline-born
  (artifact-vs-code divergence), REV-E03 gate-negative, REV-E04
  trigger-negative (non-agent code must not fire).

### Pending graduation
- `review` run against a real foreign agent — tag `review-v0.1` when the
  dogfood passes.
```

- [ ] **Step 4:** Verify version prints `0.10.0` and both manifests mention "review"; commit `chore: release v0.10.0 (review skill)`.

---

### Task 6 (Alan, interactive): eval runs + dogfood

- [ ] REV-E03, REV-E04 in scratch; REV-E01 with the seeded-defect fixture (or better: a REAL foreign repo you care about) → rows in results.md.
- [ ] REV-E02 once the real repo is post-build (or with a divergence fixture).
- [ ] Tag `review-v0.1` on pass. Marketplace update + reinstall for v0.10.0.

---

## Self-review (done at planning time)

- **§5.3 coverage:** chain-gate-free ✓ (rule 1, REV-E01 check 1); eight dimensions mapped to phases ✓ (audit-frame, exactly the §5.3 list); severity + pipeline route ✓ (rule 5, template's remediation map); read-only + single write ✓ (rule 2); file:line-or-not-found ✓ (rule 4); does-not-replace-ship ✓ (rule 7, REV-E02 check 2, template scope notes); front-door framing ✓ (map = proposal, stated in SKILL.md and template).
- **Lessons applied:** self-contained frame (no agent-design/workspace reference — v0.4.1); DES-E02's old exclusion ("review tasks belong outside") now has its owner — the description claims exactly that territory; ship's audit disciplines reused (evidence-per-claim ~ evidence-per-command, read-only ~ auditor-writes-one-file); frontmatter on the single artifact path (no dual-path trap — one report, always).
- **Boundary check:** REV-E04 (non-agent code) vs generic code review; ship's SHP-E04 (deployment) unaffected; design's DES-E02 text (updated in v0.8.1 to "outside the pipeline") now consistent — review is IN the pipeline as a transversal, but design still correctly refuses review REQUESTS (different skill fires).
- **Check counts:** E01=8, E02=3, E03=2, E04=2 — match cases.json.
```
