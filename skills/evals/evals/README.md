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
