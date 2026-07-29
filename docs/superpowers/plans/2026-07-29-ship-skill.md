# agent-cycle `/ship` Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship phase 7 — `agent-cycle:ship` — the mechanical audit that closes the pipeline: chain integrity, end-to-end traceability, the suite re-run live (never trusted from build.md), security re-verification, the anti-gaming word-diff audit, observability + alarm checks, runbook verification, and an explicit SHIP / NO-SHIP verdict where NO-SHIP is the pipeline working. The auditor writes exactly one file: `docs/agent/ship-report.md`. Then release v0.8.0.

**Architecture:** Same shape (EDD cases → two references → SKILL.md). Core stances from plugin design §4.7: evidence-per-command (every check cites the command it ran and a summary of its output — no command, no check); green = the runner's exit code obtained DURING the audit; findings route to the re-entry ladder, never fixed inline by the auditor; the runbook is verified against minimums (a fill-in template ships in references so a missing runbook is a cheap finding, but the auditor never writes it). Self-contained: no user workspace (vaults, personal checklists) assumed — the audit checklist lives entirely in this skill.

**Tech Stack:** Claude Code plugin format, Markdown/JSON only.

**Spec:** `docs/superpowers/specs/2026-07-28-agent-cycle-plugin-design.md` § 4.7, § 6.

---

### Task 1: EDD eval cases — before the skill exists

**Files:**
- Create: `skills/ship/evals/cases.json`
- Create: `skills/ship/evals/README.md`
- Create: `skills/ship/evals/results.md`

- [ ] **Step 1: Write the eval cases**

Write `skills/ship/evals/cases.json`:

```json
{
  "skill": "agent-cycle:ship",
  "spec_ref": "docs/superpowers/specs/2026-07-28-agent-cycle-plugin-design.md#47-agent-cycleship",
  "cases": [
    {
      "id": "SHP-E01",
      "type": "positive",
      "input": "Run the ship audit. (Run in a repo with the full chain approved: design, spec, evals, build, plus skills.md and interop.md decisions recorded — e.g. the real whatsapp-owner-assistant post-build.)",
      "expected": {
        "fires": true,
        "checks": [
          "Gate: the FULL chain is approved and version-consistent — design.md, spec.md, evals/config.yaml, docs/agent/build.md, plus skills.md and interop.md with their decisions recorded (none/skip count); economics artifact read when present",
          "The eval suite is RE-RUN during the audit via the build's runner — exit code cited from this run, pass^k tiers and every release blocker verified from this run's output; build.md's own claim is treated as claim, not evidence",
          "End-to-end traceability table verified: every BHV → eval id(s) → test/phase → status in the audit's own run — complete, or gaps justified in writing",
          "Security re-verified with evidence per command: adversarial cases green in the audit run; least-privilege diff (the adapter's REAL scopes/credentials vs the spec's security table); secret scan over the repo and git history; ingress spot-checks (signature-over-raw-body, allowlist, dedupe present in code)",
          "Anti-gaming audit executed mechanically: git diff --word-diff over the build's commit range for evals/** and docs/agent/** (minus the sanctioned allow-list) — zero unsanctioned changes, command cited; hook-restore verification noted when the hook was bypassed for the Test column",
          "Observability verified with evidence: traces arriving at the adapter's backend (or exporter log), token counters present on spans, token-spend alarm configured at the economics threshold when an economics artifact exists",
          "Runbook verified against the minimums (queue/DLQ drain, rollback, kill switch, weekly ritual scheduled); a missing or thin runbook is a FINDING with the template referenced — never silence, never auditor-authored",
          "Explicit verdict: SHIP or NO-SHIP; every finding carries a severity and its re-entry route (which phase re-opens); NO-SHIP framed as the pipeline working, not as failure",
          "Artifact docs/agent/ship-report.md with frontmatter (agent_name, version, status: draft, date, and the versions of every chain artifact audited); the auditor modified NOTHING else in the repo; human sign-off at the gate = shipped"
        ]
      }
    },
    {
      "id": "SHP-E02",
      "type": "gate-negative",
      "input": "Run the ship audit. (Run twice: once with no docs/agent/build.md, once where skills.md and interop.md are absent — conditional-phase decisions never recorded.)",
      "expected": {
        "fires": true,
        "checks": [
          "Refuses in both branches: names the missing gate (no build → run agent-cycle:build first; missing conditional decisions → run agent-cycle:skills / agent-cycle:interop, a recorded none/skip is required) and stops",
          "Writes NO files in either branch — verified on the filesystem afterward"
        ]
      }
    },
    {
      "id": "SHP-E03",
      "type": "edge-no-ship",
      "input": "Run the ship audit. (Run against a fixture where one release blocker is red — e.g. an adversarial case fails in the audit's own suite run.)",
      "expected": {
        "fires": true,
        "checks": [
          "Verdict is NO-SHIP with the failing blocker cited from the audit's own run output — the audit completes all sections rather than stopping at the first red",
          "The finding carries its re-entry route (e.g. containment failure → build re-entry; ambiguous scenario → spec dispute) and the auditor attempts NO fix of any kind",
          "The report's framing treats NO-SHIP as the pipeline catching what it was built to catch — no apology, no soft-pedaling the red"
        ]
      }
    },
    {
      "id": "SHP-E04",
      "type": "trigger-negative",
      "input": "Deploy my Next.js app to Vercel — set up the project and push it live.",
      "expected": {
        "fires": false,
        "checks": [
          "agent-cycle:ship does NOT fire — generic app deployment is outside the pipeline",
          "No files are created or modified — verified on the filesystem afterward"
        ]
      }
    }
  ]
}
```

