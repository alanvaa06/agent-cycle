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
