# Eval procedure for agent-cycle:build

Same agentic procedure as `skills/design/evals/README.md` (fresh session,
per-check PASS/FAIL rows in `results.md`, fix-and-rerun, dispute — never
silently edit — if a case is wrong).

Case-specific setup:

- The real whatsapp-owner-assistant fixture is pre-v0.11: it has no design
  §8 and no spec `runtime`. It needs design re-entry (Phase E) and a spec
  version bump with `runtime` before BLD-E01 can run (or use a copy with §8 +
  `runtime` added).
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
runtime — the skill loses if it scaffolds anything else, INCLUDING any
catalog stack the spec does not name. The only-Test-column check is scored with
`git diff --word-diff` on spec.md. The anti-gaming check requires seeing the
hook config on disk BEFORE source files appear in the history, not after.

## Workspace cases (v0.12)

Build the fixture in a scratch git repo (never this repo).

- **BLD-E06**: a workspace repo. `agent-cycle.yaml` lists `[ventas, soporte]`.
  `ventas` is already built: `agents/ventas/docs/agent/build.md` exists, the
  guard hook is installed at `.claude/hooks/guard_artifacts.py` at the plugin's
  current `HOOK_VERSION`, registered in `.claude/settings.json`, and
  `.claude/hooks/built-agents.txt` (tracked) contains `agents/ventas/`.
  `soporte` has an approved `design.md`, `spec.md` and `evals/` under
  `agents/soporte/` (hand-written and trivial; do NOT use the pipeline skills
  to author them), with no `build.md`. Commit them, and commit `soporte`'s
  entry in `agent-cycle.yaml` too, so check 1 is unambiguous: no baseline
  commit is expected and `build_start` is the fixture's HEAD. Variant: leave
  `soporte`'s entry in `agent-cycle.yaml` uncommitted while the three artifact
  paths stay clean; build must still make a baseline commit, containing only
  `agent-cycle.yaml`. Score the
  hook-version check with `git log -- .claude/hooks/guard_artifacts.py` (no new commit touching
  it) and the ratchet check with `git show HEAD:.claude/hooks/built-agents.txt`
  afterward. Variant: lower `HOOK_VERSION` in the installed hook, or delete the constant
  (a pre-v0.12 hook); build must
  STOP and ask the human, not rewrite it.