- [ ] **Step 2: Write the run procedure**

Write `skills/ship/evals/README.md`:

```markdown
# Eval procedure for agent-cycle:ship

Same agentic procedure as `skills/design/evals/README.md` (fresh session,
per-check PASS/FAIL rows in `results.md`, fix-and-rerun, dispute — never
silently edit — if a case is wrong).

Case-specific setup:

- **SHP-E01** is the real dogfood run and requires the FULL chain including a
  green build (BLD-E01 first, then SKL-E01 and ITP-E01 decisions recorded).
  Scoring evidence-per-command: every audit section must cite the literal
  command it ran and summarize its output — an assertion without its command
  is a FAIL for that check.
- **SHP-E02** branch 2: copy the real repo post-build and delete skills.md +
  interop.md.
- **SHP-E03** fixture: copy the real repo post-build and break one adversarial
  expectation (e.g. edit the AGENT source — not the evals — so a containment
  assert fails). The audit's own run must catch it.
- **SHP-E04**: filesystem check afterward.

Scoring anchors: the re-run check is scored by the presence of THIS audit's
runner invocation and exit code in the report — a report quoting build.md's
result is a FAIL. The nothing-else-modified check is scored by `git status`
+ `git diff` after the audit: only ship-report.md may appear.
```

- [ ] **Step 3: Create the results log**

Write `skills/ship/evals/results.md`:

```markdown
# Eval runs — agent-cycle:ship

One row per check, per run. Verdict: PASS / FAIL. Evidence: one line.

| Date | Case | Check # | Verdict | Evidence |
|---|---|---|---|---|
```

- [ ] **Step 4: Verify JSON**

Run: `python -c "import json; d=json.load(open(r'skills/ship/evals/cases.json')); print(len(d['cases']), 'cases,', len(d['cases'][0]['expected']['checks']), 'checks in E01')"`
Expected: `4 cases, 9 checks in E01`

- [ ] **Step 5: Commit**

```bash
git add skills/ship/evals/
git commit -m "feat(ship): EDD eval cases before SKILL.md (SHP-E01..E04)"
```

---

### Task 2: Audit guide

**Files:**
- Create: `skills/ship/references/audit-guide.md`

- [ ] **Step 1: Write the guide**

Write `skills/ship/references/audit-guide.md`:

