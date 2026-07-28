# agent-cycle

Claude Code plugin that runs the complete construction cycle of an AI agent —
from idea to shipped, evaluated, observable production agent — as a gated,
disk-backed pipeline of skills.

## Pipeline

| Phase | Skill | Artifact |
|---|---|---|
| 1 Design | `agent-cycle:design` | `docs/agent/design.md` |
| 2 Spec | `agent-cycle:spec` | `docs/agent/spec.md` |
| 3 Evals | `agent-cycle:evals` | `evals/` |
| 4 Build | `agent-cycle:build` | `src/` |
| 5 Skills | `agent-cycle:skills` (conditional) | target agent skills |
| 6 Interop | `agent-cycle:interop` (conditional) | Agent Card + A2A |
| 7 Ship | `agent-cycle:ship` | DoD report |
| — | `agent-cycle:economics` (transversal) | `docs/agent/<name>-economics.md` |
| — | `agent-cycle:blueprint` (transversal) | `docs/agent/blueprint.html` |

Phase artifacts land in the TARGET AGENT'S repo — this plugin repo never
contains agent artifacts.

Every phase fails hard if its upstream artifact is missing, `draft`, or stale.
Human gate between every phase. See `docs/superpowers/specs/` for the full design.

**Status:** v0.3.0 — `design` + `spec` + `evals` skills. Built skill-by-skill,
each dogfooded on a real agent before the next begins.

## Install

From an interactive Claude Code session:

```
/plugin marketplace add alanvaa06/agent-cycle
/plugin install agent-cycle@agent-cycle
```

Update later with `/plugin marketplace update agent-cycle` and reinstall to pick
up new versions.

## Versioning

Semver, driven by `.claude-plugin/plugin.json`:

- **minor** — a new pipeline skill lands (e.g. 0.2.0 = `spec` skill).
- **patch** — fixes to existing skills or docs.
- Each skill also graduates via its own eval gate (see `skills/*/evals/`);
  graduation is tagged (`design-v0.1`) independently of plugin releases.

See `CHANGELOG.md` for release history.
