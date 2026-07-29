# Eval procedure for agent-cycle:economics

Same agentic procedure as `skills/design/evals/README.md` (fresh session,
scratch project, per-check PASS/FAIL rows in `results.md`, fix-and-rerun,
dispute — never silently edit — if a case is wrong).

Case-specific setup:

- **ECO-E01** needs approved design.md + spec.md; the real dogfood repo is the
  canonical run. Prices come from the web (provider pages, URL + retrieval
  date) or from figures the user gives in-session; scoring covers dating and
  sourcing, and FAILS the run if the skill proactively asks where compiled
  sources live.
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
