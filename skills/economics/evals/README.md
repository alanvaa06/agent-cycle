# Eval procedure for agent-cycle:economics

Same agentic procedure as `skills/design/evals/README.md` (fresh session,
scratch project, per-check PASS/FAIL rows in `results.md`, fix-and-rerun,
dispute — never silently edit — if a case is wrong).

Case-specific setup:

- **ECO-E01** needs approved design.md + spec.md; the real dogfood repo is the
  canonical run. If the workspace has compiled pricing sources (e.g. vault
  articles on cloud/agent deployment costs), the run should cite them — scoring
  covers that they were found and used.
- **ECO-E02** runs twice: design at draft, and no docs/agent/ at all.
- **ECO-E03** needs an existing economics artifact with basis: estimate plus
  real numbers (paste plausible actuals in the session if no metrics export
  exists — the check is about delta handling, not the numbers' origin).
- **ECO-E04**: filesystem check afterward.

Scoring anchors: the every-price-dated check is scored by scanning the unit
price table — any row without BOTH a source and an as-of date is a FAIL. The
no-cent-precision check applies to TOTALS and scenario bands (unit prices may
carry exact list values). Formula-audit check: a reader must be able to
recompute any total from the stated assumptions without guessing.
