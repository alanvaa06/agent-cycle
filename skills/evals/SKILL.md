---
name: evals
description: "Phase 3 of the agent-cycle pipeline: turn an APPROVED docs/agent/spec.md into a framework-agnostic eval suite (evals/: golden cases citing BHV-NNN@version, adversarial cases per untrusted surface, rubrics, config.yaml with per-tier pass^k thresholds) BEFORE any agent code exists. Use when the user wants the eval suite for a specced agent — 'build the evals', 'siguiente fase', 'eval suite for the agent'. Do NOT use without an approved spec.md (run agent-cycle:spec first), nor for writing agent code or runners (that is agent-cycle:build), nor for generic unit-test writing outside the pipeline."
---

# agent-cycle:evals — Eval Suite Before Code

Evals written after the build validate what was built; written before, they ARE
the executable functional spec. All of them failing at first is correct:
red before green, at agent level.

## Hard rules

1. GATE FIRST: hard-fail if spec.md is missing or not approved, or if its
   design_version is stale vs the design. Write nothing. Name the gate.
2. The spec is settled law. Evals test the spec — they never reinterpret it.
   An ambiguous BHV is a dispute for the re-entry ladder, not a creative eval.
3. FULL COVERAGE: every BHV gets a case (bhv_ref pins BHV-NNN@spec_version) or
   a written gap justification in config.yaml. Counts must reconcile.
4. METHOD MIX is mandatory: deterministic where the Then is observable,
   llm_judge with anchored rubrics where it is judgment, adversarial for every
   untrusted surface — never judge-only.
5. Adversarial: >=2 realistic payloads per untrusted surface, including the
   end-user's real language when the spec calls for it. Gibberish tests nothing.
6. The suite is DATA (JSON/YAML). Zero runner code, zero framework imports —
   the runner belongs to /build's adapter. Trajectory modes: ANY_ORDER default,
   EXACT only where order is the contract.
7. RED BY DESIGN: with no agent built, the suite must fail. An eval that passes
   in a vacuum is a bug in the eval.
8. Writes: the target repo's evals/ tree, plus EXACTLY the Eval column of
   spec.md §6 — nothing else, ever. config.yaml carries status: draft until the
   explicit human gate. Never self-approve.

## Workflow

1. Read `references/suite-guide.md`; run steps 0→8 in order.
2. Formats come from `references/golden-format.md` — schema deviations are
   bugs, not creativity.
3. Present the gate summary (cases by method, adversarial by surface, coverage
   N/N, thresholds, release blockers, red-by-design reminder).
4. Explicit approval → config.yaml status: approved. Feedback → edit,
   re-present.
5. Hand off: "Next phase: `agent-cycle:build` binds a runner; its exit code is
   the pipeline's definition of green."

## Failure modes to avoid

- Building a suite on a draft or stale spec (violates rule 1).
- "Fixing" a confusing BHV inside the eval instead of disputing it (rule 2).
- A BHV silently absent from coverage (rule 3).
- Judge-only suites, or asserts forced onto judgment calls (rule 4).
- Gibberish injections, or English-only payloads for a Spanish-speaking owner
  (rule 5).
- Writing runner code or importing a framework into the suite (rule 6).
- An eval that would pass with no agent behind it (rule 7).
- Touching anything in spec.md beyond the §6 Eval column (rule 8).
