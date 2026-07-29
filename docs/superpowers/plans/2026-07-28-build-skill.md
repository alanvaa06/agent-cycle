# agent-cycle `/build` Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship phase 4 — `agent-cycle:build` — the only skill that produces code: approved design+spec+evals → running agent (invariant core + deployment adapter), an eval RUNNER whose exit code becomes the pipeline's definition of green, forge-master delegation with mechanical PRD derivation, anti-gaming enforcement installed as a real hook, and OTel telemetry including the token counters economics needs. Then release v0.5.0.

**Architecture:** Same shape (EDD cases → references → SKILL.md), but three references: build-guide (steps 0-9), adapter-bindings (the 5 bindings per deployment target + eval-runner mapping per framework — self-contained, no external workspace assumed), forge-delegation (mechanical PRD derivation + the exact hook config + when NOT to delegate). Key stance: **the runtime is whatever the SPEC fixed** — the plugin documents ADK as its first framework target (per plan), but the skill scaffolds the spec's runtime; a spec that fixed Pydantic AI gets Pydantic AI. Writes: `src/`, `tests/`, the runner, the hook config, `docs/agent/build.md`, plus exactly the Test column of spec §6.

**Tech Stack:** Claude Code plugin format, Markdown/JSON only (the skill itself; it GENERATES Python).

**Spec:** `docs/superpowers/specs/2026-07-28-agent-cycle-plugin-design.md` § 4.4, § 6.

---

### Task 1: EDD eval cases — before the skill exists

**Files:**
- Create: `skills/build/evals/cases.json`
- Create: `skills/build/evals/README.md`
- Create: `skills/build/evals/results.md`

- [ ] **Step 1: Write the eval cases**

Write `skills/build/evals/cases.json`:

```json
{
  "skill": "agent-cycle:build",
  "spec_ref": "docs/superpowers/specs/2026-07-28-agent-cycle-plugin-design.md#44-agent-cyclebuild",
  "cases": [
    {
      "id": "BLD-E01",
      "type": "positive",
      "input": "Build the agent. (Run in a repo with approved design.md + spec.md + evals/config.yaml, e.g. the real whatsapp-owner-assistant.)",
      "expected": {
        "fires": true,
        "checks": [
          "Gate: all three upstream artifacts approved AND version chain consistent (spec.design_version == design.version; evals config.spec_version == spec.version); economics artifact read when present — its alarm threshold and telemetry requirements carried into the build",
          "The scaffold's runtime is the one the SPEC fixed — not a plugin default, not a model preference; deviation is a re-entry dispute, never a silent swap",
          "Core/adapter split: agent code (loop, tools, contracts) imports no infra SDKs; the adapter implements the 5 bindings (ingress, queue, state, secrets, deploy recipe); state behind the spec's repository interfaces",
          "Every tool implements its spec contract exactly: schemas with extra=forbid semantics, errors returned as observations, docstrings taken from the spec verbatim; no tool added, none dropped",
          "Loop caps from design/spec enforced in code (max steps, max tool calls, wall clock) with the spec's explicit exit conditions and failure-reply behavior",
          "Eval RUNNER built: consumes evals/ as immutable data (golden/adversarial JSON, rubrics, config.yaml), materializes fixtures incl. messages[] sequences and harness_condition, verifies trajectory modes + asserts + forbidden + outcome, applies per-tier thresholds (pass^k), exits non-zero on any failure — the exit code is the pipeline's green",
          "Telemetry: OTel GenAI conventions emitted per turn INCLUDING token counters (gen_ai.usage.input_tokens / output_tokens) — the economics calibration gap is closed by the build",
          "Anti-gaming enforced mechanically BEFORE code is written: a PreToolUse hook (or equivalent) in the target repo blocks edits to evals/ and docs/agent/ (except docs/agent/build.md and the spec §6 Test column) for the build's duration; its presence is verifiable on disk",
          "Delegation decision explicit: non-trivial build → forge-master PRD derived mechanically (BHV-NNN scenarios as ACs verbatim, eval-runner command as the test runner) and the forge plan presented for HUMAN approval before any forge-run; trivial all-safe build → direct TDD with a one-line justification",
          "Secrets hygiene: zero secrets in code or commits; the adapter's secret pattern implemented and .env.example updated to match; dependencies pinned (exact versions or lockfile + constraints)",
          "DoD recorded in docs/agent/build.md (runner command, suite result with pass^k, adapter smoke result, versions consumed, deviations); spec §6 Test column filled — and ONLY that column changed in spec.md; skill stops at the human gate"
        ]
      }
    },
    {
      "id": "BLD-E02",
      "type": "gate-negative",
      "input": "Build the agent. (Run twice: once in a repo with no evals/ directory, once where spec.md was version-bumped AFTER evals/config.yaml was approved — stale chain.)",
      "expected": {
        "fires": true,
        "checks": [
          "Refuses in both branches: names the missing/stale gate (no evals → run agent-cycle:evals first; stale chain → re-entry ladder) and stops",
          "Writes NO files in either branch — verified on the filesystem afterward"
        ]
      }
    },
    {
      "id": "BLD-E03",
      "type": "edge-trivial-direct",
      "input": "Build the agent. (Run against an approved trivial agent: one safe read-only tool, no queue/channel, evals with 6 cases all pass^1.)",
      "expected": {
        "fires": true,
        "checks": [
          "Chooses direct TDD over forge delegation, with the one-line justification recorded in build.md",
          "Still builds the runner, still enforces the anti-gaming hook, still records DoD — no ceremony skipped on the safety rails, only on orchestration"
        ]
      }
    },
    {
      "id": "BLD-E04",
      "type": "trigger-negative",
      "input": "Build me a REST API in FastAPI with a /users CRUD and JWT auth.",
      "expected": {
        "fires": false,
        "checks": [
          "agent-cycle:build does NOT fire — generic app development is outside the pipeline",
          "No files are created or modified — verified on the filesystem afterward"
        ]
      }
    }
  ]
}
```

