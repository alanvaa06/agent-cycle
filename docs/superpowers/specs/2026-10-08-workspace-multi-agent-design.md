# agent-cycle v0.12 — Workspace mode (several agents per repo)

**Date:** 2026-10-08
**Status:** draft — pending Alan's review
**Author:** Alan Vazquez + Claude (brainstorming session)
**Builds on:** v0.11 (stack decision, catalog, per-stack bindings, refresh) — branch
`feat/v0.11-stack-decision`, PR alanvaa06/agent-cycle#3. This work is branched from it
(`feat/v0.12-workspace`) and is rebased onto `main` once #3 merges.

## 1. Problem

The pipeline assumes one agent per repository: about 110 path references across the 12
skills (`docs/agent/design.md`, `docs/agent/spec.md`, `evals/`, …) are relative to the repo
root, the anti-gaming hook freezes `evals/` and `docs/agent/` at the repo root for the
duration of a build, and `build_start` plus ship's anti-gaming diff cover repo-wide paths.
A second agent in the same repository would overwrite the first one's artifacts, be blocked
by the first one's hook, and pollute the first one's ship audit.

The owner's goal: one repository is a workspace where agents are created one after another,
each with its own design → ship cycle, and later optionally connected into a multi-agent
system.

## 2. Scope

**In (B1):** several independent agents per repository; an agent-root resolution rule every
skill follows; one persistent, state-driven hook for the whole workspace; per-agent
`build_start`, commits and ship audit; resource-name prefixing; the hook as a real file with
pytest tests; eval cases; release v0.12.0.

**Out:**
- B2 — the system layer connecting agents (topology, cross-agent justification, system-level
  record). Its own spec after B1.
- Shared infrastructure as code at the workspace root (e.g. one docker-compose for every
  agent).
- Shared application code between agents.

## 3. Decisions (settled during brainstorming)

| Decision | Choice | Rationale |
|---|---|---|
| Decomposition | B1 (independent agents) first, B2 (system layer) later | B2 needs agents that coexist; B1 is useful on its own. |
| Existing single-agent repos | Both layouts coexist; no migration required | A repo without the workspace marker behaves exactly as today. |
| Sharing between agents | Each agent self-contained (own src, tests, evals, docs, lockfile, deploy recipe); infrastructure may be shared at deploy time only | Keeps each agent's `build_start`, hook state and ship audit clean; no cross-agent dependency management. |
| Path strategy | One "agent root" every skill resolves first; existing relative paths become relative to it | Minimal text change across 12 skills; only git- and repo-wide steps are rewritten. Rejected: rewriting ~110 paths explicitly; one git repo per agent (submodules, split sessions, splits B2). |

## 4. Workspace marker and agent-root resolution

### 4.1 Marker

`agent-cycle.yaml` at the repository root, present only in a workspace:

```yaml
layout: workspace
agents: [ventas, soporte]      # each lives at agents/<name>/
```

The path is always `agents/<name>/`; `<name>` is the design's `agent_name` (kebab-case). No
configurable paths.

### 4.2 Resolution rule — `references/agent-root.md` (plugin root, new)

Every skill cites it with one line before touching any path. `AGENT_ROOT` resolves in order:

