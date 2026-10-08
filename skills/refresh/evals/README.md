# Eval procedure for agent-cycle:refresh

Same agentic procedure as `skills/design/evals/README.md` (fresh session,
per-check PASS/FAIL rows in `results.md`, fix-and-rerun, dispute — never
silently edit — if a case is wrong).

Case-specific setup — ALWAYS a git clone or git worktree copy of the plugin repo (the
refresh gate requires a git work tree), never this checkout (refresh edits
files):

- **REF-E01**: in the copy, set `verified_on: 2026-01-01` on
  `skills/design/references/stacks/google-adk.md` and lower its
  `version_verified` (and the binding's `version_pinned`) by one release.
- **REF-E02**: run inside any scratch project without `.claude-plugin/`;
  filesystem check afterward.
- **REF-E03**: create `../client-a/docs/agent/design.md` and
  `../client-b/docs/agent/design.md` with a §8 "Catalog drift" subsection;
  client-a's entry must be true against today's docs, client-b's false.
- **REF-E04**: point the re-verification of one crewai fact at a scratch page
  containing the injected sentence from the case.
- **REF-E05**: filesystem check afterward.
