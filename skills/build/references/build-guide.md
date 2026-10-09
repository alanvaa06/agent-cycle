# Build guide — agent-cycle:build

The only phase that produces code. Order matters; the rails (hook, runner,
DoD) are not optional at any size.

## Step 0 — Gate check

Resolve AGENT_ROOT per the agent-cycle plugin's references/agent-root.md; every path below is relative to it.

Hard-fail (write nothing, say why, stop) unless ALL hold:
- `docs/agent/design.md` approved; `docs/agent/spec.md` approved with
  `design_version` == design's `version`; `evals/config.yaml` approved with
  `spec_version` == spec's `version`. A stale link → re-entry ladder.
- spec.md frontmatter `runtime` present in one of the three forms
  (`<card-id>@<version>`, `no-framework@n/a`, `off-catalog:<name>@<version>`);
  missing -> hard-fail, route to design re-entry (§8) and a spec version bump.
- If `docs/agent/<agent_name>-economics.md` exists: read it. Carry its
  token-spend alarm threshold and any telemetry requirements (e.g. token
  counters) into the build as obligations.

## Step 1 — Fix the runtime and target (no debate)

The spec's frontmatter `runtime:` names the stack; the design states the
deployment target. BUILD EXACTLY THAT. The value takes one of three forms:
`<card-id>@<version>`, `no-framework@n/a`, or `off-catalog:<name>@<version>`.
Parse it by stripping a leading `off-catalog:` prefix, then splitting on the
LAST `@` (an off-catalog name can be npm-scoped, like `@scope/pkg@1.2.3`). The spec is law; the plugin has no favorite
framework. Wanting a different runtime is a re-entry dispute on the design
(§8), never a silent swap. Record runtime and target in build.md frontmatter.

Catalog runtime (`<card-id>@<version>` or `no-framework@n/a`): open the
binding at `references/bindings/<card-id>.md` (the agent-cycle plugin's
`skills/build/references/bindings/<card-id>.md` when the build runs in the
target repo; `no-framework` has a binding too). Its sections govern sessions,
HITL, caps, model provider, telemetry (including switching off vendor egress),
the eval-runner mapping and A2A/MCP for this build, and it holds the pins and
the spikes.

