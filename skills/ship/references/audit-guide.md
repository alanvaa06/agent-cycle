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
Section 5's expected value). Any gap → refuse, name the phase to run,
write nothing.

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
Missing or thin → FINDING that references
`references/runbook-template.md` for the owner (or a build re-entry) to
fill. The auditor NEVER writes the runbook.

## Section 7 — Verdict and report

- SHIP: every section green.
- NO-SHIP: any release blocker red, any unsanctioned artifact change, any
  missing chain link — each finding with severity (blocker / important /
  minor) and its re-entry route (which phase re-opens). NO-SHIP is the
  pipeline catching what it was built to catch; write it that way.
- Report: docs/agent/ship-report.md with frontmatter (agent_name, version,
  status: draft, date, design_version, spec_version, evals_config_date,
  build_version) + the seven sections, each with its commands and evidence.
- The auditor's ONLY write is this report. Human sign-off at the gate →
  status: approved = SHIPPED. Suggest the release tag.
