# Eval procedure for agent-cycle:review

Same agentic procedure as `skills/design/evals/README.md` (fresh session,
per-check PASS/FAIL rows in `results.md`, fix-and-rerun, dispute — never
silently edit — if a case is wrong).

Case-specific setup:

- **REV-E01** needs a FOREIGN agent target. Cheapest realistic fixture: a
  scratch repo with a hand-written ~200-line agent (a loop calling an LLM,
  2-3 tools incl. one that writes somewhere, retrieved web/text content fed
  into prompts, a README claiming a success metric). Seed it with 3-4
  deliberate defects (e.g. untrusted content concatenated into the system
  prompt, no step cap, an activity metric, no evals) — the review must find
  them WITH file:line. ~30 min; do NOT use pipeline skills to author it.
- **REV-E02**: the real dogfood repo qualifies once build exists; pre-build,
  a fixture with approved design/spec/evals plus divergent source works
  (introduce one deliberate artifact-vs-code divergence).
- **REV-E03**: empty scratch dir; filesystem check afterward.
- **REV-E04**: filesystem check afterward.

Scoring anchors: the eight-dimensions check FAILS if any dimension is absent
from the report (n/a with a reason counts as present). The evidence check
FAILS on any code claim without file:line, and on any 'the agent probably...'
construction — probabilistic architecture is invented architecture. The
seeded defects in E01's fixture are the ground truth: each missed seeded
defect is a FAIL row for the relevant dimension.
