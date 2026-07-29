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
