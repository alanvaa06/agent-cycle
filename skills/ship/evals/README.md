# Eval procedure for agent-cycle:ship

Same agentic procedure as `skills/design/evals/README.md` (fresh session,
per-check PASS/FAIL rows in `results.md`, fix-and-rerun, dispute — never
silently edit — if a case is wrong).

Case-specific setup:

- The real dogfood agent fixture (external repo) is pre-v0.11: it has no design
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

- **SHP-E05**: a workspace repo with `agents/agent-a/` and `agents/agent-b/`,
  `agent-b` fully built. It was first built at the repo root, so the
  `build_start` SHA in its `build.md` is a pre-move commit. Make the range
  `build_start..HEAD` contain: several commits that touch only
  `agents/agent-a/`; one commit that touches `agents/agent-b/src/` and
  `agents/agent-a/src/` together; and one commit with the message prefix
  `agent-cycle: workspace move` that is a pure rename (`git mv` of the
  root-level agent files into `agents/agent-b/`, nothing else, `docs/agent`
  landing at `agents/agent-b/docs/agent`), lying inside that range. Each
  agent has its own lockfile. Score the diff check from the literal command the
  audit cites.

## Orchestrator cases (v0.13)

Build every fixture in a scratch git repo (never this repo) with hand-written
minimal artifacts; do NOT use the pipeline skills to author fixtures. Run the
plugin against it as in the procedure above.

- **SHP-E06**: a workspace repo, two runs. Run 1: orchestrator through interop
  with spec §8 pinning `agent-a-contract@1` and `agent-b-contract@1`; agent-a
  has approved `interop.md` (Inbound contracts entry for orchestrator with
  `Served: agent-a-contract@1`) and an approved `ship-report.md` whose
  `interop_version` equals that interop.md's `version`; agent-b has approved
  `interop.md` (`Served: agent-b-contract@1`) but no `ship-report.md`. Run 2:
  add agent-b's `ship-report.md` (same `interop_version` rule). Each
  delegate's Inbound contracts entry has one block per served version (input
  schema, output schema, probe request, sample probe response), and
  orchestrator's `evals/delegates/agent-a-probe.json` and
  `agent-b-probe.json` carry `contract` equal to the pins and that version's
  probe request. For the live probe, a stub HTTP server per delegate
  answering that probe request is enough; orchestrator's deploy
  configuration (e.g. its `.env.example` / compose file) sets `AGENT_A_BASE_URL` and
  `AGENT_B_BASE_URL` (the keys its delegate client reads) to the stubs, plus
  its delegate credentials `AGENT_A_TOKEN` and `AGENT_B_TOKEN`.
- **SHP-E07**: a workspace repo where agent-a has the full approved chain
  (`design.md`, `spec.md`, `evals/config.yaml`, `build.md`, `skills.md`,
  `interop.md`) and a runner the audit can re-run; its `interop.md`
  publishes `agent-a-contract@2` with `Served: agent-a-contract@2` and one
  block for @2 (schemas, probe request, sample response), and its
  Inbound contracts entry cites a handler that exists in its code and a probe
  BHV in its spec. `agents/orchestrator/docs/agent/spec.md` §8 pins
  `agent-a-contract@1`, and `agents/orchestrator/docs/agent/ship-report.md` is
  approved with `delegate_contracts: [agent-a-contract@1]`. Re-run with
  `Served: agent-a-contract@1, agent-a-contract@2` (and a block per served
  version) to score the passing branch. For the last-approved variant, commit
  orchestrator's approved ship-report first, then commit a working copy with
  `status: draft` and `delegate_contracts: [agent-a-contract@2]`.
