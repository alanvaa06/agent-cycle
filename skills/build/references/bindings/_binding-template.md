# Build binding template

One file per active stack card, named `<card-id>.md`. Frontmatter
`version_pinned` must equal the card's `version_verified`
(`scripts/check_catalog.py` enforces it). Facts carry source URLs like cards.

Rules for every binding:
- Never refer to "the digest". Cite a URL or the research file path
  (`docs/superpowers/research/2026-10-07-stack-catalog/<file>.md`), or mark the
  statement `inference`.
- Each section below must answer every obligation in its placeholder text, or
  say explicitly why it does not apply to this stack.

```
---
card: <card-id>
version_pinned: <exact version>
---

# <Name> — build binding

Shape: <the core object shape, built by an injectable factory in src/agent/
(for example build_agent(model, store, tools)). Infra clients (DB drivers,
savers) are constructed in adapters/<target>/ and injected; the core never
imports infra SDKs. Framework state stores hold only conversation/graph state;
dedupe and the spec's data schemas stay behind the repository interface. Name
the framework construct this replaces, if any.>

## Sessions and state
<Postgres (incl. Supabase) / DynamoDB / Firestore: official store or the
adapter to write; per-session serialization (the queue guarantees one turn
per session); durability settings.
- Queue ordering key = the session key, so one turn per session holds even
  when an approver is a different sender. Ingress resolves an approver's reply
  to the pending session's key before enqueueing.
- Any one-time schema setup runs as a named one-shot migration job (compose
  service / ECS task / Cloud Run job), never from the worker.
- Every spike states its pass test and runs before build-guide Step 4. Every
  sessions/store spike, on failure, STOPS and raises a re-entry on the
  design's sessions seam; never a silent store swap. Other spikes state their
  own failure path (a binding defect -> fix the binding; telemetry -> its
  fallback).>

## HITL gate
<How gated/destructive tiers pause for approval and resume; idempotency
rules for work done before the pause.
- The numbered worker sequence: dequeue -> check this session for a pending
  approval -> resume with the decision OR start a new turn.
- The decision value shape (approve / deny / edit); deny and expiry behavior.
- If a message for a pending session does not parse as a decision: keep the
  interrupt pending and reply with the spec's pending-approval prompt (or deny
  if the spec says so). Expiry is evaluated when the next message for that
  session is dequeued (intended; a sweep is optional).
- Tier mapping: destructive -> HITL every time, never cached; reversible ->
  per design policy; safe -> auto.
- One recommended placement for the gate.
- If the spec says a deny ends the turn: no further tool executes after the
  reject (name the construct that routes to the end); if the spec lets the
  model continue after a deny, say so explicitly. Spike pass test: after a
  reject, zero further tool calls execute.
- How the eval runner answers approvals from the case fixture.>

## Caps
<Step cap and tool-call cap — native or own counter; the two are always
counted separately.
- Both caps are PER TURN: reset at turn start.
- The tool-call cap counts each tool call requested, not each tool-execution
  step, and is checked before execution so parallel calls cannot overshoot.
- State the unit conversion between the framework's limit and the spec's step.
- Both cap exits MUST produce the spec's single failure reply and the cap
  outcome.
- How the runner ensures the intended cap trips in
  harness_condition.force_step_cap cases.
- The wall-clock cap.
- No aborted turn (either cap, wall-clock, crash, deny-ends-turn) may leave an
  AI message with tool calls lacking tool results. Repair runs at TURN START
  (idempotent, survives crashes): if the last AI message has tool calls
  without matching tool messages, append tool-result notices through the
  framework's state/history update API (or the repository, for own-loop
  stacks), attributed to the right step/node where the framework requires
  it. A wall-clock
  abort notice says "outcome unknown - do not retry without the user" (the
  tool may have run). Spike pass test: abort mid-turn, then a follow-up turn
  succeeds against the real provider.>

## Model provider
<How the LiteLLM-style config string maps; non-native providers' caveats.
- One selection rule between the options.
- The route-string format conversion if the formats differ.>

## Telemetry
<OTel GenAI setup, token counters, and how to switch OFF any vendor egress.
- A per-turn span carrying the spec's attributes and the outcome.
- Where fallback spans hook in.
- Telemetry spikes need a real model call (fakes report no usage).>

## Eval runner mapping
<Model double, trajectory capture, EXACT/IN_ORDER/ANY_ORDER mapping, caps
and harness_condition injection; pass^k is always computed by the pipeline
runner.
- The PIPELINE runner implements EXACT / IN_ORDER / ANY_ORDER itself over the
  captured list of (tool name, args) with args_subset matching (golden-format;
  never full-argument equality).
- Framework evaluators are optional references only.
- One rule for trajectory vs forbidden: trajectory = the REQUESTED tool calls
  (name, args) read from the model messages; `forbidden` = the EXECUTED calls
  (tool messages) plus the reply text (adapter-bindings.md). No per-case
  guessing.
- Tool-surface preflight: the eval runner AND a permanent CI unit test assert
  that the FIRST model request's tool names equal the spec's tool set (plus any
  built-in the binding deliberately keeps, each with its reason in build.md).
  Test doubles must not change the tool surface.
- Name the capture source.>

## A2A and MCP
<A2A path (native / licensed / own a2a-sdk server) and MCP client.>

## Pinned version and traps
<Exact pins (and hash pinning where a card trap says so) plus the card's
traps restated as build obligations.
- Every package the binding names gets an exact pin in the lockfile; any ">="
  in the text is a minimum, never a requirement spec.>
```
