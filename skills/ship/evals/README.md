# Eval procedure for agent-cycle:ship

Same agentic procedure as `skills/design/evals/README.md` (fresh session,
per-check PASS/FAIL rows in `results.md`, fix-and-rerun, dispute — never
silently edit — if a case is wrong).

Case-specific setup:

- The real whatsapp-owner-assistant fixture is pre-v0.11: it has no design
  §8 and no spec `runtime`. It needs design re-entry (Phase E) and a spec
  version bump with `runtime` before SHP-E01 can run (or use a copy with §8 +
  `runtime` added).
- **SHP-E01** is the real dogfood run and requires the FULL chain including a
  green build (BLD-E01 first, then SKL-E01 and ITP-E01 decisions recorded).
  Scoring evidence-per-command: every audit section must cite the literal
  command it ran and summarize its output — an assertion without its command
  is a FAIL for that check.
- **SHP-E02** branch 2: copy the real repo post-build and delete skills.md +
  interop.md.
- **SHP-E03** fixture: copy the real repo post-build and break one adversarial
  expectation (e.g. edit the AGENT source — not the evals — so a containment
  assert fails). The audit's own run must catch it.
- **SHP-E04**: filesystem check afterward.

Scoring anchors: the re-run check is scored by the presence of THIS audit's
runner invocation and exit code in the report — a report quoting build.md's
result is a FAIL. The nothing-else-modified check is scored by `git status`
+ `git diff` after the audit: only ship-report.md may appear.

## Workspace cases (v0.12)

Build the fixture in a scratch git repo (never this repo).

- **SHP-E05**: a workspace repo with `agents/ventas/` and `agents/soporte/`,
  `soporte` fully built. It was first built at the repo root, so the
  `build_start` SHA in its `build.md` is a pre-move commit. Make the range
  `build_start..HEAD` contain: several commits that touch only
  `agents/ventas/`; one commit that touches `agents/soporte/src/` and
  `agents/ventas/src/` together; and one commit with the message prefix
  `agent-cycle: workspace move` that is a pure rename (`git mv` of the
  root-level agent files into `agents/soporte/`, nothing else, `docs/agent`
  landing at `agents/soporte/docs/agent`), lying inside that range. Each
  agent has its own lockfile. Score the diff check from the literal command the
  audit cites.
