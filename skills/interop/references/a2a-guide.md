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

Declare how THIS runtime speaks A2A — never assume. Read the "A2A and MCP"
section of the agent-cycle plugin's
`skills/build/references/bindings/<card-id>.md`. Take the card id from
spec.md's `runtime` (`<card-id>@<version>`, or `no-framework@n/a`, whose
binding is `no-framework.md`); for `off-catalog:<name>@<version>` there is no
binding file, so read the "A2A and MCP" section of build.md's "Off-catalog
binding". The section states the paths the stack offers:
- **native** (CrewAI client and server; ADK, experimental in both roles);
- **licensed server** (LangChain family via LangSmith Agent Server, only when
  design §8 records an accepted license: cite it);
- **external server** (Pydantic AI via fasta2a);
- **own `a2a-sdk` server** in front of the ingress queue (available on every
  stack, recommended under HITL).

Record the role(s) per relationship: server (the counterpart calls this
agent) and/or client (this agent delegates). The client is the binding's A2A
client: a tool whose tier follows the design and whose results are untrusted
(Step 2); a native client only when build.md records the spike showing the
gate sees its calls.

Record in interop.md which path was chosen, whether it is licensed or free,
and anything else the section says to record (for example the protocol
version).

If the binding says a path's server (native, licensed or external, e.g. ADK
`to_a2a`, CrewAI's native server, fasta2a, LangSmith Agent Server) runs tasks
outside the ingress queue, the session key, the caps or the HITL gate, or does
not say, the record names that and the path is the own `a2a-sdk` server. A
non-own server path is usable only when build.md records the binding's A2A
spike as passed for that path (task in the ingress queue with the session key
as ordering key; a gated tool reached through it pauses). The HITL gate is
never bypassable, whatever the design says; a design may accept a
queue/session-key bypass only for an agent with no gated tools reachable
through that path (cite where).

Update the agent card's Interaction Schemas (protocol version, paused-task
state) to the chosen path.

If the chosen path requires a handler or client tool the build does not have,
adding it is a BUILD change (re-entry), not something this phase improvises.

## Step 4 — Registry decision

none (direct point-to-point config) / private (org registry, enterprise
sharing) / public (marketplace listing — an AaaS business decision, not a
default). Record the decision + reason. Public listing pulls in pricing,
SLA, and abuse handling — flag those as open questions for the owner, do not
improvise them.

## Step 5 — Record and gate

docs/agent/interop.md: frontmatter (agent_name, version, status: draft,
date, spec_version, build_version), the entry-test table, per-relationship:
card location, role(s), executor binding, registry decision, counterpart-security
notes. Human gate → status: approved. Hand off: "/ship audits this record;
cross-agent flows join the eval suite as untrusted-surface cases."
