# Agent root — which agent a skill is working on

Every agent-cycle skill resolves `AGENT_ROOT` before touching any path. All
paths the skills name (`docs/agent/...`, `evals/...`, `src/...`, `tests/...`)
are relative to `AGENT_ROOT`; git commands that take paths prefix them with it.

## Layouts

- **One-agent repo:** no `agent-cycle.yaml` at the repo root. `AGENT_ROOT` is
  the repo root. This is the layout every repo had before v0.12.
- **Workspace:** `agent-cycle.yaml` at the repo root:

  ```yaml
  layout: workspace
  agents: [ventas, soporte]      # each lives at agents/<name>/
  ```

  `<name>` is the design's `agent_name` (kebab-case). The path is always
  `agents/<name>/`; there are no configurable paths.

## Resolution order

1. No `agent-cycle.yaml` -> `AGENT_ROOT` = repo root.
2. The working directory is inside `agents/<name>/` -> that agent.
3. The user's request names an agent in `agents:` -> that agent.
4. `agents:` has exactly one entry -> that agent.
5. Otherwise -> ONE question listing the agents as lettered options.

## Rules

- A skill reads and writes only inside `AGENT_ROOT`, except: design appends a
  new agent's name to `agent-cycle.yaml`; build's baseline commit may include
  `agent-cycle.yaml`; ship reads other agents' paths only to detect commits
  that touch two agents.
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
