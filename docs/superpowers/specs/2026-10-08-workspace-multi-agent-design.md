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
`--find-renames`) as sanctioned and records it. The commands start by upgrading an existing
hook to the plugin's version, because an older hook does not protect `agents/*/`. They end by
removing the `.` line from `.claude/hooks/built-agents.txt`, since the moved agent is recorded
again under `agents/<existing-name>/`.

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
- The set of agents always comes from directories: the repo root plus every
  `agents/<dir>/`, matched longest prefix first (a path belongs to the deepest agent that
  holds it). `agent-cycle.yaml` plays no part in it, so deleting, renaming or creating the
  marker never changes what is frozen. The root freezes only when it has its own
  `docs/agent/build.md`, so root-level folders in a workspace are not an agent. The marker
  matters only for the append-only rule below.
- **Ratchet.** The hook records every agent whose `build.md` it has seen in
  `.claude/hooks/built-agents.txt`, one agent prefix per line (`.` for the root,
  `agents/<name>/` otherwise). It writes the file itself (a process write, not a tool call) on
  every run, before deciding. If an agent is recorded but its `build.md` is missing, the hook
  treats it as frozen whatever its status: `evals/`, `design.md`, `spec.md` and the `build.md`
  path itself, with no Test-column exception. So deleting `build.md` by glob, rename,
  `git reset`/`revert` or `python -c` never unfreezes the agent. A failed write never fails
  open: the call is still decided from the file's content plus what the hook sees on disk.
- `agent-cycle.yaml` is append-only: an edit passes only when the new `agents:` list is a
  superset of the old one and nothing else changed. A marker that exists but cannot be read or
  parsed blocks every change to it.
- `.claude/hooks/` stays protected (the hook and its ratchet file; the builder cannot
  disable either).