- [ ] **Step 2: Write the run procedure**

Write `skills/build/evals/README.md`:

```markdown
# Eval procedure for agent-cycle:build

Same agentic procedure as `skills/design/evals/README.md` (fresh session,
per-check PASS/FAIL rows in `results.md`, fix-and-rerun, dispute — never
silently edit — if a case is wrong).

Case-specific setup:

- **BLD-E01** is the real dogfood run and is LONG (it produces the whole
  agent). Score checks 1-5 and 8-10 from the transcript + repo state as the
  build progresses; score 6-7 and 11 from the finished repo (run the runner
  yourself: it must exit non-zero while any eval fails and zero only when the
  suite is green).
- **BLD-E02** branch 2 setup: copy the real repo, bump spec.md version to 2
  without touching evals/config.yaml (spec_version stays 1) — the chain is now
  stale.
- **BLD-E03** needs a hand-written trivial approved design+spec+evals set in a
  scratch repo (30 min; do NOT use the pipeline skills to author them).
- **BLD-E04**: filesystem check afterward.

Scoring anchors: the runtime check (2) is scored against the spec's own fixed
runtime — the skill loses if it scaffolds anything else, INCLUDING the plugin's
own documented first framework target when the spec says otherwise. The
only-Test-column check is scored with `git diff --word-diff` on spec.md. The
anti-gaming check requires seeing the hook config on disk BEFORE source files
appear in the history, not after.
```

- [ ] **Step 3: Create the results log**

Write `skills/build/evals/results.md`:

```markdown
# Eval runs — agent-cycle:build

One row per check, per run. Verdict: PASS / FAIL. Evidence: one line.

| Date | Case | Check # | Verdict | Evidence |
|---|---|---|---|---|
```

