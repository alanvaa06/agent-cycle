# Eval procedure for agent-cycle:spec

Same agentic procedure as `skills/design/evals/README.md` (fresh session in a
scratch project, paste input, score every check PASS/FAIL with one line of
evidence, record per-check rows in `results.md`, fix-and-rerun on FAIL, dispute
— never silently edit — if a case itself is wrong).

Case-specific setup:

- **SPC-E01** needs a repo with an APPROVED `docs/agent/design.md` that HAS a
  §8 Stack decision with a chosen stack. The real dogfood repo
  (the dogfood agent, an external repo) is the canonical run, after running design
  re-entry on it (or use a copy with §8 added).
- **SPC-E02** needs a repo whose `design.md` frontmatter says `status: draft`
  (copy the real one and flip the field in the copy).
- **SPC-E03** needs a minimal approved design.md: one safe read-only tool, two
  capabilities. Write it by hand in a scratch repo (5 minutes); do NOT use the
  design skill for it.

- **SPC-E04**: no fixture (the input is outside the pipeline).
- **SPC-E05**: a scratch git repo that is a workspace: `agent-cycle.yaml` with
  `layout: workspace` and `agents: [agent-a, agent-b]`, and both
  `agents/agent-a/docs/agent/design.md` and `agents/agent-b/docs/agent/design.md`
  approved (hand-written and trivial, each with a §8 chosen stack). Start the
  session at the repo root (no working-directory hint) and do not name an
  agent in the request. Score "reads no design.md before the question" from the
  tool-call order, and the write scope with `git status --porcelain` afterward.

Scoring anchors for SPC-E01: for the capability-coverage checks, anchor on the
human-confirmed capability list in the session transcript (derivation guide
step 1) — do not re-derive your own list. For the tool-contract check, count
DISTINCT tool operations, not table rows: a row naming two tools (x / y) means
two contracts. (The real design's harness line says "6" counting rows; the
correct contract count there is 7.)

Run SPC-E02 three times: (1) design.md at status: draft, (2) no docs/agent/
directory at all, (3) an APPROVED design.md with §8 removed (expect a hard fail
routed to design re-entry, nothing written) — every hard-fail branch must
refuse and write nothing.

Presence checks require judgment on substance — a Gherkin scenario that cannot
fail, or a docstring that just restates the tool name, does NOT pass. For
SPC-E02, always check the filesystem afterward.

Gate: all checks PASS on all 6 cases before the skill graduates.

## Orchestrator cases (v0.13)

Build every fixture in a scratch git repo (never this repo) with hand-written
minimal artifacts; do NOT use the pipeline skills to author fixtures. Run the
plugin against it as in the procedure above.

- **SPC-E06**: a workspace repo with `agents/orchestrator/docs/agent/design.md`
  approved, with a §8 chosen stack, its §4 tool inventory listing agent-a and
  agent-b, and its §9 Delegation listing them as delegates; and
  `agents/agent-a/docs/agent/interop.md` approved with an Inbound contracts
  entry for orchestrator publishing `agent-a-contract@1` (line
  `Served: agent-a-contract@1`). `agents/agent-b/` has no `interop.md`.
  Score that only `agents/orchestrator/docs/agent/spec.md` was written.
