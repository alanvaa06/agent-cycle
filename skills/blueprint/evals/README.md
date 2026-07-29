# Eval procedure for agent-cycle:blueprint

Same agentic procedure as `skills/design/evals/README.md` (fresh session,
per-check PASS/FAIL rows in `results.md`, fix-and-rerun, dispute — never
silently edit — if a case is wrong).

Case-specific setup:

- **BLP-E01** is the real dogfood run (pre-build state of the real repo
  qualifies today). Score self-containment by actually grepping the produced
  HTML for `http://`, `https://`, `src=`, `href=`, `url(`, `fetch(`,
  `XMLHttpRequest` — any external reference is a FAIL. Open the file from
  disk with networking off (or devtools network tab empty) — it must render
  fully.
- **BLP-E02**: scratch repos; filesystem check afterward.
- **BLP-E03** fixture: copy the real repo and hand-write a minimal approved
  build.md (with runtime, target, runner command, a recorded green DoD) and a
  minimal ship-report.md. ~20 min; do NOT run the build skill for it.
- **BLP-E04**: filesystem check afterward.

Scoring anchors: the sanitization check is scored by grepping the HTML for
every value in the repo's .env.example patterns and any token-like string —
NAMES may appear, values never. The economics check is scored by diffing the
embedded numbers against the economics artifact — identical or FAIL (no
recomputation drift).