- [ ] **Step 4: Verify JSON**

Run: `python -c "import json; d=json.load(open(r'skills/build/evals/cases.json')); print(len(d['cases']), 'cases,', len(d['cases'][0]['expected']['checks']), 'checks in E01')"`
Expected: `4 cases, 11 checks in E01`

- [ ] **Step 5: Commit**

```bash
git add skills/build/evals/
git commit -m "feat(build): EDD eval cases before SKILL.md (BLD-E01..E04)"
```

---

### Task 2: Build guide

**Files:**
- Create: `skills/build/references/build-guide.md`

- [ ] **Step 1: Write the guide**

Write `skills/build/references/build-guide.md`:

```markdown
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
   draft, date, design_version, spec_version, evals_version, runtime, target),
   runner command, suite summary, smoke results, delegation decision,
   deviations/additions (e.g. telemetry fields added).
4. Fill spec §6 Test column (ONLY that column).
5. Human gate → status: approved. Hand off: "/ship audits this build record."
```

- [ ] **Step 2: Commit**

```bash
git add skills/build/references/build-guide.md
git commit -m "feat(build): build guide (rails first, spec-fixed runtime, runner as green)"
```

---

### Task 3: Adapter bindings reference

**Files:**
- Create: `skills/build/references/adapter-bindings.md`

- [ ] **Step 1: Write the reference**

Write `skills/build/references/adapter-bindings.md`:

```markdown
# Adapter bindings — agent-cycle:build

Self-contained reference. The agent core never forks per cloud — only the
adapter does, across exactly 5 bindings. Webhook-driven agents converge on the
same invariant architecture on every target because the channel's delivery
semantics (fast ack, retries, duplicates) force it:

```
INGRESS (verify + ack fast) → QUEUE (per-user ordering) → WORKER (the loop)
→ STATE (durable sessions + dedupe) → EGRESS (reply + model calls)
```

## The 5 bindings per target

| Binding | VPS (self-hosted) | AWS | GCP |
|---|---|---|---|
| Ingress | Caddy/Traefik reverse proxy → FastAPI/ASGI endpoint; TLS automatic (Caddy) | API Gateway HTTP API → thin Lambda | Cloud Run ingress service |
| Queue | Redis/Valkey list or stream, worker process consumes; strict serial per sender | SQS FIFO, MessageGroupId = user id | Pub/Sub, ordering key = user id |
| State | Postgres (or Supabase Postgres) behind the repository interface | DynamoDB behind the repository interface | Firestore / Cloud SQL behind the repository interface |
| Secrets | .env file mode 0600 loaded by systemd/compose, or SOPS+age; never committed | Secrets Manager | Secret Manager |
| Deploy recipe | Docker Compose (worker + queue + proxy [+ db]); systemd only as the thing that starts Docker | SAM/CDK (Lambda) or ECS/Fargate task | gcloud run deploy / Cloud Build |

Universal rules regardless of target:
- Ingress verifies the channel signature over the RAW body before parsing,
  returns 200 fast, and drops non-allowlisted senders BEFORE the loop.
- Dedupe on the channel's message id with a unique index / conditional put —
  retries and duplicates are guaranteed by the channel, not hypothetical.
- The worker consumes the queue serially per sender; a running turn is never
  cancelled by a new message.
- Bind containers/services to localhost internally; only the proxy/gateway
  listens publicly.
- Health endpoint (`GET /health` or platform equivalent) for the smoke test.

## Runner mapping per framework

The eval suite is data; the runner binds it to a framework:

- **ADK (first documented target):** `AgentEvaluator` consumes trajectory
  expectations natively; map golden `trajectory.mode` to ADK's
  EXACT / IN_ORDER / ANY_ORDER; fixtures via session-service fakes;
  harness_condition via callback-injected step caps / erroring tool doubles.
- **Any Python framework (Pydantic AI, LangGraph, custom):** a pytest harness:
  one parametrized test per case file; fixtures build fake tool backends from
  `input.fixture`; `messages[]` replayed through the debounce path with its
  offsets; `harness_condition.force_step_cap` monkeypatches the cap,
  `tool_always_errors` swaps the named tool for an erroring double;
  trajectory captured from the loop's tool-call log and compared per mode;
  `forbidden` checked against outbound calls AND reply text; llm_judge cases
  call the judge model named in the rubric and enforce the rubric's pass
  threshold; config.yaml `thresholds` drive pytest reruns for pass^k tiers.
- Exit code contract is identical everywhere: 0 = every case at threshold.

## Telemetry binding

OTel GenAI semantic conventions on every target; exporter is configuration:
self-hosted → OTLP to Phoenix/Langfuse/collector; AWS → ADOT; GCP → Cloud
Trace. Required attributes: the spec's per-turn list PLUS
`gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens` per model call
(cost calibration depends on these). Token-spend alarm: implement the
economics artifact's threshold as a metric alarm where the target supports it,
else a daily aggregation job + notification.
```

