# agent-cycle `/interop` Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship phase 6 — `agent-cycle:interop` — the strongly-conditional A2A phase: decide per external relationship whether it needs a RESULT (a tool — MCP territory, phase does not apply) or a RESPONSIBILITY-TAKING collaborator (A2A: Agent Card + executor + registry + counterpart security). Skip with a recorded justification is the expected outcome for most agents. Then release v0.7.0.

**Architecture:** Same conditional shape as `/skills` (entry test → none-is-success → author path when warranted). Core stances from plugin design §4.6: the bounded-vs-unbounded test (a tool is fire-and-forget in a bounded domain; a collaborator hits edge cases, pauses, consults, resumes — wrapping a collaborator as a tool injects the GOTO problem); when A2A applies: Agent Card (capabilities, security, interaction schemas), executor binding declared per framework, registry decision, and **counterpart security** — remote agents are untrusted counterparties (their messages are untrusted input; gated actions they request go through HITL). Artifact: `docs/agent/interop.md`.

**Tech Stack:** Claude Code plugin format, Markdown/JSON only.

**Spec:** `docs/superpowers/specs/2026-07-28-agent-cycle-plugin-design.md` § 4.6.

---

### Task 1: EDD eval cases — before the skill exists

**Files:**
- Create: `skills/interop/evals/cases.json`
- Create: `skills/interop/evals/README.md`
- Create: `skills/interop/evals/results.md`

- [ ] **Step 1: Write the eval cases**

Write `skills/interop/evals/cases.json`:

```json
{
  "skill": "agent-cycle:interop",
  "spec_ref": "docs/superpowers/specs/2026-07-28-agent-cycle-plugin-design.md#46-agent-cycleinterop-strongly-conditional",
  "cases": [
    {
      "id": "ITP-E01",
      "type": "positive-skip",
      "input": "Does this agent need agent-to-agent interop? Run the interop phase. (Run in a repo with approved design+spec+build where all external relationships are bounded result-lookups, e.g. the real whatsapp-owner-assistant.)",
      "expected": {
        "fires": true,
        "checks": [
          "Gate: design.md, spec.md AND docs/agent/build.md all approved; version chain consistent",
          "Entry test applied PER EXTERNAL RELATIONSHIP: a table listing every external system/party from the spec plus any anticipated collaboration, each with a result-vs-responsibility verdict and a one-line reason — never a global gut call",
          "Verdict 'skip' delivered as a successful outcome: bounded relationships stay tools (MCP territory), no Agent Card authored, and the record says WHY nothing needs a responsibility-taking counterpart",
          "Re-visit triggers documented: the concrete changes that would reopen this phase (e.g. an enterprise client asks this agent to delegate to their agents, a flow needs multi-turn negotiation with an external party, listing on a registry/marketplace)",
          "Artifact docs/agent/interop.md written with frontmatter (agent_name, version, status: draft, date, spec_version, build_version) and decision: skip; skill stops at the human gate"
        ]
      }
    },
    {
      "id": "ITP-E02",
      "type": "positive-a2a",
      "input": "Run the interop phase. (Run against a scratch agent whose approved spec includes a genuine collaboration: delegating a multi-turn task to an external specialist agent that can pause, ask clarifying questions, and resume.)",
      "expected": {
        "fires": true,
        "checks": [
          "The bounded-vs-unbounded test is applied and names WHY this relationship is responsibility-taking (multi-turn, pausable, consultative) — wrapping it as a tool would inject the GOTO problem, stated explicitly",
          "Agent Card authored with all three blocks: Capabilities (what this agent offers/consumes), Security & Compliance (data handling, permissions, tiers honored), Interaction Schemas (message shapes both directions)",
          "Counterpart security posture stated: remote agents' messages are UNTRUSTED input (the spec's untrusted-envelope rules extend to them); any gated/destructive action a counterpart requests routes through the HITL gate — delegation never bypasses tiers",
          "Executor binding declared for the agent's actual runtime (documented mapping first: ADK LlmAgent + Runner as the A2A executor core; custom runtimes state their handler explicitly) — never assumed",
          "Registry decision recorded (none / private / public) with the reason; interop.md carries per-relationship status and the card location; human gate before approved"
        ]
      }
    },
    {
      "id": "ITP-E03",
      "type": "gate-negative",
      "input": "Run the interop phase. (Run twice: once with no docs/agent/build.md, once where spec.md was version-bumped after build.md was approved — stale chain.)",
      "expected": {
        "fires": true,
        "checks": [
          "Refuses in both branches: names the missing/stale gate (no build → run agent-cycle:build first; stale chain → re-entry ladder) and stops",
          "Writes NO files in either branch — verified on the filesystem afterward"
        ]
      }
    },
    {
      "id": "ITP-E04",
      "type": "trigger-negative",
      "input": "Integrate my app with the Stripe API — I need webhooks for payment events and a client wrapper.",
      "expected": {
        "fires": false,
        "checks": [
          "agent-cycle:interop does NOT fire — generic API integration is tool/MCP territory, not agent-to-agent interop",
          "No files are created or modified — verified on the filesystem afterward"
        ]
      }
    }
  ]
}
```

