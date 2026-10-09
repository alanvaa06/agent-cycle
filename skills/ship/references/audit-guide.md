# Audit guide — agent-cycle:ship

Mechanical, not creative. Every section: run the command, cite it, summarize
its output, verdict the check. No command → no check. Complete ALL sections
even after a red — the report is a full picture, not a first-failure abort.

## Section 0 — Gate

Resolve AGENT_ROOT per the agent-cycle plugin's references/agent-root.md; every
path below is relative to it.

The full chain, approved and version-consistent: design.md; spec.md
(design_version matches); evals/config.yaml (spec_version matches);
docs/agent/build.md (approved, versions match); skills.md AND interop.md
present with decisions recorded (none/skip are valid decisions — absence is
not). Economics artifact read when present (its alarm threshold becomes
Section 5's expected value). Orchestrators (spec §8 lists at least one
delegate): every delegate has an approved `docs/agent/interop.md` publishing
Inbound contracts for this caller and an approved `docs/agent/ship-report.md`
that covers its current interop: the ship-report's frontmatter
`interop_version` equals the delegate's interop.md `version` (older → refuse:
the delegate must re-ship). These cross-agent reads run from the repo root
(see Section 3). Any gap → refuse, name the phase to run (for a delegate, name
the delegate too), write nothing.

## Section 1 — Suite re-run (the load-bearing section)

Run the build's runner NOW, from the report: cite the exact command, the exit
code, the per-tier pass^k summary, and every release blocker's status from
THIS run. build.md's recorded result is a historical claim — the audit's
evidence is its own run. A non-zero exit here does not stop the audit; it
sets the verdict floor to NO-SHIP and the remaining sections still execute.

## Section 2 — Traceability

Reconstruct BHV → eval id(s) (spec §6 Eval column) → test/phase (§6 Test
column) → status in Section 1's run. Every BHV accounted for or its gap
justified in writing. Cross-check the counts against evals/config.yaml's
coverage map.

## Section 3 — Security re-verify

- Adversarial: every adversarial case green in Section 1's run (they are
  release blockers; a red one is already NO-SHIP — still enumerate them).
- Least privilege: diff the adapter's REAL credential scopes (env/config, the
  deploy recipe, provider consoles where readable) against the spec's
  security/credential table. Extra scope = finding.
- Secrets: scan the working tree AND git history for secret patterns; verify
  .env-class files are ignored and no credential ever entered a commit.
- Ingress spot-checks: signature-over-raw-body before parsing, sender
  allowlist before the loop, dedupe on the channel message id — present in
  the code, cite file:line.
