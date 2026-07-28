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

**Status:** v0.1 — `design` skill only. Built skill-by-skill, each dogfooded on
a real agent before the next begins.
