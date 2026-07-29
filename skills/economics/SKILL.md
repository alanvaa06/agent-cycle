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
2. EVERY unit price carries a source and an as-of date. Priority: figures the
   user gave ("user-provided, <date>") → provider pricing pages via web (URL +
   retrieval date, the default) → UNKNOWN row. Use a user's own compiled
   sources only if they offer them — never ask where such sources live. Check
   free tiers and pricing conditions before quoting headline rates. A price with no dated source does not enter the model. Never quote prices
   from model memory.
3. Tokens first — they usually dominate (70–90% in multi-user agents), but at
   very low volume flat infra can win. Model tokens first, then STATE which
   line dominates and why.
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
