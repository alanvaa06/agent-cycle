---
name: build
description: "Phase 4 of the agent-cycle pipeline — the only phase that produces code: turn approved design.md + spec.md + evals/ into a running agent (invariant core + deployment adapter), an eval runner whose exit code is the pipeline's green, forge-master delegation for non-trivial builds, OTel telemetry with token counters. Use when the user wants to build/implement a pipelined agent — 'build the agent', 'siguiente fase del pipeline', 'implement the whatsapp agent'. Do NOT use without approved design+spec+evals (run the earlier phases first), nor for generic app development outside the pipeline, nor to modify evals or specs (frozen artifacts; re-entry ladder)."
---

# agent-cycle:build — From Paper to Green

Everything upstream was a contract; this phase honors it. The suite that has
been red by design goes green here, through a runner — never through opinion.

## Hard rules

1. TRIPLE GATE + chain: design, spec, evals all approved; design_version /
   spec_version links consistent. Stale → re-entry, not a build. Economics
   read when present (alarm + telemetry obligations).
2. THE SPEC'S RUNTIME IS LAW. Scaffold exactly the runtime/target the spec and
   design fixed — the plugin has no favorite framework at runtime. Wanting
   otherwise is a re-entry dispute.
3. RAILS BEFORE CODE: the anti-gaming hook (blocks evals/ and docs/agent/
   edits) is installed and verified BEFORE the first source file. The builder
   NEVER edits evals or specs — disputes go to the human via the re-entry
   ladder.
4. Core/adapter split: agent code imports no infra SDKs; the adapter owns the
   5 bindings (ingress, queue, state, secrets, deploy). Ingress enforces
   signature-over-raw-body, allowlist, dedupe BEFORE the loop.
5. Tools = the spec's contracts exactly: verbatim docstrings, extra=forbid,
   errors-as-observations, tiers structural. None added, none dropped.
6. THE RUNNER IS THE GREEN: it consumes evals/ as immutable data, materializes
   fixtures (messages[], harness_condition), verifies trajectory/asserts/
   forbidden/outcome, applies pass^k thresholds, and exits non-zero on any
   failure. No suite-green claim without the runner's exit code.
7. Telemetry: OTel GenAI per turn INCLUDING gen_ai.usage token counters —
   economics cannot calibrate without them; note them as a spec addition if
   the spec's list predates them.
8. Delegation: non-trivial builds derive a forge PRD mechanically (BHV ACs
   verbatim + runner as test command) and the forge plan gets HUMAN approval
   before running. Trivial all-safe builds may go direct TDD with a recorded
   justification. Same finish line either way.
9. Secrets never in code; deps pinned from the first commit; registries
   vetted (slopsquatting defense).
10. Writes: src/, tests/, the runner, the hook config, docs/agent/build.md,
    and ONLY the Test column of spec §6 (after green, sanctioned at the
    gate). DoD = suite green + adapter smoke, recorded in build.md,
    status: draft until the explicit human gate. Never self-approve.

## Workflow

1. Read `references/build-guide.md`; run steps 0→9 in order — the rails
   (Step 2) come before any code.
2. Bindings and runner mapping from `references/adapter-bindings.md`;
   delegation and the hook from `references/forge-delegation.md`.
3. Finish line: runner green (pass^k) + smoke test + build.md record + Test
   column + gate summary (suite result, smoke result, delegation decision,
   deviations).
4. Explicit approval → build.md status: approved. Feedback → fix, re-run,
   re-present.
5. Hand off: "/ship audits this build record; /blueprint can now render the
   real graph."

## Failure modes to avoid

- Building on a stale chain, or scaffolding a runtime the spec didn't fix
  (rules 1-2).
- Writing code before the hook exists (rule 3).
- "Fixing" a failing eval by editing it — the cardinal violation (rules 3, 6).
- Infra imports inside src/agent/, or a tool the spec never declared
  (rules 4-5).
- Declaring the suite green from a transcript instead of the runner's exit
  code (rule 6).
- Skipping token counters because the spec's telemetry list predates them
  (rule 7).
- Running forge without the human approving the plan (rule 8).
- A secret in a commit, or an unpinned dependency (rule 9).
