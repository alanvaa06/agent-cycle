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
- Post-run commit order. Own-loop stacks: (a) ONE transaction that persists
  the run's messages/state, writes or deletes the pending-approval record
  (`requested_at` = now, taken just before sending; the record is deleted in
  the SAME transaction that stores the resume's messages), sets the turn
  status, and sets `processed_at` and the reply text on the ingress dedupe
  record of the dequeued message; (b) send the prompt or reply; (c) ack the
  queue message. Checkpointer stacks: the checkpointer has committed during
  the run; then one repository transaction writes `requested_at` and the
  dedupe record's `processed_at` and reply; then send; then ack. A pending
  interrupt with no `requested_at` is treated as requested now.
- Redelivery: the ingress dedupe record (keyed by the channel message id)
  carries `processed_at` and the reply text. On dequeue, a message whose
  record has `processed_at` set is not re-run: re-send the stored reply if the
  send may not have happened, then ack. Ingress dedupe alone only catches
  channel retries; this closes queue redelivery after a worker crash. The
  step-2a expiry commit does NOT set `processed_at`: only the final post-run
  commit of the turn that handles the message sets it.
- Pending-record lifecycle: every pause writes a NEW pending record with a
  fresh UUID `approval_id` (never the session key, never reused across pauses
  or turns). Any run started from a pending record deletes it in the post-run
  transaction unless the run ended in a NEW pause, which writes a fresh record
  (new id) in that same transaction. "Ended in a pause" = pending calls
  non-empty AND the run completed without an exception or timeout; otherwise
  discard the pending calls (a wall-clock abort with a gated call pending must
  not write a record). Checkpointer stacks: a pending interrupt found at step 2
  with no record (crash after the checkpoint commit, or a timeout after the
  interrupt was checkpointed) gets a fresh record (new UUID `approval_id`,
  `requested_at` = now) before prompting or resuming.
- Crash marker (own-loop stacks): write the turn status `running` at turn
  start, after the repair, and overwrite it with the outcome on every exit.
  The repair treats `running` or a missing status row as a crash and writes
  "outcome unknown", never "not executed".
- Every spike states its pass test and runs before build-guide Step 4. Every
  sessions/store spike, on failure, STOPS and raises a re-entry on the
  design's sessions seam; never a silent store swap. Other spikes state their
  own failure path (a binding defect -> fix the binding; telemetry -> its
  fallback).>

## HITL gate
<How gated/destructive tiers pause for approval and resume; idempotency
rules for work done before the pause.
- The numbered worker sequence: dequeue -> check this session for a pending
  approval -> resume with the decision OR start a new turn. Step 2a (expiry)
  deletes the pending record but does not set the dedupe record's
  `processed_at`.
- Idempotency key for a gated/destructive call: unique per APPROVED CALL,
  `"<approval_id>:<call index or function_call_id>"`, where `approval_id` is the
  fresh UUID of the pending record (see Sessions and state). A resume that
  pauses again writes a new record with a new id, so keys are never reused
  across pauses or turns; the key is stable across queue redelivery because the
  record is deleted only in the post-run transaction. Spike pass test: resume
  -> second pause -> second approval yields distinct keys and the second tool
  body runs.
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
  Test doubles must not change the tool surface. Name how the first
  request's tool names are observed.
- The eval runner drives the worker's single turn handler (dequeue logic,
  expiry, repair, resume-or-end, cap mapping) against an in-memory
  implementation of the repository interface, never the framework's run call
  directly, so the deny, expiry and cap branches cannot diverge from
  production.
- `tool_always_errors` = the tool's injected BACKEND double raises and the real
  tool returns the spec's error observation (build-guide Step 5); the tool
  surface never changes.
- Name the capture source.>

## A2A and MCP
<A2A path (native / licensed / own a2a-sdk server) and MCP client.>

## Pinned version and traps
<Exact pins (and hash pinning where a card trap says so) plus the card's
traps restated as build obligations.
- Every package the binding names gets an exact pin in the lockfile; any ">="
  in the text is a minimum, never a requirement spec.>
```
