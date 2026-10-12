# Forge delegation — agent-cycle:build

/build does not reimplement loop engineering. Non-trivial builds delegate
execution to forge-master through its PUBLIC contract only: a PRD with ACs +
a test-runner command whose exit code defines green.

## When to delegate

Delegate when ANY holds: >3 tools, any non-safe tier, a queue/channel adapter,
or an eval suite with >15 cases. Direct TDD (no forge) only when ALL of:
few tools, all safe-tier, no channel infra, small suite — and record the
one-line justification in build.md.

## Mechanical PRD derivation

forge-master's real contract (verified against its installed skills): PRDs live
at `docs/forge/prd/NNN-name.md` (NNN = next number in the directory) with the
mandatory shape `## Goal / ## Non-Goals / ## User Stories (US-n, "As a
<role>...") / ## Constraints / ## Definition of Done`, ACs numbered `AC-n.m`
nested under their US-n, and stable IDs never renumbered. Derive mechanically:

1. `## Goal`: the design's Performance metric, one paragraph.
2. `## Non-Goals`: the design's NO-goals, copied.
3. `## User Stories`: one US-n per capability from the spec (C1..Cn map 1:1).
   Under each, one `AC-n.m` per BHV scenario of that capability. The AC text
   is the scenario's Given/When/Then verbatim, with the BHV id preserved as a
   leading annotation inside the text: `AC-1.2: [BHV-002] Given the calendar
   API returns 503...`. BHV ids ride inside the AC text — forge's AC-n.m
   numbering stays canonical for its machinery; the BHV annotation keeps the
   pipeline's traceability chain intact (BHV → eval → AC → phase → test).
4. `## Constraints`: runtime + target (spec/design), loop caps, the frozen-
   artifact rule (`<AGENT_ROOT>/evals/`, `<AGENT_ROOT>/docs/agent/design.md`
   and `spec.md` are read-only for the forge run: the hook freezes them).
5. `## Definition of Done`: the eval-runner command stated exactly and run from
   AGENT_ROOT (e.g. `python -m evals.runner`; in a workspace
   `cd agents/<name> && python -m evals.runner`), "exit code 0 with every case
   at its threshold", plus the adapter smoke test.

Then follow forge-master's OWN two-gate process: `forge-master:prd-import` on
the derived PRD (Human Gate 1 — the human approves the PRD) →
`forge-master:plan-design` (Human Gate 2 — the human approves the plan) →
`forge-master:forge-run`. Never collapse or skip either gate. Forge's "green =
test runner exit code" composes with the runner's "0 = every case at
threshold" — no opinion anywhere in the chain.

Forge under the persistent hook: once any agent is built, Claude cannot run
`git merge`, `pull`, `rebase`, `stash push -u` and the other tree-rewriting
verbs (see "The anti-gaming hook" below). The forge Run Config therefore sets
`on_complete: pr` or `keep` (never `merge`) and `max_parallel: 1`; merging the
result and forge's resume stash recovery are the human's, from their own
terminal. Forge's default `isolation: worktree` runs outside the project
directory, where the hook does not apply; for delegated builds /ship's diff
audit is the protection there.

## The anti-gaming hook