Version: install EXACTLY the spec's version. For `no-framework@n/a` the
version is n/a and the pins live in the binding. If the spec's version
differs from the binding's `version_pinned` (design may have re-checked a newer
release), the build records the difference in build.md, re-resolves the lock for
the spec's version (the binding's transitive pins hold only at
`version_pinned`), and treats the binding's "observed" facts as unverified
until their spikes pass. The spikes always run (Step 4); on a version
difference EVERY spike of the binding runs on the spec's version. A failing
spike is a re-entry (per the binding's own failure path), never a silent
downgrade to `version_pinned`. Facts marked "re-observe" count as unverified at
ANY version until their spike passes, and their spikes always run.

Off-catalog runtime (`off-catalog:<name>@<version>`): no binding exists.
Derive the same eight sections (Sessions and state, HITL gate, Caps, Model
provider, Telemetry, Eval runner mapping, A2A and MCP, Pinned version and
traps) from design §8's cited research, per
`skills/build/references/bindings/_binding-template.md` of the agent-cycle
plugin: answer every placeholder obligation, including spikes with pass tests
and failure paths. Write them into build.md under "Off-catalog binding", and note in the gate summary that `agent-cycle:refresh`
should draft a card.

## Step 2 — Install the anti-gaming rail FIRST

Baseline first: /ship's anti-gaming audit diffs the approved artifacts from
the commit before the build, so they must be in git before the build touches
anything.
- Not a git repo → ask the human whether to `git init`; no repo, no build.
- `git status --porcelain -- <AGENT_ROOT>/docs/agent/design.md <AGENT_ROOT>/docs/agent/spec.md <AGENT_ROOT>/evals/`
  prints anything, or `git ls-files` misses one -> commit exactly those paths
  (plus `agent-cycle.yaml` when this agent's entry is uncommitted):
  `git add -- <paths>` then
  `git commit -m "Approved design, spec and evals (<agent_name>)" -- <paths>`.
- Record `git rev-parse --short HEAD` as `build_start`.
- Write `<AGENT_ROOT>/docs/agent/build.md` as a stub (`status: draft`,
  `build_start`) and commit it alone, before any source file exists. Its
  existence freezes this agent's evals, design and spec.
- Hook: install when absent: the script, `.claude/hooks/built-agents.txt`
  seeded with this agent's prefix, and the pinned `python -I -S` registration
  in `.claude/settings.json`, all committed together in ONE commit. If the
  installed `HOOK_VERSION` is lower than the plugin's, STOP and ask the human
  to upgrade it from their own terminal (rename to `.off`, copy the plugin's
  file, rename back). Build never writes `.claude/hooks/` once the hook
  exists. Otherwise verify it is active (a dummy edit to
  `<AGENT_ROOT>/evals/config.yaml` is blocked), and commit `built-agents.txt`
  when the hook has added this agent's line (forge-delegation.md). While any
  agent is built, the git verbs that rewrite the tree (merge, pull, rebase,
  revert, cherry-pick, apply, am, reset --hard, stash pop/apply) are the
  human's.

## Step 3 — Scaffold: core/adapter split

Every file this build writes lives inside AGENT_ROOT (source, tests, lockfile, deploy recipe). Shared infrastructure is reached through configuration, never written outside AGENT_ROOT.

```
src/
  agent/        loop, tools, contracts, repository INTERFACES — imports the
                agent framework and stdlib ONLY, never infra SDKs
  adapters/<target>/   the 5 bindings (references/adapter-bindings.md):
                ingress · queue · state impl · secrets · deploy recipe
tests/          unit tests + the eval-runner integration entrypoint
```

Dependencies pinned from the first commit (exact versions / lockfile).
Hash pins (`--require-hashes`) are mandatory when the spec's §4 "Stack
security rows" carry an install-time supply-chain row (an install-time
supply-chain row: its BHV column cites build rule 9 instead of a scenario), or
when the stack card (the agent-cycle plugin's
`skills/design/references/stacks/<card-id>.md`) tags as a `[security]` trap a
dependency that the build installs, directly or transitively (LiteLLM today): generate the lock with hashes and install
with `pip install --require-hashes -r requirements.txt`, or the lockfile
manager's equivalent (for example `uv pip install --require-hashes -r
requirements.txt`). /ship checks the lockfile. Vetted
registries only — hallucinated package names are an attack surface
(slopsquatting): verify every dependency exists and is the canonical name
before installing.

Coding standards: if the operator has coding-standards skills loaded (user or
org), they govern style and idiom. The pipeline's own hard floor, always:
typed contracts with extra=forbid, TDD, pinned deps, errors-as-observations,
no secrets in code.

## Step 4 — State and contracts first

Before anything below: run the binding's spikes (the ones its "Sessions and
state" and other sections number, each stated as running at this step) and
record each one's pass/fail in build.md. Off-catalog: the spikes you derived in
"Off-catalog binding". Spikes run as scratch harnesses under `tests/spikes/`;
credentials and the store DSN come from an uncommitted `.env` the human
supplies (ask; never commit it). A spike whose pass test needs a later step's
component (tools, loop, worker handler) runs now as a scratch harness and
again once that component exists; record both results.

A store spike (sessions/store) that fails STOPS the build and routes to a
design re-entry on the sessions seam, per the binding's own failure path. A
binding defect (any other spike failing because the binding is wrong) -> STOP,
record it in build.md, and report it to the human as a plugin fix
(`agent-cycle:refresh` or the maintainer); the build never edits plugin files.
A spike for a seam the design does not use is recorded `n/a: <reason>`, which
is distinct from "not run"; the build does not pass Step 4 with an unrun spike
that is not `n/a`.

Implement the spec §Data schemas behind the repository interfaces (the
design's sessions seam), plus the fields the binding's Sessions and state and
HITL gate sections add (dedupe `processed_at`/`outcome`/`reply`; pending
`approval_id`/`requested_at`/`resume_started`; turn status). Record them in
build.md as additions for the next spec bump, as with token counters. Then the Pydantic models for every tool contract:
`extra="forbid"`, field constraints as specced. TDD: schema tests first
(unknown field → rejected; constraint violations → rejected).

## Step 5 — Tools

One by one, TDD: docstring VERBATIM from the spec; errors caught inside and
returned as observations (test with a deliberately failing double); untrusted
outputs wrapped per the spec's envelope; tier respected structurally (a
recipient-less send stays recipient-less). No tool beyond the spec's
inventory.

## Step 6 — Loop

The spec's loop with the design's caps as CODE (max steps, max tool calls,
wall clock), explicit exits (answer / cap → single failure reply / tool error
policy), outcome recording per the spec's telemetry enum. Telemetry: OTel
GenAI spans per turn — attributes from the spec PLUS
`gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens` (economics'
calibration depends on them; emit even if the spec's telemetry list predates
them and note it in build.md as an addition for the next spec bump).
Debounce/timing mechanics are built against an injectable clock/scheduler
seam from the start — the eval runner replays messages[] offsets through it
instantly. Step and tool-call caps are counted SEPARATELY (native or own
counter, as the binding's Caps section says; they are distinct limits in the
spec), even if the framework offers only one. The turn statuses the binding
adds (`running`, `awaiting_approval`) are recorded in build.md the same way
when the spec's enum lacks them.

Build the worker's single turn handler per the binding's HITL gate (numbered
sequence), Sessions and state (commit order, pending-record lifecycle, crash
marker) and Caps (turn-start repair) sections; it lives in `src/agent/` against
the repository interface so Step 8 can drive it.

## Step 7 — Adapter

The 5 bindings for the design's target per `references/adapter-bindings.md`
(target) and `references/bindings/<card-id>.md` (stack; off-catalog: build.md's
Off-catalog binding). Ingress enforces the spec's channel security (signature
over raw body, allowlist, dedupe, plus the worker's `processed_at` redelivery
check from adapter-bindings.md's universal rules) BEFORE anything reaches the
loop. Secrets per the adapter
pattern; update `.env.example` to match reality.

## Step 8 — The eval runner

Build the runner that makes `evals/` executable (mapping per
`references/bindings/<card-id>.md` § Eval runner mapping; off-catalog:
build.md's Off-catalog binding):
- Loads golden/ + adversarial/ + config.yaml AS-IS. Any edit to evals/ to
  "make a test pass" is the cardinal violation — dispute via re-entry instead.
- Materializes fixtures: world state, messages[] sequences (debounce),
  harness_condition (force_step_cap, tool_always_errors) via backend doubles,
  never a swapped tool; the runner drives the worker turn handler on an
  in-memory repository and runs the tool-surface preflight, per the binding's
  Eval runner mapping.
- Verifies per case: trajectory (EXACT / IN_ORDER / ANY_ORDER), asserts,
  forbidden (absence), outcome enum; llm_judge cases scored against their
  rubric with the judge model the rubric names.
- Applies config.yaml thresholds: pass^k tiers rerun k times, all green.
- Exit code: 0 only if every case meets its threshold; non-zero otherwise,
  with a per-case report. This exit code is the pipeline's definition of
  green — forge's, /ship's, and yours.

## Step 9 — Close the loop: forge or direct

Decide per `references/forge-delegation.md`: non-trivial → derive the PRD
mechanically, present the forge plan for HUMAN approval, run forge-run with
the eval runner as its test command. Trivial (few tools, all safe, small
suite) → direct TDD to green, one-line justification in build.md.

Either way the finish line is identical:
1. Eval suite GREEN via the runner (pass^k satisfied) — paste the summary
   into build.md.
2. Adapter smoke test: service starts, health endpoint answers, one simulated
   end-to-end webhook roundtrip locally — record the commands + results.
3. Write `docs/agent/build.md`: frontmatter (agent_name, version, status:
   draft, date, design_version, spec_version, evals_config_date, runtime, target,
   build_start),
   runner command, suite summary, smoke results, spike results (and the
   spec-vs-binding version difference, if any), delegation decision,
   deviations/additions (e.g. telemetry fields added).
4. Fill spec §6 Test column (ONLY that column).
5. Human gate → status: approved. Hand off: "/ship audits this build record."