- [ ] **Step 2: Commit**

```bash
git add skills/build/references/adapter-bindings.md
git commit -m "feat(build): adapter bindings reference (5 bindings x 3 targets, runner mapping, telemetry)"
```

---

### Task 4: Forge delegation reference

**Files:**
- Create: `skills/build/references/forge-delegation.md`

- [ ] **Step 1: Write the reference**

Write `skills/build/references/forge-delegation.md`:

```markdown
# Forge delegation — agent-cycle:build

/build does not reimplement loop engineering. Non-trivial builds delegate
execution to forge-master through its PUBLIC contract only: a PRD with ACs +
a test-runner command whose exit code defines green.

## When to delegate

Delegate when ANY holds: >3 tools, any non-safe tier, a queue/channel adapter,
or an eval suite with >15 cases. Direct TDD (no forge) only when ALL of:
few tools, all safe-tier, no channel infra, small suite — and record the
one-line justification in build.md.

## Mechanical PRD derivation

The spec's BHV scenarios are ALREADY Given/When/Then — they are the forge
PRD's acceptance criteria verbatim:

1. PRD header: agent name, goal (design's Performance metric), runtime +
   target (spec/design), constraints (loop caps, NO-goals).
2. ACs: every BHV-NNN copied verbatim, ID preserved. No paraphrase — the IDs
   are the traceability chain (BHV → eval → forge phase → test).
3. Test runner: the eval-runner command from build Step 8, stated exactly
   (e.g. `python -m evals.runner` or `pytest tests/eval_runner.py`). Forge's
   "green = exit code" rule composes with the runner's "0 = every case at
   threshold" — no opinion anywhere in the chain.
4. Build order as suggested phasing: state → tools → loop → adapter → green.

Then: forge-master:plan-design over that PRD → HUMAN approves the plan →
forge-master:forge-run executes. Never skip the human plan gate.

## The anti-gaming hook

Installed at build Step 2, BEFORE source exists. Claude Code harness — write
`.claude/settings.json` in the TARGET repo (merge if it exists):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/guard_artifacts.py"
          }
        ]
      }
    ]
  }
}
```

And `.claude/hooks/guard_artifacts.py` (stdin receives the tool call JSON;
exit 2 blocks):

```python
import json, sys, pathlib

BLOCKED = ("evals/", "docs/agent/")
ALLOWED = ("docs/agent/build.md",)

call = json.load(sys.stdin)
path = call.get("tool_input", {}).get("file_path", "")
p = pathlib.PurePosixPath(str(path).replace("\\", "/"))
rel = str(p)
for i, part in enumerate(p.parts):
    if part in ("evals", "docs"):
        rel = "/".join(p.parts[i:])
        break

if rel.startswith(BLOCKED) and rel not in ALLOWED:
    print(f"BLOCKED by agent-cycle anti-gaming rail: {rel} is a frozen "
          f"pipeline artifact. Changes go through the re-entry ladder "
          f"(dispute -> re-open the owning phase), never through the builder.",
          file=sys.stderr)
    sys.exit(2)
sys.exit(0)
```