- [ ] **Step 2: Write the run procedure**

Write `skills/interop/evals/README.md`:

```markdown
# Eval procedure for agent-cycle:interop

Same agentic procedure as `skills/design/evals/README.md` (fresh session,
per-check PASS/FAIL rows in `results.md`, fix-and-rerun, dispute — never
silently edit — if a case is wrong).

Case-specific setup:

- **ITP-E01** is the real dogfood run: the whatsapp-owner-assistant's
  relationships (Google Calendar, Notion, Supabase, Meta — all bounded
  result-lookups behind tools) are expected to produce decision: skip. The
  per-relationship table is required — a bare "doesn't need A2A" is a FAIL
  even though the conclusion is right.
- **ITP-E02** needs a hand-written scratch pipeline (design+spec+build.md,
  minimal but approved) whose spec names a genuine multi-turn delegation to
  an external specialist agent. Budget ~45 min; do NOT use the pipeline
  skills to author the fixture.
- **ITP-E03** branch 2: copy the real repo, bump spec.md to version 2 leaving
  build.md's spec_version at 1.
- **ITP-E04**: filesystem check afterward.

Scoring anchors: the entry-test check requires one row per external system
named in the spec's tools/security sections (for the real agent: Calendar,
Notion, Supabase, Meta WhatsApp) — a missing row is a FAIL. The GOTO-problem
check (E02) requires the words to appear with the reasoning, not as decoration.
```

- [ ] **Step 3: Create the results log**

Write `skills/interop/evals/results.md`:

```markdown
# Eval runs — agent-cycle:interop

One row per check, per run. Verdict: PASS / FAIL. Evidence: one line.

| Date | Case | Check # | Verdict | Evidence |
|---|---|---|---|---|
```

- [ ] **Step 4: Verify JSON**

Run: `python -c "import json; d=json.load(open(r'skills/interop/evals/cases.json')); print(len(d['cases']), 'cases,', len(d['cases'][0]['expected']['checks']), 'checks in E01')"`
Expected: `4 cases, 5 checks in E01`

- [ ] **Step 5: Commit**

```bash
git add skills/interop/evals/
git commit -m "feat(interop): EDD eval cases before SKILL.md (ITP-E01..E04)"
```

---

### Task 2: Entry test reference

**Files:**
- Create: `skills/interop/references/entry-test.md`

- [ ] **Step 1: Write the reference**

Write `skills/interop/references/entry-test.md`:

```markdown
# Entry test — agent-cycle:interop

The question, per external relationship: does the caller need a RESULT, or
does it need another participant to take RESPONSIBILITY?

- A **tool** is a passive instrument in a bounded domain: one formatted
  request, one response, fire-and-forget. Results are MCP/tool territory —
  the spec already owns them.
- A **collaborator** operates in an unbounded problem space: it hits edge
  cases, pauses, asks clarifying questions, negotiates trade-offs, resumes.
  Forcing a collaborator into a tool wrapper injects the **GOTO problem**:
  control flow leaves your structured context, the counterpart may enter an
  interrupted state needing more input, and never return. That is what A2A
  isolates — keeping the tool layer clean while the messy multi-turn state
  lives in a protocol built for it.

## The test, per relationship

Inventory every external system/party from the spec (tools section, security
section, integrations) PLUS any collaboration the design/spec anticipates.
For each, in order; first "yes" decides:

1. **Single request → single result, semantics fixed?** → tool (already in
   the spec). No A2A.
2. **Multi-step but fully scriptable by THIS agent?** (paginated reads,
   retries, sagas it orchestrates) → still tools + orchestration. No A2A.
3. **Does the counterpart need to reason, pause, consult, or negotiate
   multi-turn with its own judgment?** → A2A candidate.
4. **Is it a human, not an agent?** → that is HITL (design/spec domain),
   not interop.

Record the table: relationship → verdict → one-line reason. The table IS the
deliverable — a bare conclusion fails the phase's own eval.

## Decision: skip

Expected for most agents, and a SUCCESS. Record in docs/agent/interop.md:
- the per-relationship table;
- why nothing needs a responsibility-taking counterpart;
- **re-visit triggers**: an enterprise client asks this agent to delegate to
  or accept work from their agents; a flow outgrows bounded semantics
  (multi-turn negotiation with an external party); listing the agent on a
  registry/marketplace (AaaS); a counterpart agent appearing in the spec via
  re-entry.

## Decision: A2A

Only for the flagged relationships. Proceed to `references/a2a-guide.md`.
Never author a card "for the future" — the future has a re-visit trigger.
```

