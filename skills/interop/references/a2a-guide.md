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
