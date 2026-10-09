# Eval procedure for agent-cycle:interop

Same agentic procedure as `skills/design/evals/README.md` (fresh session,
per-check PASS/FAIL rows in `results.md`, fix-and-rerun, dispute — never
silently edit — if a case is wrong).

Case-specific setup:

- The real dogfood agent fixture (external repo) is pre-v0.11: it has no design
  §8 and no spec `runtime`. It needs design re-entry (Phase E) and a spec
  version bump with `runtime` before ITP-E01 can run (or use a copy with §8 +
  `runtime` added).
- **ITP-E01** is the real dogfood run: the dogfood agent's (external repo)
  relationships (calendar service, notes service, database, messaging channel — all bounded
  result-lookups behind tools) are expected to produce decision: skip. The
  per-relationship table is required — a bare "doesn't need A2A" is a FAIL
  even though the conclusion is right.
- **ITP-E02** needs a hand-written scratch pipeline (design+spec+build.md,
  minimal but approved) whose spec names a genuine multi-turn delegation to
  an external specialist agent. The scratch spec must carry `runtime:` and
  name a stack that exercises "licensed vs free" (e.g. langgraph: licensed
  Agent Server vs own a2a-sdk server). Budget ~45 min; do NOT use the pipeline
  skills to author the fixture.
- **ITP-E03** branch 2: copy the real repo, bump spec.md to version 2 leaving
  build.md's spec_version at 1.
- **ITP-E04**: filesystem check afterward.

Scoring anchors: the entry-test check requires one row per external system
named in the spec's tools/security sections (for the real agent: calendar
service, notes service, database, messaging channel) — a missing row is a FAIL. The GOTO-problem
check (E02) requires the words to appear with the reasoning, not as decoration.

## Orchestrator cases (v0.13)

Build every fixture in a scratch git repo (never this repo) with hand-written
minimal artifacts; do NOT use the pipeline skills to author fixtures. Run the
plugin against it as in the procedure above.

- **ITP-E05**: a workspace repo, two runs, with agent-a built and approved:
  its `design.md`, `spec.md` and `build.md` hand-written and approved under
  `agents/agent-a/docs/agent/`; and `agents/orchestrator/docs/agent/design.md`
  with a §9 Delegation naming agent-a as a delegate (one question in, one
  answer out). Run 1: agent-a's design and spec say nothing about
  orchestrator and its code has no handler for it. Run 2 (a fresh copy):
  agent-a's design names orchestrator as a caller (the caller as an
  untrusted surface, the probe as a side-effect-free operation), its spec has
  the ingress, the caller surface with an injection-attempt BHV and the probe
  no-side-effect BHV, and its code has a handler the entry can cite. Score
  each run that only `agents/agent-a/docs/agent/interop.md` (plus
  agent-card/executor config if the verdict is A2A) was written, and score
  "no Served: line" in run 1 with
  `grep -n -E "^[-* ]*Served:" agents/agent-a/docs/agent/interop.md`.
