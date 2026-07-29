# Eval procedure for agent-cycle:build

Same agentic procedure as `skills/design/evals/README.md` (fresh session,
per-check PASS/FAIL rows in `results.md`, fix-and-rerun, dispute — never
silently edit — if a case is wrong).

Case-specific setup:

- **BLD-E01** is the real dogfood run and is LONG (it produces the whole
  agent). Score checks 1-5 and 8-10 from the transcript + repo state as the
  build progresses; score 6-7 and 11 from the finished repo (run the runner
  yourself: it must exit non-zero while any eval fails and zero only when the
  suite is green).
- **BLD-E02** branch 2 setup: copy the real repo, bump spec.md version to 2
  without touching evals/config.yaml (spec_version stays 1) — the chain is now
  stale.
- **BLD-E03** needs a hand-written trivial approved design+spec+evals set in a
  scratch repo (30 min; do NOT use the pipeline skills to author them).
- **BLD-E04**: filesystem check afterward.

Scoring anchors: the runtime check (2) is scored against the spec's own fixed
runtime — the skill loses if it scaffolds anything else, INCLUDING the plugin's
own documented first framework target when the spec says otherwise. The
only-Test-column check is scored with `git diff --word-diff` on spec.md. The
anti-gaming check requires seeing the hook config on disk BEFORE source files
appear in the history, not after.