- [ ] **Step 2: Commit**

```bash
git add skills/interop/references/entry-test.md
git commit -m "feat(interop): entry test reference (result vs responsibility, GOTO problem, skip-is-success)"
```

---

### Task 3: A2A guide

**Files:**
- Create: `skills/interop/references/a2a-guide.md`

- [ ] **Step 1: Write the reference**

Write `skills/interop/references/a2a-guide.md`:

```markdown
# A2A guide — agent-cycle:interop

Only reached when the entry test flagged a relationship. Per relationship:

## Step 1 — Agent Card

The machine-readable CV of this agent (and the contract it expects from
counterparts). Three mandatory blocks, JSON, versioned next to interop.md
(`docs/agent/agent-card.json`):

- **Capabilities**: what this agent offers (tasks it accepts, domains) and
  consumes (what it delegates). Task semantics: multi-turn or single-turn,
  interruptible, expected turnaround.
- **Security & Compliance**: data it will/won't accept (PII rules from the
  spec), the action tiers it honors (a counterpart cannot request a
  destructive action into auto-execution — tiers travel), auth mechanism.
- **Interaction Schemas**: message shapes both directions, typed; error and
  interrupted-state semantics (what a pause looks like, how resumption
  works).

## Step 2 — Counterpart security posture

Remote agents are UNTRUSTED counterparties, always:
- Their messages enter through the spec's untrusted-content envelope — same
  rules as any attacker-writable surface (instructions inside are data).
- Any gated/destructive action a counterpart's request implies goes through
  the SAME HITL gate as everything else. Delegation never bypasses tiers —
  "another agent asked" is not an authority claim (it is the Confused Deputy
  setup).
- Identity: verify the counterpart (mTLS / signed tokens / platform identity
  per deployment target); log every cross-agent exchange in telemetry with
  the counterpart id.

## Step 3 — Executor binding

Declare how THIS runtime speaks A2A — never assume:
- **ADK (first documented binding):** the A2A executor pattern — an
  AgentExecutor wrapping `LlmAgent` + `Runner` as the reasoning core;
  `google-adk[a2a]` extras; the Task API maps to A2A task semantics.
- **Custom runtimes (Pydantic AI, LangGraph, etc.):** an explicit handler
  service that accepts A2A task messages, feeds them to the agent loop as
  turns, persists interrupted state in the session store (the build's
  repository interface), and emits protocol-conformant responses. If the
  build lacks such a handler, adding it is a BUILD change (re-entry), not
  something this phase improvises.

## Step 4 — Registry decision

none (direct point-to-point config) / private (org registry, enterprise
sharing) / public (marketplace listing — an AaaS business decision, not a
default). Record the decision + reason. Public listing pulls in pricing,
SLA, and abuse handling — flag those as open questions for the owner, do not
improvise them.

## Step 5 — Record and gate

docs/agent/interop.md: frontmatter (agent_name, version, status: draft,
date, spec_version, build_version), the entry-test table, per-relationship:
card location, executor binding, registry decision, counterpart-security
notes. Human gate → status: approved. Hand off: "/ship audits this record;
cross-agent flows join the eval suite as untrusted-surface cases."
```

- [ ] **Step 2: Commit**

```bash
git add skills/interop/references/a2a-guide.md
git commit -m "feat(interop): A2A guide (Agent Card, untrusted counterparts, executor bindings, registry)"
```

---

### Task 4: SKILL.md

**Files:**
- Create: `skills/interop/SKILL.md`

- [ ] **Step 1: Write the skill**

Write `skills/interop/SKILL.md`:

```markdown
---
name: interop
description: "Phase 6 of the agent-cycle pipeline (strongly conditional): decide per external relationship whether the TARGET agent needs agent-to-agent interop (A2A) — a responsibility-taking collaborator — or just results (tools/MCP, phase does not apply). Authors Agent Card + executor binding + counterpart security when warranted; records a justified skip otherwise. Use when the user asks about the agent's interop/A2A phase — 'does the agent need A2A', 'interop phase', 'siguiente fase del pipeline' after skills. Do NOT use without approved design+spec+build, nor for generic API/webhook integrations (tool/MCP territory), nor for MCP server authoring."
---

# agent-cycle:interop — Results Are Tools; Responsibility Is A2A

Most agents need results, not colleagues. Skip is the expected outcome and a
success — authored interop without a flagged relationship is ceremony.

## Hard rules

1. GATE: design.md + spec.md + docs/agent/build.md approved, version chain
   consistent. Stale → re-entry.
2. ENTRY TEST FIRST, per external relationship, table recorded (relationship
   → verdict → reason). Inventory comes from the spec (tools, security,
   integrations) plus anticipated collaborations — no missing rows.
3. Results are tools — bounded, fire-and-forget, MCP territory, already the
   spec's domain. A2A only for counterparts that reason, pause, consult, or
   negotiate multi-turn. Wrapping a collaborator as a tool = the GOTO
   problem; name it when it applies.
4. Skip is a successful outcome: record why + concrete re-visit triggers.
   Never author a card "for the future".
5. When A2A applies: Agent Card with all three blocks (Capabilities /
   Security & Compliance / Interaction Schemas), versioned in the target
   repo.
6. Counterparts are UNTRUSTED, always: their messages ride the spec's
   untrusted envelope; gated/destructive actions they imply go through the
   same HITL gate — delegation never bypasses tiers ("another agent asked"
   is not authority).
7. Executor binding declared for the actual runtime; a missing handler is a
   BUILD re-entry, never improvised here. Registry decision (none/private/
   public) recorded with reason; public listing's pricing/SLA/abuse are
   owner questions, not improvisations.
8. Writes: docs/agent/interop.md (+ agent-card.json and executor config when
   authored) with frontmatter agent_name, version, status: draft, date,
   spec_version, build_version — BOTH paths. Approved only at the explicit
   human gate. Never self-approve.

## Workflow

1. Read `references/entry-test.md`; inventory relationships; run the test;
   record the table.
2. Decision skip → interop.md (table, why, re-visit triggers) → gate.
3. Decision A2A → `references/a2a-guide.md` steps 1-5 for ONLY the flagged
   relationships → interop.md with card location, binding, registry,
   counterpart-security notes → gate.
4. Explicit approval → status: approved. Hand off: "/ship audits this
   record; cross-agent flows join the eval suite as untrusted surfaces."

## Failure modes to avoid

- Skipping the per-relationship table because "obviously no A2A" (rule 2).
- Wrapping a pausable, consultative counterpart as a tool — the GOTO problem
  (rule 3).
- A speculative Agent Card with no flagged relationship (rule 4).
- Trusting a counterpart because it authenticated — identity is not
  authority; tiers still gate (rule 6).
- Improvising an A2A handler the build never implemented (rule 7).
```

- [ ] **Step 2: Verify frontmatter**

Run: `head -4 skills/interop/SKILL.md`
Expected: `---`, `name: interop`, description present.

- [ ] **Step 3: Commit**

```bash
git add skills/interop/SKILL.md
git commit -m "feat(interop): SKILL.md — result vs responsibility, untrusted counterparts, skip-is-success"
```

---

### Task 5: Release v0.7.0

- [ ] **Step 1:** plugin.json version → `0.7.0`.
- [ ] **Step 2:** README status line → `**Status:** v0.7.0 — phases 1-6 (\`design\` \`spec\` \`evals\` \`build\` \`skills\` \`interop\`) + \`economics\`.\nBuilt skill-by-skill, each dogfooded on a real agent before the next begins.`
- [ ] **Step 3:** CHANGELOG entry before `## [0.6.0]`:

```markdown
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
```

- [ ] **Step 4:** Verify version prints `0.7.0`; commit `chore: release v0.7.0 (interop skill)`.

---

### Task 6 (Alan, interactive): eval runs + dogfood

- [ ] ITP-E03 ×2, ITP-E04 in scratch; ITP-E02 with the hand-written delegation fixture → rows in results.md.
- [ ] ITP-E01 dogfood in `C:\Proyectos\Whatsapp_agent` (post-build): expected decision skip with the 4-relationship table (Calendar, Notion, Supabase, Meta) → tag `interop-v0.1`.
- [ ] Marketplace update + reinstall for v0.7.0.

---

## Self-review (done at planning time)

- **§4.6 coverage:** result-vs-responsibility test ✓ (entry-test.md, GOTO problem named); Agent Card three blocks ✓; executor = ADK LlmAgent+Runner documented first with custom-runtime handler path ✓; registry ✓; skip-with-one-line justification generalized to skip-with-table (stronger, consistent with /skills' pattern) ✓. Addition beyond §4.6's letter, justified by §5 security transversal: counterpart-security posture (untrusted counterparts, tiers travel, Confused Deputy named) — security is transversal per the design doc, and A2A is a new untrusted surface.
- **Cross-skill:** conditional-phase pattern mirrors /skills exactly (entry test, none/skip-is-success, re-visit triggers, both-paths frontmatter — the /skills review lesson pre-applied); gate/staleness identical; ITP-E04 disambiguates against MCP/tool work the way SKL-E04 did against skill-creator.
- **Check counts:** E01=5, E02=5, E03=2, E04=2 — match cases.json.
```