```markdown
# Audit guide — agent-cycle:ship

Mechanical, not creative. Every section: run the command, cite it, summarize
its output, verdict the check. No command → no check. Complete ALL sections
even after a red — the report is a full picture, not a first-failure abort.

## Section 0 — Gate

The full chain, approved and version-consistent: design.md; spec.md
(design_version matches); evals/config.yaml (spec_version matches);
docs/agent/build.md (approved, versions match); skills.md AND interop.md
present with decisions recorded (none/skip are valid decisions — absence is
not). Economics artifact read when present (its alarm threshold becomes
Section 5's expected value). Any gap → refuse, name the phase to run,
write nothing.

## Section 1 — Suite re-run (the load-bearing section)

Run the build's runner NOW, from the report: cite the exact command, the exit
code, the per-tier pass^k summary, and every release blocker's status from
THIS run. build.md's recorded result is a historical claim — the audit's
evidence is its own run. A non-zero exit here does not stop the audit; it
sets the verdict floor to NO-SHIP and the remaining sections still execute.

## Section 2 — Traceability

Reconstruct BHV → eval id(s) (spec §6 Eval column) → test/phase (§6 Test
column) → status in Section 1's run. Every BHV accounted for or its gap
justified in writing. Cross-check the counts against evals/config.yaml's
coverage map.

## Section 3 — Security re-verify

- Adversarial: every adversarial case green in Section 1's run (they are
  release blockers; a red one is already NO-SHIP — still enumerate them).
- Least privilege: diff the adapter's REAL credential scopes (env/config, the
  deploy recipe, provider consoles where readable) against the spec's
  security/credential table. Extra scope = finding.
- Secrets: scan the working tree AND git history for secret patterns; verify
  .env-class files are ignored and no credential ever entered a commit.
- Ingress spot-checks: signature-over-raw-body before parsing, sender
  allowlist before the loop, dedupe on the channel message id — present in
  the code, cite file:line.

## Section 4 — Anti-gaming audit

`git diff --word-diff <build-start>..<build-end> -- evals/ docs/agent/` minus
the sanctioned allow-list (docs/agent/build.md; the spec §6 Test column).
Zero unsanctioned changes. Cite the commit range and the diff summary. If the
hook was bypassed for the Test column, build.md must record the
restore-verification; confirm it.

## Section 5 — Observability + alarm

- Traces: evidence they arrive (query the backend, or the exporter's local
  log) — cite what was seen, including one span with the spec's per-turn
  attributes AND gen_ai.usage token counters.
- Alarm: the token-spend alarm exists and its threshold equals the economics
  artifact's stated number (when economics exists). Absent economics → note
  it; absent alarm → finding.

## Section 6 — Runbook

Verify docs/runbook.md (or the repo's stated location) against the minimums:
queue/DLQ drain steps, rollback (how to return to the previous version),
kill switch (how to stop the agent NOW), weekly ritual scheduled (suite
re-run + judge spot-validation + corrections mined into new eval cases).
Missing or thin → FINDING that references
`references/runbook-template.md` for the owner (or a build re-entry) to
fill. The auditor NEVER writes the runbook.

## Section 7 — Verdict and report

- SHIP: every section green.
- NO-SHIP: any release blocker red, any unsanctioned artifact change, any
  missing chain link — each finding with severity (blocker / important /
  minor) and its re-entry route (which phase re-opens). NO-SHIP is the
  pipeline catching what it was built to catch; write it that way.
- Report: docs/agent/ship-report.md with frontmatter (agent_name, version,
  status: draft, date, design_version, spec_version, evals_config_date,
  build_version) + the seven sections, each with its commands and evidence.
- The auditor's ONLY write is this report. Human sign-off at the gate →
  status: approved = SHIPPED. Suggest the release tag.
```

- [ ] **Step 2: Commit**

```bash
git add skills/ship/references/audit-guide.md
git commit -m "feat(ship): audit guide (evidence per command, live re-run, verdict rules)"
```

---

### Task 3: Runbook template

**Files:**
- Create: `skills/ship/references/runbook-template.md`

- [ ] **Step 1: Write the template**

Write `skills/ship/references/runbook-template.md`:

