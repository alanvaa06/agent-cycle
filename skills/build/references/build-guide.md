# Build guide — agent-cycle:build

The only phase that produces code. Order matters; the rails (hook, runner,
DoD) are not optional at any size.

## Step 0 — Gate check

Hard-fail (write nothing, say why, stop) unless ALL hold:
- `docs/agent/design.md` approved; `docs/agent/spec.md` approved with
  `design_version` == design's `version`; `evals/config.yaml` approved with
  `spec_version` == spec's `version`. A stale link → re-entry ladder.
- If `docs/agent/<agent_name>-economics.md` exists: read it. Carry its
  token-spend alarm threshold and any telemetry requirements (e.g. token
  counters) into the build as obligations.

## Step 1 — Fix the runtime and target (no debate)

The spec states the runtime (language, agent framework, model route) and the
design states the deployment target. BUILD EXACTLY THAT. The plugin's own
adapter docs may cover other frameworks more deeply — irrelevant: the spec is
law. Wanting a different runtime is a re-entry dispute on the spec, never a
silent swap. Record both in build.md frontmatter.

## Step 2 — Install the anti-gaming rail FIRST

Before any source file exists, install the hook per
`references/forge-delegation.md` §Hook: the target repo blocks edits to
`evals/**` and `docs/agent/**` (allow-list: `docs/agent/build.md`, and spec.md
ONLY for the §6 Test column at the end). Verify it triggers (attempt a dummy
edit, see it blocked). If the harness has no hook mechanism, fall back to the
documented git-diff audit contract in the same file — but say so in build.md.

## Step 3 — Scaffold: core/adapter split

```
src/
  agent/        loop, tools, contracts, repository INTERFACES — imports the
                agent framework and stdlib ONLY, never infra SDKs
  adapters/<target>/   the 5 bindings (references/adapter-bindings.md):
                ingress · queue · state impl · secrets · deploy recipe
tests/          unit tests + the eval-runner integration entrypoint
```

Dependencies pinned from the first commit (exact versions / lockfile). Vetted
registries only — hallucinated package names are an attack surface
(slopsquatting): verify every dependency exists and is the canonical name
before installing.

Coding standards: if the operator has coding-standards skills loaded (user or
org), they govern style and idiom. The pipeline's own hard floor, always:
typed contracts with extra=forbid, TDD, pinned deps, errors-as-observations,
no secrets in code.

## Step 4 — State and contracts first

Implement the spec §Data schemas behind the repository interfaces (the
design's sessions seam). Then the Pydantic models for every tool contract:
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
instantly. Step and tool-call caps are counted SEPARATELY in the loop (they
are distinct limits in the spec), even if the framework offers only one.

## Step 7 — Adapter

The 5 bindings for the design's target per `references/adapter-bindings.md`.
Ingress enforces the spec's channel security (signature over raw body,
allowlist, dedupe) BEFORE anything reaches the loop. Secrets per the adapter
pattern; update `.env.example` to match reality.

## Step 8 — The eval runner

Build the runner that makes `evals/` executable (mapping per
`references/adapter-bindings.md` §Runner):
- Loads golden/ + adversarial/ + config.yaml AS-IS. Any edit to evals/ to
  "make a test pass" is the cardinal violation — dispute via re-entry instead.
- Materializes fixtures: world state, messages[] sequences (debounce),
  harness_condition (force_step_cap, tool_always_errors) via injected fakes.
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
   draft, date, design_version, spec_version, evals_config_date, runtime, target),
   runner command, suite summary, smoke results, delegation decision,
   deviations/additions (e.g. telemetry fields added).
4. Fill spec §6 Test column (ONLY that column).
5. Human gate → status: approved. Hand off: "/ship audits this build record."
