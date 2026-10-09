# Changelog

All notable changes to the agent-cycle plugin. Semver: minor = new pipeline
skill or new pipeline capability, patch = fixes.

## [0.12.0] — 2026-10-08

### Added
- **Workspace mode:** several independent agents per repository under
  `agents/<name>/`, declared by `agent-cycle.yaml`; one-agent repos are
  unchanged. Every skill resolves `AGENT_ROOT` first
  (`references/agent-root.md`).
- **The anti-gaming hook is a tested file** (`skills/build/assets/guard_artifacts.py`,
  `tests/test_guard_artifacts.py`): freezing is decided per agent from its
  state (build.md present; draft vs approved). Agents come from the
  directories (the root and every `agents/<dir>/`), never from
  `agent-cycle.yaml`, which is append-only.
- **build.md ratchet:** the hook records every built agent in
  `.claude/hooks/built-agents.txt`, so deleting or moving a build.md by any
  route never unfreezes the agent.
- **Settings protection:** the hook is registered as
  `python -I -S "$CLAUDE_PROJECT_DIR/.claude/hooks/guard_artifacts.py"`. It
  blocks any change to that entry or to the `env` key of
  `.claude/settings.json` / `settings.local.json`, and `disableAllHooks`. The
  user's `~/.claude/settings.json` is guarded too (`disableAllHooks` and the
  guard entry; its `env` rule covers only `PATH` and `PYTHON*`, the variables
  that steer the hook's interpreter).
- **Tracked ratchet and human-only git:** `built-agents.txt` is committed with
  the hook, so a fresh clone stays frozen. While any agent is built, merge,
  pull, rebase, revert, cherry-pick, apply, am, reset --hard, stash
  pop/apply/branch, and checkout/restore from another commit over protected
  paths are the human's. Path-less destructive verbs (`git clean`,
  `git stash -u`/`-a`) are blocked at the repo root and in an agent folder;
  give them a path (`git clean -fd src`). Branch switching stays allowed.
