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
commit, then stops; after that commit design runs again for the new agent. Ship accepts that pure-rename commit (detected with
`--find-renames`) as sanctioned and records it. The commands start by upgrading an existing
hook to the plugin's version (and its registration to the pinned `python -I -S` form), committed
on its own, because an older hook does not protect `agents/*/`. They end by
replacing the `.` line of the tracked `.claude/hooks/built-agents.txt` with
`agents/<existing-name>/` and committing it.

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
  The file is **tracked**. Build seeds it with the agent's prefix and commits it in the same
  commit as the hook (§6.1), and commits it again whenever the hook appends a line. A fresh
  clone therefore stays frozen, and `git clean` cannot remove the file.
- `agent-cycle.yaml` is append-only: an edit passes only when the new `agents:` list is a
  superset of the old one and nothing else changed. A marker that exists but cannot be read or
  parsed blocks every change to it.
- `.claude/hooks/` stays protected (the hook and its ratchet file; the builder cannot
  disable either). A file that is a hard link to a protected file (same device and inode,
  `st_nlink > 1`) is protected too, for file tools and shell targets alike. Creating such a
  link (`ln`, `mklink`, `fsutil hardlink`) is judged on the linked file as well.
- **Settings.** The registration is pinned to
  `python -I -S "$CLAUDE_PROJECT_DIR/.claude/hooks/guard_artifacts.py"`. `-I` ignores
  `PYTHON*` environment variables and the user site; `-S` skips `site`.
  - A file-tool write to `.claude/settings.json` or `.claude/settings.local.json` (and to the
    user's `~/.claude/settings.json`) is blocked when the result is not valid JSON, changes the
    guard's `PreToolUse` entry in any way, changes the `env` key (in the user's file, only its
    `PATH` and `PYTHON*` entries, which steer the hook's interpreter), or sets `disableAllHooks`.
    An entry with the flags stripped counts as dropping the guard.
  - Installing the pinned entry where none exists is allowed.
  - Existing installs registered without `-I -S` are updated by the human from their own
    terminal.
  - Any shell write whose target names `.claude/settings` is blocked.
- **Git verbs are the human's while any agent is built.** These verbs rewrite the working tree
  from another commit, so the hook blocks them outright and the human runs them from their
  own terminal: `git apply`, `git am`, `git revert`, `git cherry-pick`, `git merge`,
  `git pull`, `git rebase`, `git reset --hard`, `git stash pop`/`apply`/`branch`, and
  `git checkout`/`git restore` from a tree-ish (or `--source`/`-s`) when the pathspec is `.`,
  a `:` magic pathspec, or reaches a holder folder or a protected path.
  - Path-less destructive verbs act on the current directory, so the holder rule blocks them
    at the root or in an agent folder: `git clean` (any flags), `git stash -u`/`-a`/
    `--include-untracked`/`--all`, and `git reset --hard`.
  - Still allowed: `git restore src/app.py`, `git checkout -- src/x`, `git checkout <branch>`,
    `git checkout -b <branch>` and `git switch`.
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
- Shell commands are read heuristically. A command line is split into segments (on `;`,
  `&&`, `||`, `&` and newlines), and each segment into commands (on pipes, `( )` and
  backticks). Adjacent quote pieces join into one word: `e""vals`, `r''m`, `$'evals'`.
  - **The verb comes from parsed words.** The hook takes the basename, lower-cased, with
    `.exe` dropped, after skipping `VAR=value` assignments and wrappers such as `sudo`, `env`,
    `timeout` and `xargs`. So `/bin/rm`, `rm.exe`, `"rm"`, `\rm` and
    `C:/Windows/System32/robocopy.exe` are all recognised.
  - **Only write targets are judged.** Examples:
    - `cp`/`Copy-Item`/`xcopy`/`robocopy`/`rsync`: the destination, plus the source when it
      is moved away;
    - `Set-Content`/`Add-Content`/`Out-File`: `-Path`/`-FilePath` or the first positional
      argument;
    - `dd`: the `of=` value;
    - redirects: their target;
    - `rm`, `mv`, `touch`, `tee`, `ln`, in-place `sed`/`perl`/`awk`, and similar: every
      argument;
    - `find`: its starting points, when `-delete` or `-exec <write verb>` is present.

    Reading a frozen file into a pipe or a copy passes (`cp evals/x /tmp/`,
    `Get-Content evals/config.yaml | Out-File out.txt`). A write whose targets arrive through a
    pipe or a subexpression (`... | xargs rm`, `Get-ChildItem evals | Remove-Item`) is judged
    on the rest of the segment, plus the current directory when it removes.
  - Redirects that only move a stream (`2>&1`, `>/dev/null`, `2>NUL`) are not writes.
  - Folders that hold frozen files (the root, `agents/`, an agent folder, its `docs`,
    `docs/agent`, `evals`) count only for destructive verbs (`rm`, `mv`, `Remove-Item`,
    `robocopy /MIR`, `git clean/rm/mv`, `find -delete`, ...).
  - The protected-name substring check runs on unquoted write targets only.
  - Some text is read as code rather than data: here-documents that feed a shell or
    interpreter, `bash -c` and `pwsh -Command` strings, `eval` and `Invoke-Expression`.
  - **Globs are matched by depth:**
    - a protected file (marker, settings, `design.md`, `spec.md`, `build.md`) only at its own
      depth;
    - a protected folder (`.claude/hooks`, and a built agent's `evals`, `docs/agent`) at its
      depth or deeper;
    - a holder folder (destructive verbs only) at its depth or above.

    So `rm -rf */__pycache__` and `rm docs/*.html` pass, while `rm -rf ev*`,
    `rm docs/agent/*.md` and `rm agent-cycle.*` are blocked.
  - `git -C <dir>` resolves from `<dir>`.

## 6. Per-agent build and ship

### 6.1 Build of agent X

1. Baseline commit of X's artifacts only:
   `git add -- <AGENT_ROOT>/docs/agent/design.md <AGENT_ROOT>/docs/agent/spec.md <AGENT_ROOT>/evals/`
   (plus `agent-cycle.yaml` when X's entry is not yet committed); record `build_start` = HEAD.
2. Write X's `docs/agent/build.md` stub (`status: draft`, `build_start`) and commit it alone —
   this is what freezes X's artifacts.
3. Hook: install it when absent. Installing means three things, committed together in ONE
   commit before the hook is active:
   - copy the script;
   - seed `.claude/hooks/built-agents.txt` with X's prefix (`.` for a one-agent repo,
     `agents/<name>/` in a workspace);
   - merge the pinned registration into `.claude/settings.json`.

   If the installed `HOOK_VERSION` is lower than the plugin's, STOP and ask the human to
   upgrade it from their own terminal (rename to `.off`, copy the plugin's file, rename back).
   Build never writes `.claude/hooks/` once the hook exists. When the hook is already
   installed, it records X itself the first time it sees X's `build.md`, and build commits
   the updated ratchet file (`git add .claude/hooks/built-agents.txt`). Otherwise verify the
   hook is active: a dummy edit to X's `evals/config.yaml` must be blocked.
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

  The second re-review adds:
  - **Path-less destructive git:** a stub revert followed by `git clean` is blocked at the
    clean step; `git clean` (any flags), `git stash -u`/`-a`/`--include-untracked`/`--all` and
    `git reset --hard` are blocked at the root and in an agent folder. `git clean -fd src`,
    `git stash` and `git reset HEAD~1` pass.
  - **Human-only git while built:**
    - each of apply, am, revert, cherry-pick, merge, pull, rebase, reset --hard, stash
      pop/apply, and checkout/restore from a tree-ish over `.`, `:/`, a holder or a frozen
      path;
    - the scoped forms that pass (`git restore src/app.py`, `git checkout -- src/x.py`,
      `git checkout main`, `git checkout -b`, `git switch`);
    - the same verbs before any build.
  - **Pinned registration:** `main()` under `python -I -S`; the hook's `GUARD_COMMAND`
    matches; flags stripped, an unpinned install and a human-only upgrade are blocked; `env`
    added or changed is blocked; an unchanged `env` plus another key passes.
  - **Verb from parsed words:**
    - path, case and quote forms: `/bin/rm`, `rm.exe`, `"rm"`, `r''m`, `\rm`, full
      `robocopy.exe`;
    - assignments and wrappers: `VAR=1`, `sudo -u`, `env`, `timeout`;
    - code read from strings and pipes: `$(...)`, `eval`, `Invoke-Expression`,
      `Get-ChildItem | Remove-Item`, `Remove-Item (Join-Path ...)`, `ls | xargs rm`,
      `find -exec rm`.
  - **Glob depth:** `*/__pycache__`, `**/__pycache__`, `docs/_build/*`, `docs/*.html`,
    `agents/*/__pycache__`, `agents/*/node_modules` and `cd agents/x && rm -f *.log` pass;
    `ev*`, `docs/agent/*.md`, `agent-cycle.*` and `d*` are blocked.
  - **Hard links:** a write through a hard link to a frozen file is blocked (file tool and
    redirect); a link between free files passes; `fsutil hardlink create` and `ln` onto a
    frozen file are blocked.
  - **Write targets only:** reading a frozen file into a copy, pipe, `dd if=` or `-Value`
    passes; destinations, `-Path`, `-FilePath`, `cp -t`, `dd of=`, `robocopy /MOV` sources
    and `rsync` destinations are judged.
  - **Other:** `$'...'` quoting; the test file is `mypy --strict` clean.
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
  back). A pre-v0.12 hook does not protect `agents/*/`. A repo whose `.claude/settings.json`
  registers the hook without `-I -S` keeps working, but the human updates that command to the
  pinned form (the hook blocks the builder from changing its own registration), then commits
  `.claude/hooks/built-agents.txt`.
- Pending graduation: a real workspace with two agents both taken through build.

## 10. Risks

**Two layers.** The hook is the first layer. It blocks the obvious and the moderately clever
forms at the moment of the tool call, and it is a heuristic, not a sandbox. The second layer
is ship:
- its word-diff from `build_start` on the agent's `evals/`, `design.md` and `spec.md` sees
  every change to a frozen artifact, whatever wrote it;
- its rule 4 re-runs the suite from the committed tree, so a result produced by a modified
  working tree does not survive.

After the second security re-review the bypass hunt on the hook stops: a residual shell form
is accepted when ship's two checks catch its effect.

| Risk | Mitigation |
|---|---|
| A skill forgets to resolve `AGENT_ROOT` and writes to the repo root in a workspace | One shared rule cited at the top of every skill; DES-E07/BLD-E06/SHP-E05 exercise the workspace path; the hook freezes per agent so a misplaced write to another agent's frozen files is blocked. |
| The builder of X edits another agent's source (not frozen by the hook) | Ship of X flags any commit touching X and another agent together. |
| State-driven freezing has an edge where a frozen file becomes editable (e.g. `build.md` deleted) | The hook blocks visible deletes and moves of `build.md` once it exists. The ratchet (`.claude/hooks/built-agents.txt`) keeps a recorded agent frozen even when `build.md` disappears through a form the hook cannot see. Tests cover both. |
| Shell forms the hook cannot see: a script that writes (`python fix.py`, `python -c`, PowerShell .NET calls not on its list), paths assembled in variables, backslash escapes inside names, brace expansion, encoded commands, tools that rewrite files in place (`ruff format .`, `prettier --write .` over frozen files) | Residual, accepted. Ship's word-diff from `build_start` on the agent's `evals/`, `design.md` and `spec.md` catches any change to frozen artifacts, whatever wrote it. Ship's rule 4 re-runs the suite from the committed tree. For `build.md`, the tracked ratchet means a hidden deletion never unfreezes the agent, not even in a fresh clone. |
| Heuristic false blocks: a destructive verb on a folder that holds frozen files (`find . -name x -delete`, `find . -exec rm`, `... \| xargs rm` run from the root, path-less `git clean` at the root), a `cp`/`dd if=` whose read side is fine but whose target is protected | The block message names the path. Use `find ... -delete` or `find ... -exec rm {} +` instead of `\| xargs rm` (a destructive command fed by xargs is judged against the current directory chain), and give `git clean` a path (`git clean -fd src`). Reading a frozen file is not a write (`cp evals/x /tmp/` passes). Everyday build commands are regression-tested as allowed. |
| Git verbs that rewrite the tree (merge, pull, rebase, revert, cherry-pick, apply, am, reset --hard, stash pop/apply, checkout/restore from another commit over protected paths) | Blocked while any agent is built; the human runs them from their own terminal. Branch switching (`git checkout <branch>`, `git switch`) stays allowed: ship's diff covers a switch that carries other artifact versions. |
| The builder rewrites its own registration (strip `-I -S`, add an `env` key, `disableAllHooks`) | Settings protection pins the guard entry and the `env` key; any change is the human's. |
| Persistent hook surprises single-agent users | Upgrade note; the frozen set is narrower than before, not wider. |
