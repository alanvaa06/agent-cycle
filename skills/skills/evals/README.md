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
