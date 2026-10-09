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
including failing and malicious ones (evals), the delegate's inbound contract (owned by the
delegate's spec, published by its interop), gate, contract and live checks (ship of the
orchestrator), a handler check and a contract-bump block (ship of the delegate), and the
weekly live check (runbook). Eval cases first; release v0.13.0.

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
| Re-record trigger | The delegate's contract version changes (shape of input/output), not every delegate ship | Delegates can improve internally without reopening the orchestrator. Known risk (same shape, worse content) recorded in `todo.md` to revisit; the weekly probe catches it on the probe request only. |
| Delegate contract bump | Blocks the delegate's ship while an orchestrator's latest approved ship-report pins the older version, unless the delegate still serves it | The check reads what the orchestrator has SHIPPED; otherwise shipping the delegate breaks the orchestrator in production. |
| Owner of a delegate's inbound interface | The delegate's spec (ingress, untrusted surface for its callers, probe no-side-effect BHV); evals, build and interop follow | An interface with no spec has no BHV, no eval and no anti-gaming coverage; a build-only re-entry would ship untested code. |

## 4. Design — orchestrator mode

### 4.1 When it applies

Design is in orchestrator mode when the agent being designed (in a workspace) would call one
or more other agents listed in `agent-cycle.yaml`. Detected from the interview (the user
names existing agents as things this agent hands work to) or stated by the user. Delegates must be workspace agents: in a one-agent repo design first
shows the v0.12 conversion (interview-guide "Second agent in a one-agent repo") and stops.

### 4.2 Justification test

Before any delegate is inventoried, design runs the test (interview-guide Phase C2, before
design.md is created); an orchestrator verdict records it in a new **design.md §9
Delegation**. First: is routing mechanical (by channel or keyword)? If so the verdict is
"router without an LLM" even when the reasons below hold — reuse justifies separate agents,
not an LLM in front of them. Otherwise an orchestrator is justified only when at least one
reason holds, each written with a concrete fact from this case:

1. **Reuse:** the delegate already exists as an agent with its own channel or releases.
2. **Separate permissions:** one merged agent would need credentials it should not hold.
3. **Context too large:** one agent would carry too many tools or conflicting instructions.
4. **Different models or costs:** parts need different models (an expensive one and a cheap
   one).

Two outcomes produce no orchestrator, and both are successful outcomes (the router check
runs first). When no new agent results, design writes NO file and does not touch
`agent-cycle.yaml` (append-only, hook-enforced): it states the verdict and the §9-style
reasoning in chat.
- **One agent:** no reason holds → add the work to an existing agent (design re-entry of
  that agent, a separate run; no file now) or design one new agent that does the whole
  job (design continues; its §9 is "No delegation: <reason>").
- **Router without an LLM:** routing is mechanical (by channel or keyword) → plain code
  outside agent-cycle. Design names it in chat, writes nothing, and stops.

### 4.3 Delegate inventory

When justified, §9 lists each delegate: agent name (must be in `agent-cycle.yaml`), what it
is used for, which reason(s) above it serves. Each delegate is also a tool: it is added to
design §4's tool inventory with a tier guess. Subagents that exist only to serve this agent
are NOT delegates: they stay in §3/§8 as internal subgraphs/subagents of this agent's stack.

Design reads other agents' `docs/agent/design.md`, `docs/agent/interop.md` and the
frontmatter of `docs/agent/build.md` (whether the delegate is built) to build the inventory
(read-only; §8 adds this exception to `references/agent-root.md`). A delegate's inbound
interface is owned by the DELEGATE'S SPEC. If a delegate has no inbound interface for this
orchestrator, design warns: adding it is a spec re-entry of that delegate — a new
ingress/channel in its spec (§3), an untrusted surface in its §4 for its callers with an
injection-attempt BHV, and a BHV proving the probe request has no side effects; then its
evals, then its build (the handler), then its interop publishes the contract version in
Inbound contracts. On an already-built delegate this re-entry is the human's, hook off
(the build skill's `references/forge-delegation.md` re-entry steps), in a commit separate
from the orchestrator's work. The ideal order (design the orchestrator before building its
delegates) is advised, not required.

## 5. Spec — delegates table

New **spec.md §8 Delegates** (orchestrators only; one row per delegate):

| Column | Content |
|---|---|
| Delegate | agent name, e.g. `ventas` |
| Used by | BHV ids that call it |
| Input | schema of what the orchestrator sends |
| Output | schema of what it expects back |
| Contract | pinned contract version, one listed on the `Served:` line of the delegate's Inbound contracts entry for this caller, e.g. `ventas-contract@1` |
| On failure | what the orchestrator does when the delegate is down, times out or returns invalid output (retry, tell the user, hand to a human); one BHV per mode |

Rules:
- Each delegate is also a tool: a §2 tool contract per delegate that references its §8 row.
- Each On failure mode (down, timeout, invalid output) has its own BHV, listed in Used by,
  so every failure eval case has a `bhv_ref`.
