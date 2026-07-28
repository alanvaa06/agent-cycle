# Eval procedure for agent-cycle:spec

Same agentic procedure as `skills/design/evals/README.md` (fresh session in a
scratch project, paste input, score every check PASS/FAIL with one line of
evidence, record per-check rows in `results.md`, fix-and-rerun on FAIL, dispute
— never silently edit — if a case itself is wrong).

Case-specific setup:

- **SPC-E01** needs a repo with an APPROVED `docs/agent/design.md`. The real
  dogfood repo (`whatsapp-owner-assistant`) is the canonical run.
- **SPC-E02** needs a repo whose `design.md` frontmatter says `status: draft`
  (copy the real one and flip the field in the copy).
- **SPC-E03** needs a minimal approved design.md: one safe read-only tool, two
  capabilities. Write it by hand in a scratch repo (5 minutes); do NOT use the
  design skill for it.

Presence checks require judgment on substance — a Gherkin scenario that cannot
fail, or a docstring that just restates the tool name, does NOT pass. For
SPC-E02, always check the filesystem afterward.

Gate: all checks PASS on all 3 cases before the skill graduates.
