# Audit guide — agent-cycle:ship

Mechanical, not creative. Every section: run the command, cite it, summarize
its output, verdict the check. No command → no check. Complete ALL sections
even after a red — the report is a full picture, not a first-failure abort.

## Section 0 — Gate

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
  `off-catalog:` prefix and split on the LAST `@`. Show the lockfile line
  (command + output) for each case:
  - `<card-id>@<version>`: the lockfile line for the card's package (named by
    the agent-cycle plugin's `skills/build/references/bindings/<card-id>.md`,
    its frontmatter and "Pinned version and traps" list) equals exactly the
    spec's version.
  - `no-framework@n/a`: every pin the `no-framework` binding lists is exact
    in the lockfile (hashed where the next bullet requires it).
  - `off-catalog:<name>@<version>`: the named package is exactly that version.
  Any range, or any other version, is a finding routed to build.
- Install-time supply chain: for each spec §4 "Stack security rows" row whose
  BHV column cites build rule 9 hash pins, show that the lockfile or
  requirements file carries hashes for the named dependency (command +
  output, for example the `--hash=` lines of that package). Missing hashes are
  a finding routed to build.

## Section 4 — Anti-gaming audit

`git diff --word-diff <build_start>..HEAD -- evals/ docs/agent/design.md docs/agent/spec.md`
minus the sanctioned allow-list (the spec §6 Test column), where
`<build_start>` is build.md's frontmatter value: the commit that holds the
approved artifacts, taken before the hook went in. The range ends at HEAD so
nothing after the build slips past; it covers design.md and spec.md rather
than all of docs/agent/ because later phases add their own files there
(skills.md, interop.md, blueprint.html). No `build_start` in build.md, or any
of those artifacts first entering git inside the range
(`git log --diff-filter=A --format=%h <build_start>..HEAD -- evals/ docs/agent/design.md docs/agent/spec.md`
prints something) → there is no baseline to compare against: blocker, routed
to build. Zero unsanctioned changes. Cite the commit range and the diff
summary. The Test column is filled with the hook on: build.md must record the
post-fill check (a dummy edit to `evals/config.yaml`, blocked); confirm it.
Evidence that the builder disabled, renamed or moved the hook during the
build is a blocker routed to build, even with a clean diff.

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
