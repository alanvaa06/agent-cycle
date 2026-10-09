# agent-cycle

Claude Code plugin that runs the **complete construction cycle of an AI agent** —
from idea to shipped, evaluated, observable production agent — as a gated,
disk-backed pipeline of skills. Evals are written before code, artifacts are
contracts, humans gate every phase, and "the suite is green" is only ever an
exit code.

## Install

From an interactive Claude Code session:

```
/plugin marketplace add alanvaa06/agent-cycle
/plugin install agent-cycle@agent-cycle
```

Update later with `/plugin marketplace update agent-cycle` and reinstall.

## The production cycle

Seven **vertical phases** run in sequence, each gated by an approved artifact
from the previous one. Three **horizontal transversals** attach at any point —
they read whatever artifacts exist and never block the chain.

```mermaid
flowchart TB
    REV["review · HORIZONTAL<br/><i>any existing agent in →<br/>findings + fix-route per phase out</i>"]
    REV -.->|"entry point:<br/>adopt the cycle"| D

    D["1 · design<br/><i>design.md — what the agent is,<br/>how success is measured</i>"]
    S["2 · spec<br/><i>spec.md — exact behavior,<br/>tools + tiers, security</i>"]
    E["3 · evals<br/><i>evals/ — the exams,<br/>written before code, red by design</i>"]
    B["4 · build<br/><i>src/ + runner —<br/>code until the suite is green</i>"]
    K["5 · skills — conditional<br/><i>skills.md (none = success)</i>"]
    I["6 · interop — conditional<br/><i>interop.md (skip = success)</i>"]
    H["7 · ship<br/><i>ship-report.md →<br/>SHIP / NO-SHIP</i>"]

    D --> S --> E --> B --> K --> I --> H

    ECO["economics · HORIZONTAL<br/><i>monthly cost, break-even,<br/>token-spend alarm</i>"]
    S -.->|"run #1 after spec:<br/>estimate — worth building?<br/>quote the client"| ECO
    B -.->|"run #2 after build:<br/>recalibrate with real usage"| ECO
    ECO -.->|"alarm threshold"| H

    BLP["blueprint · HORIZONTAL<br/><i>one-page client-shareable HTML,<br/>renders whatever exists</i>"]
    S -.->|"typical: after spec<br/>(sell it)"| BLP
    B -.->|"typical: after build<br/>(show the real thing)"| BLP

    H -->|"findings"| RL(("re-entry<br/>ladder"))
    RL -.->|"re-opens the<br/>owning phase"| D
```

**When to run the horizontals:** `review` BEFORE the cycle (an existing agent
is the input; its remediation map is the adoption plan). `economics` twice —
right after `spec` (you now know what it does and on which model: decide
whether it is worth building / quote the client, before paying for a build)
and again after `build` (recalibrate the estimate with real usage; its alarm
threshold feeds `ship`). `blueprint` any time after `design` — typically after
`spec` to sell and after `build` to show the real thing.

**The re-entry ladder:** when anything downstream finds a defect in an
upstream artifact, the fix goes back to the *lowest phase whose artifact is
wrong* (version bump → surgical staleness → re-approve). The builder never
edits evals or specs — that path is mechanically blocked.

## The 11 skills, in plain words

### The 7 phases — in order, each needs the previous one approved

**1 · `design` — decide WHAT you want and how you'll know it works.**
It interviews you, one question at a time, and writes the blueprint. Like the
floor plan of a house before laying a single brick. Example: "an assistant
that saves me half the time I spend checking my calendar and Notion."
It also picks the stack with you: filters out frameworks that can't meet your
constraints, shows 2-3 with cited pros and cons, and you choose.
*Use it when:* starting a new agent from an idea. *Skip it when:* you want to
examine an agent that already exists — that's `review`.

**2 · `spec` — turn the idea into exact instructions.**
What the agent does in every situation (with concrete "if I say X, it does Y"
examples), which tools it has and how dangerous each one is, and what it must
NEVER do. *Use it when:* the design is approved. *Skip it when:* there's no
approved design yet.

**3 · `evals` — write the exams BEFORE building.**
Every behavior gets a test, including trap questions (like injection attempts
hidden in a calendar invite). All exams FAIL at first — of course they do,
the agent doesn't exist yet. An exam that passes against nothing is a broken
exam. *Use it when:* the spec is approved. *Skip it when:* you want generic
unit tests for normal code.

**4 · `build` — write the code until every exam passes.**
The only phase that produces code. "It's done" is never an opinion — it's the
exam runner saying every test passed. It also installs a lock so the builder
can't cheat by editing the exams. *Use it when:* design + spec + evals are
all approved. *Skip it when:* any of those is missing or outdated.

**5 · `skills` — does the agent need loadable "procedure manuals"?**
Think: 12 different return policies, one per client, loaded only when needed.
Most agents don't need this — and "no, here's why" is a perfectly good
outcome that gets written down. *Use it when:* the build is done. *Skip it
when:* you're writing Claude Code skills outside this pipeline.

