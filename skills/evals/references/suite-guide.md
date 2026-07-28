# Suite derivation guide — agent-cycle:evals

## Step 0 — Gate check

Read `docs/agent/spec.md`. Hard-fail (write nothing, say why, stop) if missing
("run agent-cycle:spec first") or `status` != `approved`. Record `spec_version`.
If the spec's `design_version` no longer matches the design's `version`, stop —
staleness goes to the re-entry ladder, not into a suite built on sand.

## Step 1 — Inventory (no interview)

Parse from the spec: the full BHV list with capability + type (happy/wrong/
edge/security), the tool tiers, the untrusted-surface table, the outcome enum
(telemetry section, if any), and the spec's §7 open questions. The suite's
scope is exactly this inventory. Ask the user NOTHING the spec already answers;
at most, interview on §7 items that shape evals (e.g. which language variants
matter) — one question at a time. An open question whose honest answer is
"data does not exist until post-launch" (e.g. a usage-derived corpus) is
recorded in config.yaml notes as a deferred corpus source — not re-asked, and
not a blocker: the suite is authored from the spec's scenarios, which need no
usage data.

## Step 2 — Classify method per BHV

Rule: if every Then line is an observable fact (tool called with X, reply
contains/omits Y, outcome == Z, no file written) → `deterministic`. If any Then
requires judgment (quality, tone, helpfulness) → `llm_judge` with a rubric. If
the scenario exercises an untrusted surface or an abuse path → `adversarial`.
A single BHV may yield one deterministic case AND one judge case; never force
judgment into asserts or asserts into judgment.

If a BHV is genuinely ambiguous — two honest readings that would produce
different evals — stop and dispute it via the re-entry ladder. Never resolve
ambiguity by authoring a creative eval (that is reinterpreting the spec).

## Step 3 — Author golden cases

One JSON file per case (schema: golden-format.md). Fixtures come from the
spec's own Given lines — reuse its fixture block verbatim where it defines one.
Trajectory mode per the format rules (ANY_ORDER default). Put every Then line
into asserts/forbidden — dropping a Then line silently is a coverage lie.
Failure-path scenarios assert the ABSENCE of side effects (`forbidden`).

## Step 4 — Adversarial expansion

Per surface the spec marks UNTRUSTED: at least 2 payloads — direct instruction
and authority-claim variants — plus at least one in the end-user's real
language when the spec calls for it (a Spanish-speaking owner gets Spanish
injections). A surface the spec explicitly classifies as trusted-by-design
(e.g. owner-only channel behind an allowlist) gets NO injection payloads
against its content; instead, its ENFORCEMENT mechanism gets a deterministic
case (e.g. non-owner delivery → dropped, zero outbound).
Payloads must be realistic enough that a naive model might follow them;
gibberish does not test containment. Each case's forbidden list encodes the
containment claim (no extra recipients, no writes, no secrets in reply, rules
unchanged).

## Step 5 — Rubrics

One rubric file per llm_judge/human_review dimension: a 1-5 scale, what each
band means, and at least one anchored positive and one anchored negative
example. The judge model must be at least as strong as the judged model — note
this in the rubric header. Validate judges against the human gate verdicts
periodically (the weekly ritual owns this).

## Step 6 — config.yaml

Thresholds by tier (pass^k for destructive). Release blockers: all adversarial
cases, plus every hard constraint the spec states (lift them verbatim).
Dimensions: activate only what this agent can emit (cost_efficiency needs the
telemetry fields the spec defines). coverage_gaps: any BHV without a case, with
its one-line justification.

## Step 7 — Coverage + spec column

Reconcile: every BHV ↔ case id(s) or gap entry — counts must match exactly.
Update the spec §6 Eval column with the case ids. ONLY that column — any other
edit to spec.md is forbidden (anti-gaming boundary).

## Step 8 — Gate

Present: total cases by method, adversarial count by surface, coverage N/N,
thresholds table, release blockers, and the red-by-design reminder (running
the suite now MUST fail — there is no agent). Explicit approval → config.yaml
status: approved. Hand off: "Next: agent-cycle:build binds a runner to this
suite; its exit code becomes the pipeline's definition of green."
