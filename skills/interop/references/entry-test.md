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
the row proves they were considered. In a workspace, also add one row per
agent whose design §9 or spec §8 names THIS agent as a delegate (inbound),
and one row per delegate in this agent's spec §8 (outbound).
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
- the Inbound contracts section when another workspace agent calls this one
  (below);
- **re-visit triggers**: an enterprise client asks this agent to delegate to
  or accept work from their agents; a flow outgrows bounded semantics
  (multi-turn negotiation with an external party); listing the agent on a
  registry/marketplace (AaaS); a counterpart agent appearing in the spec via
  re-entry.

## Decision: A2A

Only for the flagged relationships. Proceed to `references/a2a-guide.md`.
Never author a card "for the future" — the future has a re-visit trigger.

## Inbound contracts (delegates)

When another workspace agent calls this one, `docs/agent/interop.md` carries
an **Inbound contracts** section in BOTH decisions (skip or A2A), one entry
per caller:
- caller (agent name), input schema, output schema;
- protocol: this relationship's entry-test verdict (A2A or simple call);
- contract version `<this-agent>-contract@<n>`; any change to the input or
  output shape bumps `<n>`;
- one fixed line listing every version still served, so greps are
  mechanical: `Served: <this-agent>-contract@1, <this-agent>-contract@2`;
- the handler that serves the interface (file:line in the built code) and the
  BHV in this agent's spec that proves the probe has no side effects;
- one **probe request**: side-effect-free (no writes, no gated action), with
  its expected response (shape plus one sample reply the caller records as
  its golden probe response). The caller's ship and weekly ritual use it.

The interface is owned by THIS agent's spec. No handler in the built code, or
no spec coverage for it (the ingress/channel in §3, an untrusted surface in
§4 for its callers with an injection-attempt BHV, the probe's no-side-effect
BHV) → SPEC re-entry of this agent: spec, then evals, then build (the
handler), then this interop publishes the version. Never improvised here,
never a build re-entry alone. On a built agent that re-entry is the human's,
hook off (the re-entry steps in the build skill's
`references/forge-delegation.md`); this agent's re-entry and the caller's
work go in separate commits (a shared commit is a mixed-agent ship finding).

Dropping a served version: only when no orchestrator's latest approved
ship-report pins it (`delegate_contracts` in its frontmatter). Order: serve
both versions → the orchestrator re-enters spec, evals and build and ships
the new pin → this agent drops the old version from `Served:`.

Orchestrator side: each delegate in this agent's spec §8 gets its own row and
verdict, recorded with the pinned contract. The protocol cites the one the
delegate published in its Inbound contracts entry; on disagreement the
delegate's verdict wins (it owns the interface) and this agent's spec
re-enters to match.