- Runtime pin: read spec.md's frontmatter `runtime`, strip a leading
  `off-catalog:` prefix and split on the LAST `@`. Show the entry in the
  lockfile under `<AGENT_ROOT>` (command + output) for the form the spec uses:
  - `<card-id>@<version>`: the lockfile entry for the card's package (the
    `package:` field in the frontmatter of the agent-cycle plugin's
    `skills/design/references/stacks/<card-id>.md`; the binding's "Pinned
    version and traps" names any alternative, e.g. `pydantic-ai-slim`) equals
    exactly the spec's version. Compare names case-insensitively with `-`,
    `_` and `.` treated as equivalent.
  - `no-framework@n/a`: each package pinned in `bindings/no-framework.md`
    section "Pinned version and traps" that appears in the lockfile is at
    exactly the listed version (packages the design does not use are absent,
    not findings), and every lockfile entry carries hashes (the binding
    requires it).
  - `off-catalog:<name>@<version>`: the named package is exactly that version.
  Lockfile = the one under `<AGENT_ROOT>` that the deploy recipe/Dockerfile installs from (`uv.lock`,
  `poetry.lock`, or a compiled `requirements.txt`; `package-lock.json` or
  `pnpm-lock.yaml` for an npm-scoped off-catalog name). `uv.lock` or
  `poetry.lock`: `grep -n -i -A1 '^name = "<normalized-pkg>"$' <lockfile>`
  (normalized = lowercase, hyphens; also try the underscore form if absent) shows
  `version = "<v>"`. `requirements.txt`: `grep -n -i -A3 '^<pkg>==' requirements.txt`
  shows `<pkg>==<v>` and its `--hash=` lines. Also cite the install command in
  the deploy recipe that reads that lockfile (with `--require-hashes` or the
  manager's equivalent when the hash bullet below applies). No lockfile, the
  package absent, or a deploy that installs around the lockfile is a finding
  routed to build.

  A range in the requirements file, or any other version, is a finding routed
  to build.
- Install-time supply chain: for each spec §4 "Stack security rows" row whose
  BHV column cites build rule 9 hash pins, show that the lockfile or
  requirements file carries hashes for the named dependency (command +
  output, for example the `--hash=` lines of that package). Missing hashes are
  a finding routed to build.
Cross-agent reads and greps (the Delegates, Inbound contracts and Dependents
checks below, and Section 0's delegate gate) run from the REPO ROOT, not from
`<AGENT_ROOT>`. In a workspace, a cross-agent grep that matches nothing is an
error to report (wrong directory or missing artifact), never a pass. The one
legitimate empty result is Dependents ("no orchestrator pins this agent"),
and it counts only when the audit also lists the files the grep searched
(`ls agents/*/docs/agent/spec.md` from the repo root, showing the other
agents' specs); a glob that expands to nothing is the error above.

- Delegates (orchestrators: spec §8 lists at least one delegate). Gate:
  checked in Section 0 before anything runs. Contract: a spec §8 pin that
  reads `pending` → blocker; otherwise the pin must be AMONG the versions on
  the `Served:` line of the delegate's Inbound contracts entry for this caller
  (cite `grep -n "<delegate>-contract@" agents/<this-agent>/docs/agent/spec.md`
  and `grep -n -E "^[-* ]*Served:" agents/<delegate>/docs/agent/interop.md`;
  the pattern tolerates a stray bullet or indent, which is itself a minor
  finding routed to the delegate's interop); a pin not served → blocker.
  Both route to this agent's re-entry: spec, then evals, then build (the
  human's, hook off; build.md deleted or moved and its ratchet line removed,
  so build re-runs with a new `build_start`). Live probe: send the probe
  request for the PINNED version, taken from this agent's own
  `evals/delegates/<delegate>-probe.json` (its `contract` equals the pin;
  evals seeded it from the delegate's published block for that version; a
  file whose `contract` differs from the pin, or a missing file, is a finding
  routed to this agent's evals) — never any other request — to the
  delegate's base URL from THIS agent's deploy configuration (the env/config
  key its delegate client reads; cite the key), authenticated with this
  agent's delegate credential, and validate the response against the pinned
  output schema; cite command and output. Failure → finding routed to the
  delegate (down or off-contract) or to this agent (client wrong). This
  agent's delegate credentials are part of the least-privilege diff above.
  The pins validated here go into the report frontmatter `delegate_contracts`
  (Section 7).
- Inbound contracts (any agent whose interop.md has an Inbound contracts
  section). For each entry, cite the handler file:line in `<AGENT_ROOT>`'s
  code (show the line), the BHV in this agent's spec covering the probe's
  no-side-effect claim, with its eval status in Section 1's run, and one
  block (input schema, output schema, probe request, sample probe response)
  per version on its `Served:` line. Missing → finding routed to this
  agent's design re-entry (design, then spec, evals, build, then interop
  publishes) when the caller is not yet in its design, else to a spec
  re-entry (spec, evals, build, then interop); on this built agent that re-entry is the human's, from their
  own terminal with the hook off (the build skill's
  `references/forge-delegation.md` re-entry steps), deleting or moving its
  `docs/agent/build.md` and removing its line from
  `.claude/hooks/built-agents.txt` so build re-runs with a fresh baseline and
  a new `build_start` (otherwise Section 4 flags the new BHVs and evals as
  unsanctioned).
- Dependents (workspace only; in a one-agent repo record "no other agents").
  What counts is what each orchestrator has SHIPPED. From the repo root, find
  the orchestrators that name this agent, excluding this agent's own spec
  (`grep -n "<this-agent>-contract@" agents/*/docs/agent/spec.md | grep -v "^agents/<this-agent>/"`).
  For each one, read its LAST APPROVED ship-report: if the frontmatter of
  `agents/<orchestrator>/docs/agent/ship-report.md` reads `status: approved`,
  use it; otherwise list its history
  (`git log --format=%h -- agents/<orchestrator>/docs/agent/ship-report.md`)
  and take the first commit, newest first, where
  `git show <sha>:agents/<orchestrator>/docs/agent/ship-report.md` has
  `status: approved` in its frontmatter. Cite the commands and the
  `delegate_contracts` line read. No approved version in that history → the
  orchestrator pins nothing only if it never shipped (cite the empty result
  and `git rev-parse --is-shallow-repository` printing `false`); a shallow
  history, or any other sign that it shipped (e.g. a release tag) with no
  readable approved report → blocker. A version pinned in the last approved
  report that this ship's interop.md no longer lists on its `Served:` line →
  blocker, routed to that orchestrator (re-entry of spec, then evals with
  re-recording, then build — the human's, hook off, its build.md deleted or
  moved and its ratchet line removed — then its interop re-run and a ship
  of the new pin) or to this agent (keep serving the version). A pin only in
  an orchestrator's spec, not yet shipped, is noted, not a blocker: that
  orchestrator's own ship checks it. Order of a bump: this agent serves both
  versions → the orchestrator re-enters spec, evals and build, re-runs
  interop (its outbound row re-recorded with the new pin) and ships the new
  pin → this agent drops the old version (an interop `version` bump).

## Section 4 — Anti-gaming audit

`git diff --word-diff --find-renames <build_start>..HEAD -- <AGENT_ROOT>/evals/ <AGENT_ROOT>/docs/agent/design.md <AGENT_ROOT>/docs/agent/spec.md`
plus, when a commit in the range has a message starting `agent-cycle: workspace move`
and `git show -M --name-status --format= <sha>` lists only `R100` entries plus
`A agent-cycle.yaml` (the conversion creates it), the same three
pre-move paths (repo root) in the pathspec, so the move shows as renames. Each
`R100` entry must map a path `p` to `agents/<AGENT_ROOT name>/p` exactly (for
example `docs/agent/design.md` -> `agents/<name>/docs/agent/design.md`); an
entry mapping anywhere else, an `R` below 100, or any other status is not a
sanctioned move. A commit that passes is sanctioned: record its sha. Apply
the same pathspec to the "first entered git inside the range" check
(`--diff-filter=A --find-renames`).

Mixed-agent commits (workspace only):
`git log --format=%h <build_start>..HEAD -- <AGENT_ROOT>` then, per commit,
`git show --name-only --format= <sha>`: a commit that touches `<AGENT_ROOT>`
and any other `agents/<name>/` is a finding routed to build. Commits touching
only other agents are their work and are ignored.

The diff is taken minus the sanctioned allow-list (the spec §6 Test column),
where `<build_start>` is build.md's frontmatter value: the commit that holds
the approved artifacts, taken before this agent's build.md stub went in (the
hook may already be active, installed by an earlier agent's build). The range
ends at HEAD so nothing after the build slips past; it covers design.md and
spec.md rather than all of docs/agent/ because later phases add their own
files there (skills.md, interop.md, blueprint.html). No `build_start` in
build.md, or any of those artifacts first entering git inside the range
(`git log --diff-filter=A --find-renames --format=%h <build_start>..HEAD -- <AGENT_ROOT>/evals/ <AGENT_ROOT>/docs/agent/design.md <AGENT_ROOT>/docs/agent/spec.md`
prints something, with the pre-move paths added for a sanctioned move) →
there is no baseline to compare against: blocker, routed to build. Zero
unsanctioned changes. Cite the commit range and the diff summary. The Test
column is filled with the hook on: build.md must record the post-fill check (a
dummy edit to `<AGENT_ROOT>/evals/config.yaml`, blocked); confirm it. Evidence
that the builder disabled, renamed or moved the hook, edited its script, or
removed this agent's line from `.claude/hooks/built-agents.txt` during the
build is a blocker routed to build, even with a clean diff, beyond these
sanctioned commits (record each sha): the one-commit install of an absent hook;
the commit adding this agent's own line; (a) a commit whose subject starts
`agent-cycle: hook upgrade` and touches only `.claude/hooks/guard_artifacts.py`
(`HOOK_VERSION` raised or added) and/or `.claude/settings.json` (the guard
command changed to the pinned
`python -I -S "$CLAUDE_PROJECT_DIR/.claude/hooks/guard_artifacts.py"` form),
which is how the human upgrades the hook (a re-ship of a moved agent and any
later hook upgrade pass through it); (b) a commit whose subject starts
`agent-cycle: ratchet follows the move` and whose only change to
`.claude/hooks/built-agents.txt` replaces the `.` line with
`agents/<this agent>/` (when the file first enters git in that commit, it
holds `agents/<this agent>/` and no `.` line). Any other change in those commits is not sanctioned.

## Section 5 — Observability + alarm

- Traces: evidence they arrive (query the backend, or the exporter's local
  log) — cite what was seen, including one span with the spec's per-turn
  attributes AND gen_ai.usage token counters.
- Alarm: the token-spend alarm exists and its threshold equals the economics
  artifact's stated number (when economics exists). Absent economics → note
  it; absent alarm → finding.

## Section 6 — Runbook

Verify docs/runbook.md (or the repo's stated location) against the minimums:
queue/DLQ drain steps, rollback (how to return to the previous version),
kill switch (how to stop the agent NOW), weekly ritual scheduled (suite
re-run + judge spot-validation + corrections mined into new eval cases).
Orchestrators (spec §8 lists at least one delegate) add: the weekly probe per
delegate, sending the pinned version's probe request from this agent's
`evals/delegates/<agent>-probe.json` and comparing the reply with the pinned
schema and that file's golden probe response, and this agent's On failure
path when a delegate's kill switch is used.
Missing or thin → FINDING that references
`references/runbook-template.md` for the owner (or a build re-entry) to
fill. The auditor NEVER writes the runbook.

## Section 7 — Verdict and report

- SHIP: every section green.
- NO-SHIP: any release blocker red, any unsanctioned artifact change, any
  missing chain link, any other finding of blocker severity — each finding with severity (blocker / important /
  minor) and its re-entry route (which phase re-opens). NO-SHIP is the
  pipeline catching what it was built to catch; write it that way.
- Report: docs/agent/ship-report.md with frontmatter (agent_name, version,
  status: draft, date, design_version, spec_version, evals_config_date,
  build_version, interop_version — the interop.md version this ship covers —
  and, for orchestrators, `delegate_contracts: [<agent>-contract@<n>, ...]`,
  the pins this ship validated) + the seven sections, each with its commands
  and evidence.
- The auditor's ONLY write is this report. Human sign-off at the gate →
  status: approved = SHIPPED. Suggest the release tag.
