# Interview guide — agent-cycle:design

Rules: ONE question per message. Multiple choice where possible. Skip anything
the user already provided (edge case DES-E03) — but never skip the Goodhart
stress-test, even on user-provided metrics.

## Phase A — PEAS (order: P, E, A, S)

**P (Performance):**
- "What single measurable outcome defines success for this agent?" If the answer
  is agent activity (messages sent, tickets touched), push back once: "That
  measures the agent, not the world. What changes in the business if it works?"
- Goodhart stress-test (always): "If the agent optimized ONLY <metric>, what's
  the worst way it could hit the number?" Record the answer as a Goodhart note
  and add the balancing factor (e.g. call-time metric → agent hangs up on hard
  problems → balance with resolution rate). On user-provided metrics this is
  ONE follow-up max — never re-ask what the metric is (DES-E03 contract).

**E (Environment):** lead question: "Who talks to this agent, and through what
channel?" Then, in SEPARATE messages as needed: connected systems, language/
market. For WhatsApp agents, a separate follow-up: business-initiated or
user-initiated? 24h-window implications land in /spec, but note the mode here.
Never bundle these into one message (DES-E01 check #1).

**A (Actuators):** "What is the agent allowed to DO?" List tools by name +
one-line purpose only. For each, gut-guess the tier (safe read / reversible
write / destructive) — /spec finalizes.

**S (Sensors):** "What can it READ?" Inbound messages, DBs, calendars, APIs.

## Phase B — Environment classification

Ask only the dimensions not already obvious from Phase A answers. Map each to
its implication (table in artifact-template.md). Typical WhatsApp business
agent: partially observable, stochastic, sequential, dynamic, single-agent —
confirm each against THIS agent's Phase A answers, don't copy the example.

## Phase C — Harness

Default single-agent. Ask: "Is there any part of this job that needs different
permissions, different systems access, or true parallelism?" If no → single,
and record the one-line justification (e.g. "no differing-permission/system/
parallelism boundary identified"). If yes → name the boundary and justify
multi-agent in one paragraph with a MEASURABLE claim (latency, quality, or
safety it buys). The template's Justification field is filled in BOTH branches.
Run the 5-part completeness check (model/tools/memory/orchestration/deployment)
and note gaps as open questions.

## Phase D — Deployment intent

"Where will this run — AWS, GCP, or a VPS — and is that the client's constraint
or a choice?" Declare the 3 seams (sessions/model/telemetry) with the concrete
binding for the chosen target. Cite the vault's Multi-Cloud Agent Deployment
Patterns for the adapter surface.

## Phase E — NO-goals and gate

- "Name at least two things this agent must NOT do." (refunds without human?
  medical advice? out-of-scope topics?)
- Open questions (§7) must NEVER be empty. If Phase C found no gaps, surface at
  least one genuine uncertainty from any phase: an unconfirmed classification
  dimension, a tool-tier gut-guess, a deployment detail pending client sign-off.
- Present the filled artifact summary in chat. Ask for approval. On explicit
  approval ONLY: set `status: approved`, bump nothing else. On feedback: edit,
  re-present.
