# Agent root — which agent a skill is working on

Every agent-cycle skill resolves `AGENT_ROOT` before touching any path. All
paths the skills name (`docs/agent/...`, `evals/...`, `src/...`, `tests/...`)
are relative to `AGENT_ROOT`; git commands that take paths prefix them with it,
and every non-git command (the eval runner, the package manager, the adapter
smoke test, a lockfile `grep`) runs from `AGENT_ROOT`, except the
cross-agent reads of orchestrators, which run from the repo root (Rules).

## Layouts

- **One-agent repo:** no `agent-cycle.yaml` at the repo root. `AGENT_ROOT` is
  the repo root. This is the layout every repo had before v0.12.
- **Workspace:** `agent-cycle.yaml` at the repo root:

  ```yaml
  layout: workspace
  agents: [agent-a, agent-b]      # each lives at agents/<name>/
  ```

  `<name>` is the design's `agent_name` (kebab-case). The path is always
  `agents/<name>/`; there are no configurable paths.

Starting a workspace from scratch: the human creates `agent-cycle.yaml` with
`layout: workspace` and `agents: []` (an empty list is valid), then design
appends each new agent as it creates it. Every other skill, finding an empty
`agents:`, stops and says to run design first.

## Resolution order

1. No `agent-cycle.yaml` -> `AGENT_ROOT` = repo root.
2. The working directory is inside `agents/<name>/` -> that agent.
3. The user's request names an agent in `agents:` -> that agent.
4. `agents:` has exactly one entry -> that agent.
5. Otherwise -> ONE question listing the agents as lettered options.

Exception: design creating a NEW agent in a workspace does not use this order.
Its `AGENT_ROOT` is `agents/<new name>/` (design's step 0), never an existing
agent reached through steps 2-4, even when the working directory is inside
another agent's folder or only one agent is listed.

## Rules

- A skill reads and writes only inside `AGENT_ROOT`, except: design appends a
  new agent's name to `agent-cycle.yaml`; build's baseline commit may include
  `agent-cycle.yaml`; build's hook install and ratchet commits touch
  `.claude/hooks/` and `.claude/settings.json`; ship reads other agents' paths
  only to detect commits that touch two agents, reads the pre-move root paths
  of a sanctioned workspace move, and reads the history of `.claude/hooks/`.
  Orchestrators (design §9 Delegation) add read-only exceptions: design of an
  orchestrator reads other agents' `docs/agent/design.md`,
  `docs/agent/interop.md` and the frontmatter of `docs/agent/build.md` (to
  know whether a delegate is built); spec of an orchestrator reads its
  delegates' `docs/agent/interop.md`; evals of an orchestrator reads its
  delegates' `docs/agent/interop.md` (to seed
  `evals/delegates/<agent>-probe.json` from the published probe for the
  pinned version); interop reads other agents' design §9 and spec §8 to find
  its callers, and interop of an orchestrator reads its delegates'
  `docs/agent/interop.md` (the protocol they published); ship of an
  orchestrator reads its delegates' `docs/agent/interop.md` and
  `docs/agent/ship-report.md`; ship of any agent reads other agents' spec §8
  and the frontmatter of their last approved `docs/agent/ship-report.md`
  (from git history when the working copy is not approved) to find
  orchestrators that pin it; economics of an orchestrator reads its
  delegates' economics artifacts.
  These cross-agent reads and greps run from the REPO ROOT (not from
  `AGENT_ROOT`); in a workspace, a cross-agent grep that matches nothing is an
  error to report, never a pass (ship's Dependents check, where "no
  orchestrator pins this agent" is legitimate, lists the files it searched).
- A delegate's re-entry (for example to add an inbound interface for an
  orchestrator, which starts at the delegate's design) and the
  orchestrator's own work go in separate commits; a commit touching both
  agents is a mixed-agent finding at ship.
- The anti-gaming hook (the agent-cycle plugin's
  `skills/build/assets/guard_artifacts.py`) takes its agents from the
  directories (the repo root and every `agents/<dir>/`), never from this
  file. An agent's `evals/`, `docs/agent/design.md` and `docs/agent/spec.md`
  freeze once its `docs/agent/build.md` exists, and the agent stays frozen
  even if build.md later disappears (ratchet). `agent-cycle.yaml` is
  append-only.
- Agents in one workspace share no code. They may share infrastructure at
  deploy time (one Postgres, one reverse proxy); resource names carry the
  agent prefix (build's adapter bindings).