```markdown
# Runbook template — referenced by ship findings, filled by the owner/build

Minimum viable operations runbook for a pipelined agent. The ship audit
verifies these sections exist and are actionable; it never writes them.

---

# <Agent Name> — Runbook

## Kill switch

How to stop the agent NOW, in order of speed:
1. <e.g. stop the worker service/container: exact command>
2. <e.g. disable the webhook at the provider: where, which toggle>
3. <e.g. revoke the channel token: where>
Expected effect of each (what stops, what queues, what the user sees).

## Queue / DLQ drain

- Inspect depth: <command>
- Drain safely: <command / procedure — what happens to queued turns>
- Poison message: how to identify, park, and replay one message.

## Rollback

- Current version identifier: <where it is recorded>
- Roll back to previous: <exact commands — image tag / git ref / deploy step>
- State compatibility note: <sessions/schema — safe window for rollback>

## Alarms

| Alarm | Threshold | Source | First response |
|---|---|---|---|
| Token spend | <economics §6 number> | <where it fires> | <check what, then what> |
| <queue age / DLQ depth / error rate> | ... | ... | ... |

## Weekly ritual (the living suite)

- Re-run the eval suite: <command> — investigate any new red.
- Judge spot-validation: sample N llm_judge verdicts vs human read.
- Mine corrections: user corrections from the week become candidate eval
  cases (via the evals phase, never edited in place).
- Review token spend vs the economics estimate; recalibrate when >25% off.

## Contacts / escalation

- Owner: <who>. Provider status pages: <links>. Escalation order.
```

- [ ] **Step 2: Commit**

```bash
git add skills/ship/references/runbook-template.md
git commit -m "feat(ship): runbook template (kill switch, drain, rollback, alarms, weekly ritual)"
```

---

### Task 4: SKILL.md

**Files:**
- Create: `skills/ship/SKILL.md`

- [ ] **Step 1: Write the skill**

Write `skills/ship/SKILL.md`:

```markdown
---
name: ship
description: "Phase 7 of the agent-cycle pipeline — the closing mechanical audit: full-chain gate, live suite re-run (never trusted from build.md), end-to-end traceability, security re-verification, anti-gaming word-diff audit, observability + alarm checks, runbook verification, and an explicit SHIP / NO-SHIP verdict with re-entry routes. Use when the user wants the ship audit / release check for a pipelined agent — 'run the ship audit', 'is the agent ready to ship', 'siguiente fase del pipeline' after build+conditionals. Do NOT use without the full approved chain (design+spec+evals+build+skills/interop decisions), nor for generic app deployment (Vercel/hosting setup), nor to FIX anything — findings route to the re-entry ladder."
---

# agent-cycle:ship — The Audit That Closes the Pipeline

Ship audits; it never fixes. Every check is a command plus its output.
NO-SHIP is the pipeline working.

## Hard rules

1. FULL-CHAIN GATE: design, spec, evals, build approved and version-
   consistent; skills.md and interop.md present with recorded decisions
   (none/skip valid; absence is not); economics read when present. Any gap →
   refuse, name the phase, write nothing.
2. THE AUDITOR ONLY WRITES docs/agent/ship-report.md. Nothing else — not a
   fix, not a runbook, not a config touch-up. Findings route to the re-entry
   ladder with the owning phase named.
3. EVIDENCE PER COMMAND: every check cites the literal command it ran and a
   summary of its output. No command, no check. Claims in build.md are
   history, not evidence.
4. GREEN = THIS AUDIT'S RUN: the suite is re-run live via the build's runner;
   exit code, pass^k, and release blockers come from that run.
5. A red does not abort the audit — all sections complete; the verdict floor
   becomes NO-SHIP.
6. Security re-verify is mandatory: adversarial status, least-privilege diff
   (real scopes vs spec), secret scan incl. git history, ingress spot-checks
   with file:line.
7. Anti-gaming audit is mandatory: word-diff over the build's commit range on
   evals/ and docs/agent/ minus the sanctioned allow-list; hook-restore
   verification confirmed when bypassed.
8. Observability: spans with token counters evidenced; token-spend alarm
   matches the economics threshold when economics exists. Runbook verified
   against the template minimums — missing runbook is a finding referencing
   the template, never auditor-authored.
9. Verdict explicit (SHIP / NO-SHIP), findings carry severity + re-entry
   route, NO-SHIP written as the pipeline catching what it was built to
   catch. Human sign-off at the gate → approved = SHIPPED. Never
   self-approve.

## Workflow

1. Read `references/audit-guide.md`; run sections 0→7 in order, completing
   all sections regardless of reds.
2. Write docs/agent/ship-report.md (frontmatter: agent_name, version,
   status: draft, date, design_version, spec_version, evals_config_date,
   build_version) with every section's commands and evidence.
3. Present: verdict, blockers (if any) with re-entry routes, the suggested
   release tag.
4. Explicit sign-off → status: approved = SHIPPED. Findings → the owner
   routes re-entry; re-audit after.

## Failure modes to avoid

- Quoting build.md's green instead of re-running (rules 3-4).
- Stopping at the first red (rule 5).
- Fixing anything — even a one-line runbook gap (rule 2).
- An assertion without its command (rule 3).
- Accepting a missing skills.md/interop.md as "obviously none/skip" (rule 1).
- Soft-pedaling NO-SHIP (rule 9).
```