1. No `agent-cycle.yaml` at the repo root → single-agent repo: `AGENT_ROOT` = repo root
   (today's behavior).
2. The working directory is inside `agents/<name>/` → that agent.
3. The user's request names an agent in the list → that agent.
4. The list has exactly one agent → that agent.
5. Otherwise → ONE question listing the agents as lettered options.

All existing skill paths (`docs/agent/…`, `evals/…`, `src/…`, `tests/…`) are relative to
`AGENT_ROOT`. Git commands that take paths prefix them with `AGENT_ROOT`.

### 4.3 Creating an agent in a workspace

design creates `agents/<name>/docs/agent/design.md` and appends `<name>` to `agents:` in
`agent-cycle.yaml` — the only widening of design's write scope. A name already in the list or
an existing `agents/<name>/` → stop and ask.

### 4.4 Converting a single-agent repo

When the user asks for a second agent in a single-agent repo, design does not move anything.
It shows the conversion commands — `git mv` of the existing agent's files into
`agents/<existing-name>/`, create `agent-cycle.yaml` — for the human to run as one dedicated
commit, then proceeds with the new agent. Ship accepts that pure-rename commit (detected with
`--find-renames`) as sanctioned and records it.

## 5. One persistent hook for the workspace

Installed once in the repository root's `.claude/` (the first build in the repo) and kept.
Freezing is decided from each agent's state at call time, never from a static list:

| Path of agent X (relative to `AGENT_ROOT` of X) | Frozen when |
|---|---|
| `evals/**`, `docs/agent/design.md`, `docs/agent/spec.md` | `docs/agent/build.md` of X exists (X's build has started) |
| spec §6 Test column | editable only while X's `build.md` has `status: draft` |
| `docs/agent/build.md` | content editable while `status: draft`; frozen once approved; deleting or moving it is blocked once it exists (deletion would unfreeze X) |
| `docs/agent/skills.md`, `interop.md`, `ship-report.md`, `blueprint.html`, `agent-card.json`, economics | never (written by phases after build) |

Additional rules:
- The set of agents comes from the directories that exist under `agents/` (plus the repo
  root as an agent in a single-agent repo), not from the YAML list — removing a name from
  the list never unfreezes an agent.
- `agent-cycle.yaml` is append-only: an edit passes only when the new `agents:` list is a
  superset of the old one and nothing else changed.
- `.claude/hooks/` stays protected (the hook cannot be disabled by the builder).
- Single-agent repos follow the same rules with `AGENT_ROOT` = repo root. Behavior change vs
  v0.11: the frozen set narrows from all of `docs/agent/**` to `design.md`, `spec.md`,
  `evals/` (matching ship's diff since PR #1), and the hook persists after the build.
- Re-entry on an already-built agent stays the human's: rename the hook to
  `guard_artifacts.py.off` from their own terminal, change, rename back.
- Everything PR #1 added stays: `$CLAUDE_PROJECT_DIR` invocation, path resolution from the
  payload's `cwd`, folder-level shell-write blocking, UTF-8 stdin, fail-closed on unparseable
  calls.

## 6. Per-agent build and ship

### 6.1 Build of agent X

1. Baseline commit of X's artifacts only:
   `git add -- <AGENT_ROOT>/docs/agent/design.md <AGENT_ROOT>/docs/agent/spec.md <AGENT_ROOT>/evals/`
   (plus `agent-cycle.yaml` when X's entry is not yet committed); record `build_start` = HEAD.
2. Write X's `docs/agent/build.md` stub (`status: draft`, `build_start`) and commit it alone —
   this is what freezes X's artifacts.
3. Install the hook only if the workspace has none, or replace it when its version constant
   is older than the plugin's; otherwise verify it is active (a dummy edit to X's
   `evals/config.yaml` must be blocked).
4. Build writes only inside `AGENT_ROOT` (source, tests, lockfile, deploy recipe).
5. Resource names carry the agent prefix: queue/stream name, database schema,
   `service.name`, so agents sharing one Postgres/Redis/collector cannot collide. Added to
   `skills/build/references/adapter-bindings.md` as a universal rule.

### 6.2 Ship of agent X

- Anti-gaming diff limited to X:
  `git diff --word-diff --find-renames <build_start>..HEAD -- <AGENT_ROOT>/evals/ <AGENT_ROOT>/docs/agent/design.md <AGENT_ROOT>/docs/agent/spec.md`.
  Other agents' commits in the range do not appear.
- A commit in the range that touches X's paths AND another agent's paths is a finding routed
  to build. Commits touching only another agent are that agent's work and are ignored.
- A pure-rename conversion commit (§4.4) is accepted as sanctioned and recorded.
- The lockfile checked is the one under `AGENT_ROOT`.

### 6.3 Other skills

spec, evals, interop, skills, blueprint, economics and review: resolve `AGENT_ROOT` first and
write inside it. economics already names its file per agent. review assessing a workspace
reviews one agent at a time (resolved per §4.2).

## 7. Hook as code, with tests

- The hook moves out of the code block in `skills/build/references/forge-delegation.md` into
  a real file `skills/build/assets/guard_artifacts.py`; forge-delegation points to it and
  build copies it into the target repo. The file carries a `HOOK_VERSION` constant.
- `tests/test_guard_artifacts.py` (pytest) covers: single-agent and workspace layouts; frozen
  vs editable by `build.md` presence and draft/approved status; Test-column-only edits while
  draft; YAML append-only; `.claude/hooks/` protection; PR #1's cases (`cd`, folder deletes,
  UTF-8, fail-closed); the pure-rename commit is not the hook's concern (ship's).
- Console output of the hook and tests stays ASCII-only.

## 8. Evals (written before the skill changes — EDD)

| Skill | Case | Proves |
|---|---|---|
| design | DES-E07 | In a workspace, a new agent gets `agents/<name>/docs/agent/design.md` and is appended to the YAML; a clashing name stops and asks |
| design | DES-E08 | In a single-agent repo, asking for a second agent shows the conversion commands and moves nothing |
| spec | SPC-E05 | Several agents, no hint which → exactly one question |
| build | BLD-E06 | Building B with A already built: hook not reinstalled but verified; baseline commit contains only B's artifacts; resource names carry B's prefix |
| ship | SHP-E05 | Ship of B: diff limited to B; a mixed-agent commit is a finding; the conversion rename commit is accepted |

## 9. Release

- **v0.12.0.** The CHANGELOG/README versioning rule changes from "minor = new pipeline
  skill" to "minor = new skill or new pipeline capability".
- Upgrade notes: the hook is persistent and narrower in single-agent repos (only
  `design.md`, `spec.md`, `evals/` frozen); repos with an older hook get it replaced on their
  next build (version constant).
- Pending graduation: a real workspace with two agents both taken through build.

## 10. Risks

| Risk | Mitigation |
|---|---|
| A skill forgets to resolve `AGENT_ROOT` and writes to the repo root in a workspace | One shared rule cited at the top of every skill; DES-E07/BLD-E06/SHP-E05 exercise the workspace path; the hook freezes per agent so a misplaced write to another agent's frozen files is blocked. |
| The builder of X edits another agent's source (not frozen by the hook) | Ship of X flags any commit touching X and another agent together. |
| State-driven freezing has an edge where a frozen file becomes editable (e.g. `build.md` deleted) | The hook protects `build.md` from deletion once it exists (a delete is a write); tests cover it. |
| Persistent hook surprises single-agent users | Upgrade note; the frozen set is narrower than before, not wider. |
