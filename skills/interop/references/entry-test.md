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

Inventory = the UNION of every external system/party across the spec's tools,
security/credential, and conversation/channel sections (the channel counts:
it is an external party even when it only carries the human), PLUS any
collaboration the design/spec anticipates. Internal-but-credentialed stores
(e.g. the session DB) get a row too — their verdict is trivially "tool", but
the row proves they were considered.
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
