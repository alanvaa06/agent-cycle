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