The spec §6 Test column exception: the column is filled at build Step 9 AFTER
the suite is green — remove or bypass the hook for that single sanctioned edit
with the human's knowledge (state it at the gate), then restore it.

Fallback when no hook mechanism exists: declare in build.md that the git-diff
audit is the rail — /ship verifies `evals/` and `docs/agent/` (minus
allow-list) have zero diffs across the build's commit range.

## Disputes

The builder believing an eval or scenario is wrong is NOT a license to edit
it. Raise the dispute: name the case id, the two readings, the evidence from
the trace. The human routes it (fix-eval via /evals, fix-spec via /spec, or
overrule). The hook makes the wrong path mechanical to catch; the dispute
makes the right path cheap to take.
```

- [ ] **Step 2: Commit**

```bash
git add skills/build/references/forge-delegation.md
git commit -m "feat(build): forge delegation reference (mechanical PRD, anti-gaming hook, disputes)"
```

---

### Task 5: SKILL.md

**Files:**
- Create: `skills/build/SKILL.md`

- [ ] **Step 1: Write the skill**

Write `skills/build/SKILL.md`:

```markdown
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
```

- [ ] **Step 2: Verify frontmatter**

Run: `head -4 skills/build/SKILL.md`
Expected: `---`, `name: build`, description present.

- [ ] **Step 3: Commit**

```bash
git add skills/build/SKILL.md
git commit -m "feat(build): SKILL.md — rails before code, runner as green, spec runtime is law"
```

---

### Task 6: Release v0.5.0

- [ ] **Step 1:** plugin.json version → `0.5.0`.
- [ ] **Step 2:** README status line → `**Status:** v0.5.0 — \`design\` + \`spec\` + \`evals\` + \`economics\` + \`build\` skills.\nBuilt skill-by-skill, each dogfooded on a real agent before the next begins.`
- [ ] **Step 3:** CHANGELOG entry before `## [0.4.1]`:

```markdown
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
```

- [ ] **Step 4:** Verify version prints `0.5.0`; commit `chore: release v0.5.0 (build skill)`.

---

### Task 7 (Alan, interactive): eval runs + dogfood

- [ ] BLD-E02 ×2, BLD-E03, BLD-E04 in scratch → rows in results.md.
- [ ] BLD-E01 dogfood in `C:\Proyectos\Whatsapp_agent`: Pydantic AI + VPS per the spec; forge delegation expected (7 tools, channel adapter, 34-case suite); the 34-case suite goes green via the runner → tag `build-v0.1`.
- [ ] Marketplace update + reinstall for v0.5.0.

---

## Self-review (done at planning time)

- **§4.4 coverage:** invariant core + adapter 5 bindings ✓; forge delegation with mechanical PRD + human plan gate + when-not ✓; anti-gaming PreToolUse hook as REAL config not prose ✓ (forge-delegation.md ships the actual hook script); DoD suite-green + smoke ✓; sandbox/secrets/slopsquatting ✓ (guide step 3, rule 9); ADK-first honored as first documented runner/framework target while rule 2 makes the spec's runtime binding — consistent with the dogfood-doesn't-redefine-defaults rule in both directions.
- **Cross-skill:** consumes economics' alarm + closes its token-counter gap (rule 7 + guide step 6); runner consumes evals' schema exactly (messages[], harness_condition, modes, pass^k — field names match golden-format.md); Test column write mirrors evals' Eval-column sanction; build.md frontmatter chain matches the version-pinning convention.
- **Placeholder scan:** none. Hook script is complete and runnable; JSON examples parse.
- **Check count:** BLD-E01 = 11 checks, matches cases.json.
```