- **Hardened paths and shell reading:** file-tool paths are canonicalised
  (junctions, 8.3 names, `\\?\`, trailing dots, NTFS streams). More write
  forms are recognised: PowerShell aliases, `sed`/`perl`/`awk` in-place,
  `git -C`, interpreter here-docs, `bash -c`, globs matched by depth, hard
  links. Only write targets are judged, so reading frozen files (`2>&1`,
  `> results.txt`, `cp evals/x /tmp/`, commit messages naming frozen paths)
  no longer trips it.
- design: new agents in a workspace; conversion commands for a one-agent repo.
  The commands are shown for the human to run from their own terminal, in
  three separate commits: the hook upgrade (with the `-I -S` registration) on
  its own, then the move (pure renames plus `agent-cycle.yaml`), then the
  ratchet, where the `.` line of `built-agents.txt` becomes `agents/<name>/`.
  design stops after showing them and is run again once the human has
  committed.
- Eval cases DES-E07, DES-E08, SPC-E05, BLD-E06, SHP-E05.

### Changed
- build: per-agent baseline commit, build.md stub committed first, writes
  only inside AGENT_ROOT, resource names prefixed per agent. The hook is
  installed in this order, in one commit: script, ratchet, registration last
  (a registered hook whose script is missing blocks every tool call). The
  human-only git verbs list now includes `stash branch`, matching the hook.
- build eval check (`skills/build/evals/cases.json`): the anti-gaming check
  now describes the persistent hook that freezes `evals/`, `design.md` and
  `spec.md` once build.md exists (the spec §6 Test column and a draft build.md
  stay editable), replacing the v0.11 wording about a build-duration hook over
  all of `docs/agent/`. A deliberate eval-text change.
- ship: anti-gaming diff limited to the agent; workspace-move commits
  accepted (subject `agent-cycle: workspace move`, only `R100` renames plus
  the added `agent-cycle.yaml`; the sha is recorded); commits touching two
  agents are findings.

### Upgrade notes
- The hook is now persistent and narrower: only `evals/`, `docs/agent/design.md`
  and `docs/agent/spec.md` freeze (no longer all of `docs/agent/`), from the
  moment build.md exists.
- Hook upgrades are a human step: build never writes `.claude/hooks/`. When
  the installed `HOOK_VERSION` is lower than the plugin's, build stops and
  asks you to rename the hook to `.off`, copy the plugin's file, and rename it
  back. An older hook does not protect `agents/*/`, so upgrade before
  converting a repo to a workspace, and commit the upgrade on its own, before
  the move commit.
- Repos whose `.claude/settings.json` registers the hook without `-I -S`:
  update the command to
  `python -I -S "$CLAUDE_PROJECT_DIR/.claude/hooks/guard_artifacts.py"` and
  commit `.claude/hooks/built-agents.txt` (both by hand; the hook blocks the
  builder from doing either through its own registration).
- Re-entry on a built agent: rename the hook to `.off`, make the change,
  remove the agent's line from `.claude/hooks/built-agents.txt` when its
  build.md is deleted or moved, then rename the hook back.
- Shell writes to an existing build.md are blocked (edit it with file tools).

### Pending graduation
- A real workspace with two agents both taken through build.

## [0.11.0] — 2026-10-08

### Added
- **Stack decision in `design` (Phase E, design.md §8):** four filter
  questions, hard filters from a dated stack catalog (eliminations written),
  2-3 cited candidates, the user picks — no weighted scores. Stale cards
  (>90 days) are re-verified before use; differences logged as catalog drift.
  Details that landed beyond the first plan:
  - A2A never eliminates a card: needing a self-owned `a2a-sdk` server is a
    con on every card; the licensed Agent Server counts only when design §8
    records an accepted license.
  - §5 seams stay stack-neutral; the concrete per-seam binding lives in §8.
  - §8 fields: Filter answers, Set aside (judgment), Mandatory spec security
    rows, Catalog drift (with a Card column).
  - Re-entry path for pre-v0.11 designs: Phase E only (plus Phase D seam
    neutrality if needed).
- **Stack catalog** (`skills/design/references/stacks/`): nine cards —
  pydantic-ai, google-adk, langchain-create-agent, langgraph, deep-agents,
  openai-agents-sdk, crewai, claude-agent-sdk, no-framework — verified
  2026-10-07, every fact URL-cited.
- **Per-stack build bindings** (`skills/build/references/bindings/`): nine
  per-stack bindings, one per catalog card. Every binding meets the generic
  obligations in `_binding-template.md`:
  - queue keyed by session key; ingress dedupe record with
    `processed_at`/`outcome`/`reply` (redelivery protection); persist -> send
    -> ack; own-loop crash marker.
  - pending-record lifecycle with a fresh `approval_id` per pause and
    per-approved-call idempotency keys; `resume_started` marker;
    `awaiting_approval` outcome; deny ends the turn when the spec says so (no
    tool runs after the deny); turn-start repair of
    dangling tool calls.
  - per-turn caps count requested calls (the whole batch) before execution;
    tool-surface preflight (negative control where tools are filtered); the
    runner drives the
    worker's turn handler; "executed" means the wrapper recorded it at body
    entry.
  - numbered spikes, each with a pass test. Build never edits plugin files:
    a binding defect is "STOP and report".
- **`refresh` skill** — maintainer re-verification of cards, bindings and
  index; harvests drift from agent projects; never commits. Gated by a
  version-move rule, marks observed facts, and also harvests design drift and
  build defect records.
- `scripts/check_catalog.py` + tests (39): cards, index and bindings never
  contradict each other.
- **Off-catalog path:** design Phase E step 7, build Step 1 "Off-catalog
  binding", interop and ship.
- New eval cases: DES-E04..E06, BLD-E05, REF-E01..E05, SPC-E02 third run.

### Changed
- `spec` gates on design §8, pins `runtime: <card-id>@<version>` (forms:
  `card@version`, `no-framework@n/a`, `off-catalog:<name>@<version>`), and
  turns the stack's security/data traps into security rows. The card-trap
  check is additive; install-time supply-chain rows feed build rule 9 and
  the ship lockfile check.
- `build` reads the runtime from spec, uses the stack binding, hash-pins
  flagged dependencies; state store decoupled from target (managed Postgres
  such as Supabase valid everywhere, with connection/schema/free-plan rules).
- `interop` takes the A2A path from the stack binding; HITL can never be
  bypassed via A2A; roles are stated per relationship. `ship` checks the
  lockfile runtime pin across `uv.lock`, `poetry.lock` and
  `requirements.txt`.
- Deliberate eval-text changes: ITP-E02 (interop) and DES-E01 check 7
  (design) were reworded on purpose, not by drift.
- Pydantic AI runner mapping rewritten for V2.

### Upgrade notes
- Approved v0.10 designs have no §8: the spec hard-fails until design re-entry
  (Phase E only).
- `build`, `interop` and `ship` now require spec `runtime`.
- The "Runner mapping per framework" section (ADK, Pydantic AI, LangGraph)
  moved from `adapter-bindings.md` into the per-stack bindings.

### Pending graduation
- Stack phase run on a real new agent; one `refresh` run with a genuinely
  changed fact.

## [0.10.1] — 2026-10-07

### Fixed
- **Anti-gaming hook hardened** (`build/references/forge-delegation.md`,
  contributed by Eduardo Ramos): the hook runs through
  `$CLAUDE_PROJECT_DIR` and resolves paths from the payload's `cwd`, so one
  `cd` no longer locks every call out; folder-level shell writes
  (`rm -rf evals`, `mv docs old`, `rm -rf *`, `cd evals && rm ...`) and
  writes to `.claude/hooks/` are blocked; stdin read as UTF-8 (Windows
  cp1252 broke the em-dash match); an unparseable call fails closed. The
  spec §6 Test column is now filled WITH THE HOOK ON — the hook admits an
  Edit/MultiEdit/Write of spec.md only when the sole change is the Test cell
  of `BHV-NNN` rows in §6; the builder never renames or disables the hook.
  Known follow-up: a writing command that merely reads from a frozen folder
  (`pytest evals | tee run.log`) is blocked too — fails closed, to narrow.
- **Build baseline for /ship's diff audit** (`build`, `ship`, contributed by
  Eduardo Ramos): build Step 2 commits the approved design, spec and evals
  before the hook and records `build_start` in build.md's frontmatter; ship
  Section 4 diffs `build_start..HEAD` over `evals/`, design.md and spec.md,
  and a missing baseline (or the artifacts first entering git inside the
  range) is a blocker routed to build. Previously the audit could compare
  the build against itself when the artifacts were never committed.
- Ship wording aligned with both fixes: rule 7, audit-guide Section 4 and
  SHP-E01 now confirm build.md's post-fill hook check instead of a
  "hook-restore when bypassed" step that no longer exists; a builder that
  disabled or moved the hook is a blocker. forge-delegation's second-layer
  sentence names the `build_start..HEAD` range.

## [0.10.0] — 2026-07-29

### Added
- **`review` skill** (transversal 3 of 3 — added to the plan by explicit
  owner decision 2026-07-29): assess ANY existing agent, pipeline-born or
  foreign, against the pipeline's practice frame. Eight dimensions with
  concrete probes (specification/Goodhart, contracts & tiers, security
  surfaces from REAL inputs, loop caps, evals-or-hope, observability,
  economics, ops), evidence discipline (file:line or explicit not-found —
  invented architecture banned), findings with severity + the pipeline phase
  that fixes each, and a remediation map grouped by phase that doubles as
  the pipeline entry proposal. The one chain-gate-free skill; read-only on
  the target; only write: docs/agent/review.md. Distilled, self-contained
  successor of the author's personal agent-design knowledge skill.
- EDD eval suite (`skills/review/evals/`): REV-E01 positive-foreign (8-check
  contract with seeded-defect ground truth), REV-E02 pipeline-born
  (artifact-vs-code divergence), REV-E03 gate-negative, REV-E04
  trigger-negative (non-agent code must not fire).

### Pending graduation
- `review` run against a real foreign agent — tag `review-v0.1` when the
  dogfood passes.

### Fixed
- Boundary routing across the audit family: `design`'s review exclusion now
  routes to `agent-cycle:review` (was "outside the pipeline" — stale once
  review joined); `ship` excludes arbitrary-agent assessment (review's job);
  `review`'s audit frame gained the absent-metric probe and the walkable
  artifact-vs-code baseline mechanics for pipeline-born targets.
- README rewritten: per-skill descriptions with use / do-NOT-use guidance,
  full-cycle mermaid diagram (vertical phases vs horizontal transversals,
  re-entry ladder), core contracts section.

## [0.9.0] — 2026-07-29

### Added
- **`blueprint` skill** (transversal 2 of 2 — completes the original 9-skill
  pipeline): one self-contained, client-shareable HTML snapshot of the agent
  rendered progressively from whatever artifacts exist (design gate only) —
  PEAS/harness, tier-colored tools, security surfaces, eval coverage,
  economics embedded verbatim (never recomputed), pipeline progress bar,
  ship verdict when present. Zero external references, zero required
  JavaScript, print-ready, sanitized by default (env names yes, values
  never). Dated snapshot carrying its source versions — regenerable, no
  approval status of its own. Only write: docs/agent/blueprint.html.
- EDD eval suite (`skills/blueprint/evals/`): BLP-E01 positive-progressive
  (7-check contract incl. grep-verified self-containment), BLP-E02
  gate-negative, BLP-E03 post-build edge (real topology, ship verdict),
  BLP-E04 trigger-negative (generic diagramming must not fire).

### Pending graduation
- `blueprint` run against the real agent — tag `blueprint-v0.1` when the
  dogfood passes (runnable TODAY: pre-build progressive render qualifies).

## [0.8.1] — 2026-07-29

### Fixed
- **`design`/`spec`**: removed the hard reference to a user-workspace
  `agent-design` skill (v0.4.1 lesson applied retroactively) — both skills'
  references are self-contained; operator-loaded knowledge skills may inform
  judgment but none is required. DES-E02 check text updated accordingly.
- **`build`**: coding-standards clause — operator-loaded standards skills
  govern style when present; the pipeline's own hard floor (extra=forbid,
  TDD, pinned deps, errors-as-observations, no secrets) always applies.

### Added
- **`build`**: concrete LangGraph runner/binding mechanics in
  adapter-bindings.md (Postgres checkpointer behind the repository interface,
  thread_id per user, interrupt() as the HITL gate binding, event-stream
  trajectory capture, recursion_limit + own tool-call counter for the spec's
  two distinct caps).

## [0.8.0] — 2026-07-29

### Added
- **`ship` skill** (phase 7 of 7 — the closing mechanical audit): full-chain
  gate (conditional-phase decisions required, none/skip valid), live suite
  re-run as the only accepted green (build.md is claim, not evidence),
  end-to-end traceability, security re-verification (adversarial /
  least-privilege diff / secret scan incl. history / ingress spot-checks),
  anti-gaming word-diff audit over the build's commit range, observability +
  token-counter + economics-threshold alarm checks, runbook verification
  against a shipped template (auditor never writes it), explicit SHIP /
  NO-SHIP verdict with per-finding severity + re-entry routes. The auditor's
  only write: docs/agent/ship-report.md.
- EDD eval suite (`skills/ship/evals/`): SHP-E01 positive (9-check contract),
  SHP-E02 gate-negative (missing build / missing conditional decisions),
  SHP-E03 no-ship edge (red blocker → complete audit, NO-SHIP, no fixing),
  SHP-E04 trigger-negative (generic deployment must not fire).

### Pending graduation
- `ship` skill run against the real agent — tag `ship-v0.1` when the dogfood
  audit completes.

## [0.7.0] — 2026-07-28

### Added
- **`interop` skill** (phase 6 of 7, strongly conditional): per-relationship
  entry test (result → tool/MCP vs responsibility → A2A; the GOTO problem
  named); skip as a recorded successful outcome with re-visit triggers; when
  warranted: Agent Card (capabilities / security & compliance / interaction
  schemas), counterpart-security posture (remote agents are untrusted; tiers
  travel; delegation never bypasses HITL), executor binding per runtime (ADK
  documented first, custom handlers via build re-entry), registry decision.
  Artifact: docs/agent/interop.md (+ agent-card.json when authored).
- EDD eval suite (`skills/interop/evals/`): ITP-E01 positive-skip (real
  dogfood expectation), ITP-E02 positive-a2a (5-check contract), ITP-E03
  gate-negative (two branches), ITP-E04 trigger-negative (generic API
  integration must not fire).

### Pending graduation
- `interop` skill run against the real agent — tag `interop-v0.1` when the
  dogfood passes (expected outcome: decision skip, justified).

## [0.6.0] — 2026-07-28

### Added
- **`skills` skill** (phase 5 of 7, conditional): entry test per capability
  (procedural on-demand vs tool+static), "none" as a recorded successful
  outcome with re-visit triggers, EDD-first authoring for warranted skills
  (routing-grade descriptions, >=90% measured trigger accuracy, co-loaded
  regression against the agent's own eval suite), draft→action authority
  ladder (pass^k + human approval), declared runtime binding (harness-native
  or build's loader — never improvised). Artifact: docs/agent/skills.md.
- EDD eval suite (`skills/skills/evals/`): SKL-E01 positive-none (real
  dogfood expectation), SKL-E02 positive-authored (7-check contract),
  SKL-E03 gate-negative (two branches), SKL-E04 trigger-negative (generic
  skill authoring must not fire).

### Pending graduation
- `skills` skill run against the real agent — tag `skills-v0.1` when the
  dogfood passes (expected outcome: decision none, justified).

## [0.5.0] — 2026-07-28

### Added
- **`build` skill** (phase 4 of 7 — the only code-producing phase): approved
  design+spec+evals → running agent. Rails before code (anti-gaming PreToolUse
  hook installed and verified before the first source file); the spec's
  runtime is law (no plugin-favorite framework at runtime); core/adapter split
  over 5 bindings (self-contained reference for VPS/AWS/GCP); eval RUNNER as
  the pipeline's definition of green (immutable evals/, fixtures incl.
  messages[] and harness_condition, pass^k thresholds, exit-code contract);
  OTel telemetry incl. gen_ai.usage token counters (closes the economics
  calibration gap); mechanical forge-master PRD derivation (BHV ACs verbatim,
  human-approved plan) with a direct-TDD path for trivial builds; secrets/
  pinning/slopsquatting hygiene; build.md DoD record + spec §6 Test column as
  the only sanctioned spec write.
- EDD eval suite (`skills/build/evals/`): BLD-E01 positive (11-check
  contract), BLD-E02 gate-negative (missing evals + stale chain), BLD-E03
  trivial-direct edge, BLD-E04 trigger-negative.

### Pending graduation
- `build` skill run against the real agent — tag `build-v0.1` when the dogfood
  goes green.

## [0.4.1] — 2026-07-28

### Fixed
- **`economics`**: price-source discovery no longer assumes or asks about
  user-maintained vaults/knowledge bases (over-fit to one workspace). New
  priority: user-provided figures → provider pricing pages via web (URL +
  retrieval date, the default) → UNKNOWN. Compiled sources are used only when
  the user offers them spontaneously; proactively asking where they live is now
  an eval FAIL (ECO-E01 check 3 + scoring anchor updated).

## [0.4.0] — 2026-07-28

### Added
- **`economics` skill** (transversal 1 of 2): monthly cost analysis for a
  designed agent. Dated unit prices (workspace sources first, never from model
  memory), tokens-first scenario model with auditable formulas and band totals,
  mandatory sensitivity (tier swap + volume) and break-even (client price or
  monetized internal metric), token-spend alarm threshold as the /ship
  contract, calibration mode with delta tables (estimates never silently
  overwritten). Artifact: docs/agent/<agent_name>-economics.md.
- EDD eval suite (`skills/economics/evals/`): ECO-E01 positive (10-check
  contract), ECO-E02 gate-negative (two branches), ECO-E03 calibration edge,
  ECO-E04 trigger-negative (generic API pricing must not fire).

### Pending graduation
- `economics` skill runs against the real agent — tag `economics-v0.1` when
  the dogfood passes.

## [0.3.0] — 2026-07-28

### Added
- **`evals` skill** (phase 3 of 7): approved spec.md → framework-agnostic eval
  suite BEFORE any code. Golden cases pin BHV-NNN@spec_version; method mix
  (deterministic / llm_judge with anchored rubrics / adversarial per untrusted
  surface, >=2 realistic payloads incl. end-user language); per-tier thresholds
  (pass^k destructive); release blockers lifted from the spec's hard
  constraints; red-by-design rule; suite is pure data — the runner belongs to
  /build. Sanctioned external write: exactly the spec §6 Eval column.
- EDD eval suite (`skills/evals/evals/`): EVL-E01 positive (11-check contract),
  EVL-E02 gate-negative (two branches), EVL-E03 non-automatable edge,
  EVL-E04 trigger-negative.

### Pending graduation
- `evals` skill runs against the real agent — tag `evals-v0.1` when the dogfood
  passes.

## [0.2.0] — 2026-07-28

### Added
- **`spec` skill** (phase 2 of 7): approved design.md → executable spec.md.
  Gherkin scenarios with BHV-NNN ids (happy/wrong/edge per capability), final
  tool contracts (docstring-as-interface, extra=forbid schemas, distinct-
  operation counting, action tiers with justified changes), conversation rules
  incl. spec-level decisions (debounce), design-anchored security model with
  mandatory injection scenarios per untrusted surface, least-privilege + PII
  rules, data schemas, traceability table. Hard gate on design approval; design
  is settled law (re-entry ladder for changes).
- EDD eval suite (`skills/spec/evals/`): SPC-E01 positive (13-check contract),
  SPC-E02 gate-negative (two hard-fail branches), SPC-E03 trivial-agent edge,
  SPC-E04 trigger-negative (generic Gherkin help must not fire).

### Pending graduation
- `spec` skill eval runs against the real agent — tag `spec-v0.1` when the
  dogfood passes.

## [0.1.0] — 2026-07-28

### Added
- Plugin scaffold: `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json`
  (installable as a GitHub marketplace: `alanvaa06/agent-cycle`).
- **`design` skill** (phase 1 of 7): PEAS interview → approvable
  `docs/agent/design.md` with environment classification, harness decision,
  deployment intent + 3 portability seams, NO-goals, open questions. Human gate;
  never self-approves.
- EDD eval suite for the skill itself (`skills/design/evals/`): 3 cases
  (DES-E01 positive / DES-E02 trigger-negative / DES-E03 partial-PEAS edge),
  11-check contract on the positive case, per-check results log.
- Design doc for the full pipeline (`docs/superpowers/specs/`): 7 gated phases +
  2 transversals (economics, blueprint), re-entry ladder, anti-gaming rules,
  forge-master delegation.

### Pending graduation
- `design` skill eval runs (DES-E01..E03) against a real agent — tag
  `design-v0.1` lands when the dogfood passes.
