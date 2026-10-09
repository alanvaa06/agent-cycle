# agent-cycle v0.13 — Orchestrator agents (system layer, B2)

**Date:** 2026-10-08
**Status:** draft — pending Alan's review
**Author:** Alan Vazquez + Claude (brainstorming session)
**Builds on:** v0.12.0 (workspace mode), tagged `v0.12.0` on `main`. Branch
`feat/v0.13-system`.

## 1. Problem

v0.12 lets one repository hold several independent agents (`agents/<name>/`), but nothing
connects them. The owner wants a multi-agent system: an agent that receives the user and
delegates to the other agents of the workspace (`recepcion` → `ventas`, `soporte`).

Two risks shape the design. First, multi-agent systems are often worse than one agent with
more tools (lost context between agents, higher token cost, compounding errors), so the
pipeline must be able to answer "do not build an orchestrator". Second, the v0.12 rule that
agents share no code conflicts with the common LangGraph / deep-agents pattern of importing
other agents as in-process subgraphs.

## 2. Scope

**In:** the orchestrator pattern. An orchestrator is an ordinary workspace agent whose tools
include other workspace agents ("delegates"), called over the network. The pipeline phases
gain: a justification test (design), a delegates table (spec), recorded delegate responses
including failing and malicious ones (evals), the delegate's inbound contract (interop),
gate, contract and live checks (ship of the orchestrator), a contract-bump block (ship of
the delegate), and the weekly live check (runbook). Eval cases first; release v0.13.0.