- **Settings.** A file-tool write to `.claude/settings.json` or `.claude/settings.local.json`
  (and to the user's `~/.claude/settings.json`) is blocked when the resulting text is not
  valid JSON, drops or alters the hook's `PreToolUse` entry, or sets `disableAllHooks`. Any
  shell write naming `.claude/settings` is blocked.
- Single-agent repos follow the same rules with `AGENT_ROOT` = repo root. Behavior change vs
  v0.11: the frozen set narrows from all of `docs/agent/**` to `design.md`, `spec.md`,
  `evals/` (matching ship's diff since PR #1), and the hook persists after the build.
- Re-entry on an already-built agent stays the human's, from their own terminal (the hook
  only governs Claude's tool calls): rename the hook to `guard_artifacts.py.off`, make the
  change, remove the agent's line from `.claude/hooks/built-agents.txt` (needed when its
  `build.md` is deleted or moved; otherwise the hook records it again on the next call), then
  rename the hook back.
- Upgrading the hook is also the human's job. Build never writes `.claude/hooks/` because the
  hook protects that folder (§6.1 step 3).
- Everything PR #1 added stays: `$CLAUDE_PROJECT_DIR` invocation, path resolution from the
  payload's `cwd`, folder-level shell-write blocking, UTF-8 stdin, fail-closed on unparseable
  calls. File-tool paths are canonicalised before they are judged: no `$VAR`/`~` expansion (the
  tool takes them literally), a leading `\\?\` stripped, and `realpath` resolves junctions,
  8.3 names, case and trailing dots or spaces. Any `:` after the drive letter (an NTFS
  alternate stream such as `::$DATA`) is blocked as an unsafe path.
- Shell commands are read heuristically, one segment at a time (split on `;`, `&&`, `||`,
  `&` and newlines; a pipeline stays one segment):
  - Redirects that only move a stream (`2>&1`, `>/dev/null`, `2>NUL`) are not writes. When a
    redirect is a segment's only write, the hook judges only its target paths.
  - Folders that hold frozen files (the root, `agents/`, an agent folder, its `docs`,
    `docs/agent`, `evals`) count only for destructive verbs (`rm`, `mv`, `Remove-Item`,
    `robocopy`, `git clean/rm/mv`, `find -delete`, ...).
  - The protected-name substring check skips quoted text such as commit messages.
  - Some text is read as code rather than data: here-documents that feed a shell or
    interpreter, `bash -c` and `pwsh -Command` strings.
  - Globs are matched against protected paths, `git -C <dir>` resolves from `<dir>`, and
    adjacent quote pieces are joined (`e""vals`).

## 6. Per-agent build and ship

### 6.1 Build of agent X

1. Baseline commit of X's artifacts only:
   `git add -- <AGENT_ROOT>/docs/agent/design.md <AGENT_ROOT>/docs/agent/spec.md <AGENT_ROOT>/evals/`
   (plus `agent-cycle.yaml` when X's entry is not yet committed); record `build_start` = HEAD.
2. Write X's `docs/agent/build.md` stub (`status: draft`, `build_start`) and commit it alone —
   this is what freezes X's artifacts.
3. Hook: install it when absent. If the installed `HOOK_VERSION` is lower than the plugin's,
   STOP and ask the human to upgrade it from their own terminal (rename to `.off`, copy the
   plugin's file, rename back). Build never writes `.claude/hooks/`. Otherwise verify it is
   active: a dummy edit to X's `evals/config.yaml` must be blocked.
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
- `tests/test_guard_artifacts.py` (pytest) covers:
  - single-agent and workspace layouts;
  - frozen vs editable by `build.md` presence and draft/approved status;
  - Test-column-only edits while draft;
  - YAML append-only;
  - `.claude/hooks/` protection;
  - PR #1's cases (`cd`, folder deletes, UTF-8, fail-closed);
  - the pure-rename commit is not the hook's concern (ship's).

  The hardening pass adds:
  - **Layout from directories:** deleting or creating the marker changes nothing; the
    longest prefix wins over a built root; `rm *.yaml`, `rm agent-cycle.*` and `Rename-Item`
    on the marker are blocked.
  - **Ratchet:**
    - `build.md` deleted after a prior call: the agent stays frozen;
    - recorded agent with `build.md` missing: Test-column edit blocked;
    - workspace `build.md` deleted by glob;
    - renamed agent folder;
    - file content, protection, write failure, and an unreadable file through `main()`.
  - **Path canonicalisation:** `::$DATA`, `\\?\`, `$VAR/..`, trailing dots and spaces,
    a junction, 8.3 names.
  - **Shell detector gaps:** new write verbs, `sed`/`perl`/`awk` in-place, `git -C` and
    global options, interpreter here-docs, empty here-docs, line continuations,
    `bash -c`/`pwsh -Command`/`cmd /c`, `find -delete`, globs, quote splitting, `cd /d`,
    `Set-Location -Path`, .NET file calls.
  - **No false blocks:** the build commands `uv pip install -e . 2>&1 | tail`, `ruff check .
    2>&1`, `pytest . 2>&1`, `cat evals/... 2>/dev/null`, `ls evals 2>&1`, `... > results.txt`,
    `git diff -- evals/ > /tmp/d.txt`, commit messages naming frozen paths, `... | tee log`,
    `cp README.md docs/`, and the workspace `uv run pytest agents/x 2>&1` and
    `cd agents/x && ...` all pass.
  - **Settings:** dropping or altering the guard entry, `disableAllHooks` (project, local and
    user files), invalid JSON, shell writes; installing is allowed.
  - **Reading state:** missing vs unreadable files, BOM and quoted `status`, on-disk case,
    non-string inputs fail closed, one disk snapshot per call.
  - **`main()`:** UTF-8 bytes on stdin, ASCII stderr, payload `cwd` different from
    `CLAUDE_PROJECT_DIR`.
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
  `design.md`, `spec.md`, `evals/` frozen). An older hook is never replaced by build: build
  stops and asks the human to upgrade it (rename to `.off`, copy the plugin's file, rename
  back). A pre-v0.12 hook does not protect `agents/*/`.
- Pending graduation: a real workspace with two agents both taken through build.

## 10. Risks

| Risk | Mitigation |
|---|---|
| A skill forgets to resolve `AGENT_ROOT` and writes to the repo root in a workspace | One shared rule cited at the top of every skill; DES-E07/BLD-E06/SHP-E05 exercise the workspace path; the hook freezes per agent so a misplaced write to another agent's frozen files is blocked. |
| The builder of X edits another agent's source (not frozen by the hook) | Ship of X flags any commit touching X and another agent together. |
| State-driven freezing has an edge where a frozen file becomes editable (e.g. `build.md` deleted) | The hook blocks visible deletes and moves of `build.md` once it exists. The ratchet (`.claude/hooks/built-agents.txt`) keeps a recorded agent frozen even when `build.md` disappears through a form the hook cannot see. Tests cover both. |
| Shell forms the hook cannot see: a script that writes (`python fix.py`, `python -c`, PowerShell .NET calls not on its list), paths assembled in variables, backslash escapes inside names, brace expansion, encoded commands | Residual. Ship's word-diff from `build_start` on the agent's `evals/`, `design.md` and `spec.md` catches any change to frozen artifacts, whatever wrote it. For `build.md`, the ratchet means a hidden deletion never unfreezes the agent. |
| Heuristic false blocks: a destructive verb on a folder that holds frozen files (`find . -name x -delete`, `find . -exec rm`), or reading a frozen file through a write verb (`cp evals/x /tmp/`) | The block message names the path; the builder narrows the command (`find src ...`, `cat evals/x > /tmp/y`). Everyday build commands are regression-tested as allowed. |
| Persistent hook surprises single-agent users | Upgrade note; the frozen set is narrower than before, not wider. |