- Delegates are untrusted counterparts: their output rides the spec's untrusted envelope, and
  any gated/destructive action a delegate's reply implies goes through the orchestrator's own
  HITL tiers (interop rule 6, unchanged).
- Each delegate the orchestrator authenticates to adds a row to §4's credential table (least
  privilege applies).
- A delegate whose contract is not yet published (its interop not approved) → spec records
  the row with `Contract: pending`. Evals refuses while a pin is pending (stops, names the
  delegate); in ship a pending or not-served pin is a blocker. Pinning it after the
  orchestrator's build is a human re-entry (spec, evals, build).

## 6. Evals — recorded delegate responses

The orchestrator's suite replaces each delegate with recorded responses. Per delegate:
- at least one golden case with a valid recorded response;
- one case per "On failure" mode in the spec row (down, timeout, invalid output), each
  citing that mode's BHV;
- adversarial cases per evals rule 5 (the delegate's replies are an untrusted surface, so
  at least 2 realistic payloads) where the reply carries injected instructions or asks for
  a gated action; expected: the orchestrator treats it as data and the gated action still
  requires HITL;
- its golden probe response (`evals/delegates/<agent>-probe.json`: the published probe
  request, the expected reply, optionally a rubric), used by the weekly live check.

A case fixture holds `response` (every call) or `responses: [...]` (one per call, in order;
for an A2A delegate one entry per turn with its task state). The build's eval runner
materializes `fixture.delegates` as backend doubles of the delegate endpoint: down =
connection refused, timeout = a delay past the client timeout, invalid = the raw payload.

Recordings live in the orchestrator's `evals/` and are frozen by the hook after build like
every eval file. They record the delegate contract version they were taken from.
Re-recording is a human re-entry (§3), only on a contract version bump.

## 7. Ship

### 7.1 Ship of an orchestrator

New sub-section in audit-guide Section 3 ("Delegates"), run when spec §8 lists at least one
delegate. Cross-agent reads and greps run from the repo root (not `AGENT_ROOT`); in a
workspace a grep that matches nothing is an error to report, not a pass (the delegate's
Dependents check, where "no orchestrator pins this agent" is legitimate, lists the files it
searched).
- **Gate** (in Section 0 with the rest of the chain, before the suite re-run): each delegate
  has an approved `interop.md` that publishes Inbound contracts for this caller and an
  approved `ship-report.md` that covers its current interop (`interop_version` in its
  frontmatter equals its `interop.md` version; older → refuse, the delegate must re-ship).
  Missing → refuse, naming the delegate and the phase.
- **Contract:** the version pinned in spec §8 is AMONG the versions on the `Served:` line of
  the delegate's Inbound contracts entry. Pending or not served → blocker routed to the
  orchestrator's re-entry (spec, evals, build; the human's, hook off).
- **Live call:** one real call per delegate, sent to the delegate's base URL from THIS
  agent's deploy configuration (the env/config key its delegate client reads), authenticated
  with this agent's delegate credential, using the side-effect-free **probe request** the
  delegate publishes in its inbound contract (§8) — never a request that writes or triggers
  a gated action; the response validates against the pinned output schema. Cite the command
  and output. A failure is a finding (route: delegate if it is down or off-contract;
  orchestrator if its client is wrong).
- **Credentials:** the orchestrator's delegate credentials are included in Section 3's least
  privilege diff.
- **Report:** the ship-report frontmatter records the pins this ship validated,
  `delegate_contracts: [<agent>-contract@<n>, ...]`, plus `interop_version` (every agent).

### 7.2 Ship of a delegate

Two checks in Section 3:
- **Inbound contracts:** for each entry in this agent's `interop.md`, cite the handler
  file:line and the BHV covering the probe's no-side-effect claim. Missing → finding routed
  to this agent's spec re-entry (the interface is owned by its spec).
- **Dependents (contract bump):** the check reads what each orchestrator has SHIPPED. From
  the repo root, find the orchestrators whose spec §8 names this agent and read the
  `delegate_contracts` in each one's latest approved ship-report. A version pinned there
  that this ship no longer lists on `Served:` is a **blocker** routed to the orchestrator
  (spec, then evals with re-recording, then build — the human's, hook off — and a ship of
  the new pin) or to this agent, to keep serving the old version. A delegate may stop
  serving a version only when no orchestrator's latest approved ship-report pins it. Order:
  the delegate serves both → the orchestrator re-enters spec, evals and build and ships the
  new pin → the delegate drops the old version.

### 7.3 Runbook

The runbook template's weekly ritual adds, for orchestrators: the live call per delegate
(same target and credential as §7.1), and what happens to the orchestrator when a
delegate's kill switch is used (its "On failure" path). The live reply is compared with the
pinned schema and with the recorded golden probe response (or its rubric). It catches
schema drift and same-shape worse content on the probe request; it does not catch worse
content on other requests. Drift or worse content without a contract bump routes to the
DELEGATE, never to re-recording; re-recording happens only on a contract bump. Audit-guide
Section 6 checks these items in an orchestrator's runbook.

## 8. Interop and other skills