The hook is the agent-cycle plugin's `skills/build/assets/guard_artifacts.py`
(tested in the plugin's `tests/test_guard_artifacts.py`). Installing it writes
three things in the TARGET repo, in this order, and commits them together in
ONE commit (the registration goes last: a registered hook whose script is
missing blocks every tool call):
1. the script, at `.claude/hooks/guard_artifacts.py`;
2. the ratchet `.claude/hooks/built-agents.txt`, seeded with this agent's prefix
   (`.` in a one-agent repo, `agents/<name>/` in a workspace);
3. the registration, merged into `.claude/settings.json` with exactly this
   command:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash|PowerShell",
        "hooks": [
          {
            "type": "command",
            "command": "python -I -S \"$CLAUDE_PROJECT_DIR/.claude/hooks/guard_artifacts.py\""
          }
        ]
      }
    ]
  }
}
```

The script path goes through `$CLAUDE_PROJECT_DIR` because hooks run from the
session's current directory, which moves with `cd`. `-I` ignores `PYTHON*`
environment variables and the user site; `-S` skips `site`.

The hook pins this exact entry. After install, any change to it or to the
`env` key of `.claude/settings*.json` is blocked; an entry with the flags
stripped counts as dropping the hook. A repo registered without `-I -S` is
updated by the human from their own terminal.

Installed once per repository and kept (it is not removed after a build).
Install when absent. If the installed file's `HOOK_VERSION` is lower than the
plugin's (a hook with no `HOOK_VERSION`, as every pre-v0.12 hook, counts as
lower), STOP and ask the human to upgrade it from their own terminal: rename
it to `guard_artifacts.py.off`, copy the plugin's file, rename it back, and
commit the upgrade with a subject starting `agent-cycle: hook upgrade` (ship
sanctions exactly that subject).
Build never writes `.claude/hooks/` once the hook exists, because the hook
protects that folder. Otherwise only verify it is active.

`built-agents.txt` is tracked. When the hook already exists, it records a newly
built agent itself the first time it sees that agent's build.md. Commit the
updated file with the next commit (`git add .claude/hooks/built-agents.txt`;
`git add` is not a write). A fresh clone therefore stays frozen, and
`git clean` cannot remove the file.

What it freezes, per agent (layouts per the plugin's `references/agent-root.md`):

| Path of an agent | Frozen when |
|---|---|
| `evals/**`, `docs/agent/design.md`, `docs/agent/spec.md` | the agent's `docs/agent/build.md` exists |
| spec §6 Test column | editable with file tools only while build.md says `status: draft` |
| `docs/agent/build.md` | editable with file tools while `draft`; frozen once approved; shell writes never touch it |
| later-phase files (skills.md, interop.md, ship-report.md, blueprint.html, agent-card.json, economics) | never |

Always:
- **Agents come from directories.** Agents are the repo root plus every
  `agents/<dir>/`, longest prefix first. `agent-cycle.yaml` never decides
  what is frozen. The root freezes only with its own `docs/agent/build.md`.
- **Marker.** `agent-cycle.yaml` is append-only.
- **Ratchet.** The hook records every agent whose build.md it has seen in
  `.claude/hooks/built-agents.txt` (`.` for the root). A recorded agent whose
  build.md is gone stays frozen: evals, design, spec, the build.md path, and no
  Test column. Deleting build.md by any route never unfreezes an agent, and
  the file is tracked.
- **Hook folder.** `.claude/hooks/` (hook and ratchet) is protected, and so is
  any file that is a hard link to a protected file.
- **Settings.** `.claude/settings.json`, `settings.local.json` and the user's
  `~/.claude/settings.json` must stay valid JSON. In the project files the
  pinned PreToolUse entry and the `env` key must not change; in the user's
  file the `env` rule covers only its `PATH` and `PYTHON*` entries (they
  steer the hook's interpreter), not the whole key. `disableAllHooks` must
  never be set. Any shell write whose target names `.claude/settings` is
  blocked.
- **Shell writes.** The hook judges only write targets, parsed per command:
  - the verb is the word's basename, so `/bin/rm`, `rm.exe` and `"rm"` count;
  - the target is the destination of `cp`, `install`, `scp`, `Copy-Item` or
    `robocopy`, the `-Path` of `Set-Content`, a redirect's target, or every
    argument of `rm`, `mv`, `touch` and `tee`;
  - a copy into a folder also lands `<folder>/<name of each source>`
    (`cp x docs/agent/` writes `docs/agent/x`). A recursive copy, a glob, or
    a copy of a folder's contents (`cp -rT`, `rsync src/ dest/`, `xcopy`,
    `robocopy`) is judged like a destructive verb on the destination;
  - an extraction (`tar x`, `unzip`, `7z x`, `jar x`, `cpio -i`,
    `Expand-Archive`) is judged like a destructive verb on the folder it
    fills: its `-C`/`-d`/`-o`/`-DestinationPath`, else the current directory.
    Creating an archive is not a write on its sources.

  Reading a frozen file is not a write. Blocked:
  - a write whose target is a frozen path;
  - a destructive verb (`rm`, `mv`, `Remove-Item`, `robocopy /MIR`,
    `git clean/rm/mv`, `find -delete`, ...) whose target is a folder holding
    frozen files: the repo root, `agents/`, an agent folder, its `docs`,
    `docs/agent` or `evals`;
  - a glob that reaches one by depth: a protected file at its own depth, a
    protected folder at its depth or deeper, a holder at its depth or above.
- **Text a shell runs.** `echo '...' | sh`, `sh <<< '...'`,
  `source <(echo ...)` and `eval "$(echo ...)"` run what the echo/printf
  prints, so its literal words are read as a command. While any agent is
  built, an echo/printf whose text cannot be read is blocked: a `$`, a
  backtick, a `printf` format, a backslash escape anywhere in the command, or
  another command between it and the shell (`echo ... | rev | sh`).
- **Git (the human runs these while any agent is built).** Blocked outright:
  - `git apply`, `am`, `revert`, `cherry-pick`, `merge`, `pull`, `rebase`,
    `bisect`, `sparse-checkout`, `checkout-index`, `filter-branch`,
    `filter-repo`, `replace`;
  - `git reset --hard`/`--keep`/`--merge`, `git stash pop`/`apply`/`branch`;
  - `git checkout`/`restore` from another commit (`<tree-ish> --`,
    `--source`/`-s`) over `.`, a `:` magic pathspec, a holder or a protected
    path; `checkout`/`restore` with `-p` or `--pathspec-from-file`;
  - `git update-ref --stdin`, `git update-index --index-info`,
    `git fetch -u`/`--update-head-ok`;
  - a `:` magic pathspec in `git clean` or `git stash push`.

  Compared with HEAD instead of listed (the hook runs `git diff`):
  - **A move to another revision** passes when that revision's hook folder,
    settings, evals and design.md equal HEAD's: `git checkout <rev>`,
    `checkout -b x <start>`, `switch`, `reset --soft`/`--mixed <rev>`,
    `read-tree`, `symbolic-ref HEAD`, and `update-ref` or `branch -f` on the
    checked-out branch. While the build is a draft, build.md may differ and
    spec.md may differ in its Test column; once approved both must be equal.
    Any other difference is the human's. That includes switching to a branch
    from before the hook was installed.
  - **A rewrite of the working tree from HEAD or the index** passes when the
    frozen files on disk and in the index are HEAD's: `git checkout -f`,
    `switch -f`/`--discard-changes`, `stash`, `read-tree -u`, and `checkout`
    or `restore` of `.`, a holder or a protected path. Whatever moved HEAD,
    this is the step where a frozen file would change.
  - A comparison that cannot run (git missing, a 3-second timeout) blocks.
    Outside a git repository nothing is compared. A command aimed at another
    repository (`git -C ../other`, `cd ../other && git ...`) is judged only
    by where that repository sits.

  Config and environment:
  - `-c`, `--config-env` and `git config` writes are blocked for entries that
    run a command or redirect git: `alias.*`, `core.hooksPath`,
    `core.worktree`, `core.fsmonitor`, `core.sshCommand`, `core.askpass`,
    `core.gitProxy`, `filter.*`, `diff.external`, `diff.*.textconv`,
    `merge.*.driver`, `include.path`, `includeIf.*`, `credential.helper`,
    `gpg.program`, `difftool.*.cmd`, `mergetool.*.cmd`, `init.templateDir`.
    Reading one (`git config --get`, `git config <key>`) is free;
  - an editor or pager given with `-c` or a variable (`core.editor`,
    `core.pager`, `pager.*`, `sequence.editor`, `GIT_EDITOR`,
    `GIT_SEQUENCE_EDITOR`, `GIT_PAGER`) is free when its value is a known
    viewer or editor with dash options (`cat`, `less -FRX`, `true`, `vim`,
    `code --wait`), blocked otherwise. `git config` never writes one;
  - `--git-dir`, `--work-tree`, `--exec-path=`, and the variables that do the
    same in any unquoted `NAME=value` word: `GIT_DIR`, `GIT_WORK_TREE`,
    `GIT_INDEX_FILE`, `GIT_COMMON_DIR`, `GIT_OBJECT_DIRECTORY`,
    `GIT_CONFIG_*`, `GIT_EXTERNAL_DIFF`, `GIT_SSH`, `GIT_SSH_COMMAND`,
    `GIT_ASKPASS`, `GIT_EXEC_PATH`, `GIT_TEMPLATE_DIR`;
  - `git config -f <file>` is a write on that file.

  `.git` internals: writes to `.git/hooks/`, `.git/config`, `.git/info/`,
  `.git/HEAD`, `.git/packed-refs` and `.git/refs/` are blocked, in file tools
  and in the shell.

  Destinations: `git clone`, `init`, `worktree add`, `submodule add` and
  `update-index --add`/`--cacheinfo` are judged by the folder or path they
  write.

  Path-less `git clean`, `git stash -u`/`-a` and `git reset --hard` act on the
  current directory, so they are blocked at the root and in an agent folder.
  Still allowed: `git checkout -b`, `git switch -c`, `git checkout <branch>`
  and `git switch <branch>` between branches whose frozen files are equal,
  `git restore src/app.py`, `git checkout -- src/x`, `git clean -fd src`,
  `git config user.name x`, `git -c core.pager=cat log`.
- **Windows paths.** A write path that names a UNC share (`\\server\share`,
  `\\wsl$\...`) or a device (`\\.\...`, `\\?\UNC\...`) is refused as
  unsafe, in file tools and as a shell write target: it can be another name
  for a frozen file, and the hook cannot compare it with a drive path. A
  repository that itself lives on a UNC path is judged as usual, and any
  other UNC spelling is refused from it. A `\\?\C:\` long path is judged
  normally.
- **Here-documents.** Their bodies are data, except when they feed a shell or
  interpreter.
- **Unreadable calls** are blocked.

Re-entry on a built agent is the human's, from their own terminal:
1. Rename the hook to `guard_artifacts.py.off`.
2. Make the change.
3. Remove the agent's line from `.claude/hooks/built-agents.txt` (needed when
   its build.md is deleted or moved).
4. Rename the hook back.

Not false blocks: `2>&1`, `>/dev/null` and `2>NUL` are not writes. A segment
whose only write is a redirect is judged by its target alone, so
`pytest evals/ > results.txt` passes. Commit messages that name frozen paths
pass too.

Still blocked:
- a destructive verb on a holder folder: `find . -name x -delete`,
  `... | xargs rm` from the root, path-less `git clean` at the root. Use
  `find ... -delete` or `find ... -exec rm {} +` instead of `| xargs rm` (a
  destructive command fed by xargs is judged against the current directory
  chain), and give `git clean` a path (`git clean -fd src`).
- the git verbs above while built.
- an extraction with no destination, from the root or after a `cd` out of
  it: `tar xf a.tar`, `cd src && tar xf ../a.tar` (the whole directory chain
  is judged). Name the folder: `tar xf a.tar -C src`.

What it cannot see:
- a script that writes (`python fix.py`, `python -c`);
- a script a shell reads from a file or the network (`curl ... | sh`,
  `cat x.sh | sh`, `sh < x.sh`, `bash <(curl ...)`): the same as
  `sh script.sh`;
- `EDITOR`, `VISUAL` and `PAGER` (only the `GIT_` forms are judged), and git
  config that was already in place before the build;
- on a repository hosted on a UNC path, a drive-letter spelling of its files;
- a path assembled in a variable, backslash escapes inside a name, brace
  expansion, encoded commands;
- a tool that rewrites files in place (`ruff format .`, `prettier --write .`
  over frozen files).

The hook is the first layer. /ship's diff audit from `build_start` and ship's
re-run of the suite from the committed tree (rule 4) are the second layer and
catch those effects. The ratchet covers build.md.

The Test column is filled at build Step 9 AFTER green, WITH THE HOOK ON:
(1) announce the sanctioned edit; (2) make the column edit; (3) confirm the
hook still bites — a dummy edit to `<AGENT_ROOT>/evals/config.yaml` is
blocked. build.md records both. The builder never disables, moves, upgrades
or unregisters the hook; re-entry and upgrades are the human's (steps above).

## Disputes

The builder believing an eval or scenario is wrong is NOT a license to edit
it. Raise the dispute: name the case id, the two readings, the evidence from
the trace. The human routes it (fix-eval via /evals, fix-spec via /spec, or
overrule). The hook makes the wrong path mechanical to catch; the dispute
makes the right path cheap to take.