- [ ] **Step 2: Verify frontmatter**

Run: `head -4 skills/ship/SKILL.md`
Expected: `---`, `name: ship`, description present.

- [ ] **Step 3: Commit**

```bash
git add skills/ship/SKILL.md
git commit -m "feat(ship): SKILL.md — audit not fix, evidence per command, NO-SHIP is the pipeline working"
```

---

### Task 5: Release v0.8.0

- [ ] **Step 1:** plugin.json version → `0.8.0`.
- [ ] **Step 2:** README status line → `**Status:** v0.8.0 — all 7 phases (\`design\` → \`ship\`) + \`economics\`. Only\n\`blueprint\` remains. Built skill-by-skill, each dogfooded on a real agent.`
- [ ] **Step 3:** CHANGELOG entry before `## [0.7.0]`:

```markdown
## [0.8.0] — 2026-07-29

### Added
- **`ship` skill** (phase 7 of 7 — the closing mechanical audit): full-chain
  gate (conditional-phase decisions required, none/skip valid), live suite
  re-run as the only accepted green (build.md is claim, not evidence),
  end-to-end traceability, security re-verification (adversarial /
  least-privilege diff / secret scan incl. history / ingress spot-checks),
  anti-gaming word-diff audit over the build's commit range, observability +
  token-counter + economics-threshold alarm checks, runbook verification
  against a shipped template (auditor never writes it), explicit SHIP /
  NO-SHIP verdict with per-finding severity + re-entry routes. The auditor's
  only write: docs/agent/ship-report.md.
- EDD eval suite (`skills/ship/evals/`): SHP-E01 positive (9-check contract),
  SHP-E02 gate-negative (missing build / missing conditional decisions),
  SHP-E03 no-ship edge (red blocker → complete audit, NO-SHIP, no fixing),
  SHP-E04 trigger-negative (generic deployment must not fire).

### Pending graduation
- `ship` skill run against the real agent — tag `ship-v0.1` when the dogfood
  audit completes.
```

- [ ] **Step 4:** Verify version prints `0.8.0`; commit `chore: release v0.8.0 (ship skill)`.

---

### Task 6 (Alan, interactive): eval runs + dogfood

- [ ] SHP-E02 ×2, SHP-E03 (broken-agent fixture), SHP-E04 in scratch → rows in results.md.
- [ ] SHP-E01 dogfood in `C:\Proyectos\Whatsapp_agent` — requires BLD-E01 green + SKL/ITP decisions first → tag `ship-v0.1`.
- [ ] Marketplace update + reinstall for v0.8.0.

---

## Self-review (done at planning time)

- **§4.7 coverage:** traceability ✓ (section 2); security gates re-verified ✓ (section 3, all four named sub-checks); anti-gaming git-diff audit ✓ (section 4, word-diff per the economics-skill lesson); observability + alarms ✓ (section 5, token counters + economics threshold — closes the loop the economics artifact opened); runbook ✓ (section 6 + template; DLQ drain/rollback/kill switch/weekly ritual all present); DoD report + sign-off ✓ (section 7). §4.7's "operationalizes the agent-design checklist" adjusted deliberately: the plugin no longer assumes any user workspace (v0.4.1 lesson) — the audit checklist is self-contained in audit-guide.md; a user's personal checklist can inform a run when they offer it, never assumed.
- **Cross-skill:** consumes build.md (claim vs evidence distinction), evals' release blockers, economics' alarm threshold, the anti-gaming allow-list exactly as build defined it (build.md + Test column); frontmatter chain matches build's (evals_config_date, not a nonexistent evals_version); "weekly ritual" in the runbook template mirrors evals' living-suite language.
- **Auditor-writes-one-file** is the phase's own anti-gaming: rule 2 + SHP-E01 check 9 (scored by git status after the audit).
- **Check counts:** E01=9, E02=2, E03=3, E04=2 — match cases.json.
```