- **interop (delegate side):** the inbound relationship "orchestrator X calls me" is recorded
  like any other relationship row. When it warrants an interface, `interop.md` gains an
  **Inbound contracts** section (written in both the skip and the A2A decision): caller,
  input schema, output schema, protocol verdict, contract version, a fixed line listing the
  versions still served (`Served: <agent>-contract@1, <agent>-contract@2`), the handler
  file:line and the probe's no-side-effect BHV, and one side-effect-free probe request with
  its expected response (shape plus a sample the caller records as its golden probe
  response), used by the caller's ship and weekly live check. A shape change bumps the
  version. The interface is owned by the delegate's spec: a missing handler or missing spec
  coverage is a spec re-entry of the delegate (spec, evals, build, then interop publishes),
  never a build re-entry alone. The delegate's relationship inventory includes every
  workspace agent whose design §9 or spec §8 names it (read-only).
- **interop (orchestrator side):** each delegate gets the existing entry test (A2A vs simple
  call); the verdict is recorded with the pinned contract and cites the protocol the
  delegate published in its Inbound contracts entry. On disagreement the delegate's verdict
  wins.
- **references/agent-root.md:** new read-only cross-agent exceptions: design of an
  orchestrator reads other agents' `design.md`, `interop.md` and `build.md` frontmatter;
  spec of an orchestrator reads its delegates' `interop.md`; interop reads other agents'
  design §9 and spec §8 to find its callers; ship of an orchestrator reads its delegates'
  `interop.md` and `ship-report.md`; ship of any agent reads other agents' spec §8 tables
  and the frontmatter of their latest approved `ship-report.md`; economics of an
  orchestrator reads its delegates' economics artifacts. These reads run from the repo root.
  A delegate's re-entry and the orchestrator's work go in separate commits (a shared commit
  is a mixed-agent ship finding).
- **economics:** an orchestrator's cost per turn includes its delegates' cost per call times
  calls per turn.
- **blueprint:** renders delegates as external agents with their contract version.
- **hook:** no change. Spec §8 and the recordings are frozen by the existing rules.

## 9. Evals (written before the skill changes — EDD)

| Skill | Case | Proves |
|---|---|---|
| design | DES-E09 | Routing is by keyword → verdict "router without an LLM" even though reuse holds; stated in chat, no file written, `agent-cycle.yaml` untouched |
| design | DES-E10 | Justified orchestrator: §9 lists delegates from `agent-cycle.yaml` with their reason, each also a §4 tool; an in-process helper stays out of the delegate list; warns that a built delegate without an inbound interface needs a spec re-entry of that delegate (human, hook off) |
| design | DES-E11 | Routing not mechanical and no reason holds → verdict "one agent" stated in chat with the reasoning; adding the work to an existing agent writes no file |
| spec | SPC-E06 | §8 Delegates with every column, pin read from the `Served:` line, `pending` for an unpublished contract, a BHV per "On failure" mode, a §2 tool contract per delegate, delegate credentials in §4 |
| evals | EVL-E05 | Recorded responses per delegate: golden, one per failure mode (with its BHV), adversarial per rule 5; recordings carry the contract version |
| interop | ITP-E05 | Delegate records the inbound contract with a version and a `Served:` line; a missing handler routes to a spec re-entry of the delegate |
| ship | SHP-E06 | Orchestrator whose delegate has no approved ship-report → refuse naming it; with all delegates shipped, pin among served versions + live call (deploy-config base URL) cited; report records `delegate_contracts` |
| ship | SHP-E07 | Delegate ships contract @2 while an orchestrator's approved ship-report pins @1 and @1 is not served → blocker |

## 10. Release

- **v0.13.0** — minor (new pipeline capability). CHANGELOG with upgrade notes: orchestrator
  mode is opt-in; one-agent repos and v0.12 workspaces without orchestrators are unchanged.
- Pending graduation: a real workspace where an orchestrator and two delegates are taken
  through ship.

## 11. Risks

| Risk | Mitigation |
|---|---|
| The justification test becomes a rubber stamp | Each reason needs a concrete fact from the case; DES-E11 proves the "one agent" outcome and DES-E09 the "router without an LLM" outcome. |
| Recordings drift from the real delegate | Weekly live check detects (schema and golden probe response); drift without a contract bump routes to the delegate; human re-entry re-records only on a bump; the contract pin catches shape changes at ship. |
| Same shape, worse content from a delegate | Not caught at ship. The weekly live check catches it on the probe request only (compared with the recorded golden probe response or its rubric); worse content on other requests is not caught. Recorded in `todo.md` to revisit (pin by ship tag instead). |
| Delegate built before the orchestrator lacks an inbound interface | Design warns; spec re-entry of the delegate (its spec owns the interface; then evals, build, interop), the human's with the hook off. |
| Contract bump breaks the orchestrator in production | Delegate's ship blocks while an orchestrator's latest approved ship-report pins the older version and it is not served. |
| Latency/cost of network calls | Economics counts delegate cost; in-process composition remains available for components that are not agents. |
