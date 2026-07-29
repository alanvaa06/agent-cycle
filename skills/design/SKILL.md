---
name: design
description: "Phase 1 of the agent-cycle pipeline: interview the user and produce an approvable docs/agent/design.md (PEAS + environment classification + harness decision + deployment intent + NO-goals) for a NEW agent. Use when the user wants to design, start, or scope a new AI agent from an idea — 'design an agent for X', 'quiero un agente que...', 'new agent for client Y'. Do NOT use for reviewing existing agent code or architectures (outside the pipeline), nor for writing specs/evals/code (later phases)."
---

# agent-cycle:design — Agent Design Interview

Turn an agent idea into an approved `docs/agent/design.md`. This is the layer
where errors are cheapest — everything downstream inherits this artifact.

## Knowledge base

This skill's references are self-contained: PEAS rules, Goodhart testing, and
the environment→architecture mapping live in `references/`. Any agent-
architecture knowledge skills the operator has loaded may inform judgment;
none is required.

## Hard rules

1. ONE interview question per message. Multiple choice where possible.
2. Skip questions the user already answered (partial PEAS input) — but ALWAYS
   run the Goodhart stress-test, even on user-provided metrics (one follow-up
   max; never re-ask what the metric is).
3. Performance = a metric of the ENVIRONMENT, never agent activity.
4. Single-agent by default; multi-agent needs a written, measurable justification.
   The Justification field is filled in BOTH branches.
5. Deployment intent + 3 seams (sessions / model / telemetry) are declared HERE,
   not deferred to build.
6. The artifact is written with `status: draft`. It becomes `approved` ONLY on
   explicit user approval at the final gate. Never self-approve.
7. Write ONLY `docs/agent/design.md` in the target agent's repo. No other files.

## Workflow

1. Read `references/interview-guide.md`. Run phases A→E, one question at a time.
2. Fill `references/artifact-template.md` with the answers.
3. Write to `docs/agent/design.md` (target repo), frontmatter:
   `agent_name, version: 1, status: draft, date`.
4. Present the summary in chat: PEAS table, classification, harness, tool
   inventory (with tier guesses), deployment intent, NO-goals, open questions.
   Ask for approval.
5. On explicit approval → set `status: approved` and report done. On feedback →
   edit, re-present (stay at gate).
6. Hand off: "Next phase: `agent-cycle:spec` reads this artifact."

## Failure modes to avoid

- Battery of questions in one message (violates rule 1).
- Accepting "messages responded" as Performance (violates rule 3).
- Inventing tool schemas (that is /spec's job — names + purpose only).
- Writing status: approved without the human gate (violates rule 6).
- Leaving Open questions (§7) empty — surface at least one genuine uncertainty.