**6 · `interop` — does the agent need to TALK to other agents?**
Real conversation: negotiating, delegating, waiting for answers. Asking an
API for data does NOT count — that's just a tool. Most agents don't need
this either; "skip, here's why" gets written down. *Use it when:* the build
is done. *Skip it when:* you just need an API integration.

**7 · `ship` — the final inspection before it goes live.**
Like a vehicle inspection: re-runs ALL the exams live (doesn't trust old
paperwork), checks security, verifies there's an off switch and a way to roll
back. Verdict: SHIP or NO-SHIP. A NO-SHIP means the system worked — it
caught something before your client did. *Use it when:* the whole chain is
approved. *Skip it when:* you want to deploy a normal app, or fix things —
this skill only inspects.

### The 3 horizontals — they never block anything, run them when it helps

**`economics` — what does it cost per month to keep it on?**
Run it TWICE. First right after `spec`: you now know what it does and which
model it uses — decide if it's worth building, or quote the client, BEFORE
paying for a build. Again after `build`: correct the estimate with real
usage. Example verdict: "$13–19/month — pays for itself if it saves you 12
minutes a month." *Skip it when:* you just want generic API price info.

**`blueprint` — the pretty one-pager.**
A single HTML page showing what the agent is, what it does, what it costs and
how far along it is. Works offline, safe to share with a client, prints
cleanly. Typical moments: after `spec` (to sell it) and after `build` (to
show the real thing). *Skip it when:* you want a generic diagram.

**`review` — the front door.**
Point it at ANY existing agent — yours or someone else's, built with this
pipeline or not — and it tells you what's missing, with file-and-line
evidence, and WHICH phase of this cycle would fix each gap. A client walks in
with their bot; walks out with a diagnosis that doubles as the proposal.
*Skip it when:* the code has no agent in it (that's normal code review), or
you want the release inspection of a pipeline agent (that's `ship`).

### Maintenance — for the plugin itself

**`refresh` — keeps the stack catalog honest.** Run it inside this repo now
and then (or after a project logged catalog drift). It re-checks every
framework card against current docs, updates what changed with sources, and
leaves the changes for you to review. It never commits.

### Several agents in one repo

A repository can hold several independent agents. Each one lives under
`agents/<name>/` with its own `docs/agent/`, `evals/`, `src/` and build state,
and `agent-cycle.yaml` at the repo root lists them (`layout: workspace`,
`agents: [...]`; it is append-only). One-agent repos keep the flat layout and
nothing changes for them. Every skill resolves which agent it is working on
first (`references/agent-root.md`), and the anti-gaming hook freezes each agent
from its own state, never from a static list. To add a second agent to a
one-agent repo, run `design`: it shows the conversion commands (hook upgrade,
then the workspace move) for you to run from your own terminal, and you run it
again afterwards for the new agent.

### Orchestrator agents

An orchestrator is an agent that hands work to other agents in the same
workspace, over the network (A2A or HTTP) only. A helper that only serves one
agent is an internal subagent, not a delegate, and stays inside that agent.
`design` §9 Delegation runs a justification test before any delegate is
listed, and it can say no: if routing is mechanical the verdict is "router
without an LLM" (plain code outside agent-cycle), and if no reason holds with
a concrete fact it is "one agent"; when no new agent results, design writes
no file. A delegate's inbound interface belongs to the delegate's own spec;
its `interop.md` then publishes Inbound contracts with a version, a
`Served:` line and a probe request. `ship` checks that the pin is served,
sends one live probe to each delegate, and blocks a delegate that would drop a
version an orchestrator has shipped. Opt-in: one-agent repos and workspaces
without orchestrators are unchanged.

## Core contracts

- **Disk-backed artifacts** land in the TARGET AGENT'S repo (`docs/agent/*`,
  `evals/`, `src/`) — this plugin repo never contains agent artifacts.
- Every artifact carries frontmatter (`agent_name, version, status, date` +
  upstream version pins). Phases **fail hard** on missing, draft, or
  version-stale upstream artifacts.
- **Human gate between every phase** — no skill ever self-approves.
- **EDD everywhere**: every skill in this plugin was built evals-first against
  its own 4-case contract (`skills/*/evals/`), and teaches the same discipline
  to the agents it builds.

## Versioning

Semver, driven by `.claude-plugin/plugin.json`:

- **minor** — a new pipeline skill or a new pipeline capability lands.
- **patch** — fixes to existing skills or docs.
- Each skill also graduates via its own eval gate (see `skills/*/evals/`);
  graduation is tagged (`<skill>-v0.1`) independently of plugin releases.

See `CHANGELOG.md` for release history.

**Status:** v0.13.0 — all 7 phases + 3 transversals + refresh. 11 skills. Built
skill-by-skill, each dogfooded on a real agent.

## License

MIT — see `LICENSE`.