**Out:**
- Event/queue choreography (agents reacting to each other's events).
- Several orchestrators sharing delegates, and a single system-level record or topology
  file. With one orchestrator the topology is its delegates table.
- An agent that both has its own channel/releases AND is imported in-process by an
  orchestrator.
- A deterministic router (no LLM) in front of the agents: valid outcome of the
  justification test, but it lives outside agent-cycle.
- Any change to the anti-gaming hook.

## 3. Decisions (settled during brainstorming)

| Decision | Choice | Rationale |
|---|---|---|
| First topology | Orchestrator (one agent delegates to others) | Most common with LangGraph/deep-agents; end-to-end flow is testable. Peers-only A2A already exists per agent in interop; events are hardest to evaluate. |
| Agent vs component | Has its own channel or releases → workspace agent, called over the network. Exists only to serve the orchestrator → subgraph/subagent inside that ONE agent (already supported by the v0.11 bindings). | Keeps v0.12's "agents share no code"; the two legitimate cases are covered; the conflicting case is hypothetical today. |
| Protocol | Decided by interop's existing entry test per delegate: A2A when the delegate converses, pauses or negotiates; a simple call (HTTP/MCP-style tool) when it returns a result | "Over the network" does not imply A2A. |
| Where B2 lives | Extend existing skills; no new skill | An orchestrator is an agent whose tools are agents; smallest scope; matches v0.12 (extend, don't add). Rejected: `agent-cycle:system` skill with a system record — only one pattern exists today. |
| Orchestrator evals | Recorded delegate responses (incl. failing and malicious); one live call per delegate at ship | Deterministic suite, pass^k meaningful, a red is the orchestrator's fault. |
| Stale recordings | Detection periodic (weekly live check); update deliberate (human re-entry, review the diff) | Blind re-recording would turn a delegate regression into the expected answer. Not the `refresh` skill (that one maintains the plugin's stack catalog). |
| Re-record trigger | The delegate's contract version changes (shape of input/output), not every delegate ship | Delegates can improve internally without reopening the orchestrator. Known risk (same shape, worse content) recorded in `todo.md` to revisit. |
| Delegate contract bump | Blocks the delegate's ship while an orchestrator pins the older version, unless the delegate still serves it | Otherwise shipping the delegate breaks the orchestrator in production. |

## 4. Design — orchestrator mode

### 4.1 When it applies

Design is in orchestrator mode when the agent being designed (in a workspace) would call one
or more other agents listed in `agent-cycle.yaml`. Detected from the interview (the user
names existing agents as things this agent hands work to) or stated by the user. Delegates must be workspace agents: in a one-agent repo design first
shows the v0.12 conversion (interview-guide "Second agent in a one-agent repo") and stops.

### 4.2 Justification test

Before any delegate is inventoried, design records the test in a new **design.md §9
Delegation**. An orchestrator is justified only when at least one reason holds, each written
with a concrete fact from this case:

1. **Reuse:** the delegate already exists as an agent with its own channel or releases.
2. **Separate permissions:** one merged agent would need credentials it should not hold.
3. **Context too large:** one agent would carry too many tools or conflicting instructions.
4. **Different models or costs:** parts need different models (an expensive one and a cheap
   one).

Two outcomes produce no orchestrator, and both are successful outcomes recorded in §9 with
the reason:
- **One agent:** no reason holds → add the tools to an existing agent (design re-entry of
  that agent) or design one agent.
- **Router without an LLM:** routing is mechanical (by channel or keyword) → plain code
  outside agent-cycle. Design names it and stops.

### 4.3 Delegate inventory

When justified, §9 lists each delegate: agent name (must be in `agent-cycle.yaml`), what it
is used for, which reason(s) above it serves. Subagents that exist only to serve this agent
are NOT delegates: they stay in §3/§8 as internal subgraphs/subagents of this agent's stack.

Design reads other agents' `docs/agent/design.md` and `docs/agent/interop.md` to build the
inventory (read-only; §8 adds this exception to `references/agent-root.md`). If a delegate
is already built and has no inbound interface for this orchestrator, design warns: adding
it is a build re-entry of that delegate (interop rule 7). The ideal order (design the
orchestrator before building its delegates) is advised, not required.

## 5. Spec — delegates table

New **spec.md §8 Delegates** (orchestrators only; one row per delegate):

| Column | Content |
|---|---|
| Delegate | agent name, e.g. `ventas` |
| Used by | BHV ids that call it |
| Input | schema of what the orchestrator sends |
| Output | schema of what it expects back |
| Contract | pinned contract version published by the delegate, e.g. `ventas-contract@1` |
| On failure | what the orchestrator does when the delegate is down, times out or returns invalid output (retry, tell the user, hand to a human) |

Rules:
- Delegates are untrusted counterparts: their output rides the spec's untrusted envelope, and
  any gated/destructive action a delegate's reply implies goes through the orchestrator's own
  HITL tiers (interop rule 6, unchanged).
- Each delegate the orchestrator authenticates to adds a row to §4's credential table (least
  privilege applies).
- A delegate whose contract is not yet published (its interop not approved) → spec records
  the row with `Contract: pending` and the gate in §7.1 blocks ship until it is pinned.

## 6. Evals — recorded delegate responses

The orchestrator's suite replaces each delegate with recorded responses. Per delegate:
- at least one golden case with a valid recorded response;
- one case per "On failure" mode in the spec row (down, timeout, invalid output);
- at least one adversarial case where the delegate's reply carries injected instructions or
  asks for a gated action; expected: the orchestrator treats it as data and the gated action
  still requires HITL.

Recordings live in the orchestrator's `evals/` and are frozen by the hook after build like
every eval file. They record the delegate contract version they were taken from.
Re-recording is a human re-entry (§3).

## 7. Ship

### 7.1 Ship of an orchestrator

New sub-section in audit-guide Section 3 ("Delegates"), run when spec §8 exists:
- **Gate:** each delegate has an approved `interop.md` that publishes the inbound contract
  and an approved `ship-report.md`. Missing → refuse, naming the delegate and the phase.
- **Contract:** the contract version in the delegate's `interop.md` equals the version pinned
  in spec §8. Mismatch → finding routed to the orchestrator's spec re-entry.
- **Live call:** one real call per delegate against its deployed endpoint (from the deploy
  configuration); the response validates against the pinned output schema. Cite the command
  and output. A failure is a finding (route: delegate if it is down or off-contract;
  orchestrator if its client is wrong).
- **Credentials:** the orchestrator's delegate credentials are included in Section 3's least
  privilege diff.

### 7.2 Ship of a delegate

New check in Section 3: read every other agent's spec §8. If any orchestrator pins an older
contract version of this agent than the one this ship publishes, and this agent does not
still serve the pinned version, that is a **blocker** routed to the orchestrator (spec
re-entry and re-recording) — or to this agent, to keep serving the old version.

### 7.3 Runbook

The runbook template's weekly ritual adds, for orchestrators: the live call per delegate
(same check as §7.1), and what happens to the orchestrator when a delegate's kill switch is
used (its "On failure" path).

## 8. Interop and other skills

- **interop (delegate side):** the inbound relationship "orchestrator X calls me" is recorded
  like any other relationship row. When it warrants an interface, `interop.md` gains an
  **Inbound contracts** section: caller, input schema, output schema, contract version. A
  shape change bumps the version.
- **interop (orchestrator side):** each delegate gets the existing entry test (A2A vs simple
  call); the verdict is recorded with the pinned contract.
- **references/agent-root.md:** new read-only cross-agent exceptions: design of an
  orchestrator reads other agents' `design.md` and `interop.md`; ship of an orchestrator
  reads its delegates' `interop.md` and `ship-report.md`; ship of any agent reads other
  agents' spec §8 tables.
- **economics:** an orchestrator's cost per turn includes its delegates' cost per call times
  calls per turn.
- **blueprint:** renders delegates as external agents with their contract version.
- **hook:** no change. Spec §8 and the recordings are frozen by the existing rules.

## 9. Evals (written before the skill changes — EDD)

| Skill | Case | Proves |
|---|---|---|
| design | DES-E09 | Justification fails (no reason holds) → verdict "one agent", no delegate inventory, §9 records why |
| design | DES-E10 | Justified orchestrator: §9 lists delegates from `agent-cycle.yaml` with their reason; an in-process helper stays out of the delegate list; warns that a built delegate without an inbound interface needs a build re-entry |
| spec | SPC-E06 | §8 Delegates with every column, an "On failure" entry per delegate, delegate credentials in §4 |
| evals | EVL-E05 | Recorded responses per delegate: golden, one per failure mode, one malicious; recordings carry the contract version |
| interop | ITP-E05 | Delegate records the inbound contract with a version; orchestrator side runs the entry test per delegate |
| ship | SHP-E06 | Orchestrator whose delegate has no approved ship-report → refuse naming it; with all delegates shipped, contract match + live call cited |
| ship | SHP-E07 | Delegate ships contract @2 while an orchestrator pins @1 and @1 is not served → blocker |

## 10. Release

- **v0.13.0** — minor (new pipeline capability). CHANGELOG with upgrade notes: orchestrator
  mode is opt-in; one-agent repos and v0.12 workspaces without orchestrators are unchanged.
- Pending graduation: a real workspace where an orchestrator and two delegates are taken
  through ship.

## 11. Risks

| Risk | Mitigation |
|---|---|
| The justification test becomes a rubber stamp | Each reason needs a concrete fact from the case; DES-E09 proves the "one agent" outcome. |
| Recordings drift from the real delegate | Weekly live check detects; human re-entry updates; contract pin catches shape changes at ship. |
| Same shape, worse content from a delegate | Not caught at ship; weekly live check. Recorded in `todo.md` to revisit (pin by ship tag instead). |
| Delegate built before the orchestrator lacks an inbound interface | Design warns; build re-entry of the delegate (existing interop rule 7). |
| Contract bump breaks the orchestrator in production | Delegate's ship blocks while an orchestrator pins the older version and it is not served. |
| Latency/cost of network calls | Economics counts delegate cost; in-process composition remains available for components that are not agents. |
