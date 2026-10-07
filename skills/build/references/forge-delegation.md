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
   artifact rule (evals/ and docs/agent/ are read-only for the forge run).
5. `## Definition of Done`: the eval-runner command stated exactly (e.g.
   `python -m evals.runner`), "exit code 0 with every case at its threshold",
   plus the adapter smoke test.

Then follow forge-master's OWN two-gate process: `forge-master:prd-import` on
the derived PRD (Human Gate 1 — the human approves the PRD) →
`forge-master:plan-design` (Human Gate 2 — the human approves the plan) →
`forge-master:forge-run`. Never collapse or skip either gate. Forge's "green =
test runner exit code" composes with the runner's "0 = every case at
threshold" — no opinion anywhere in the chain.

## The anti-gaming hook

Installed at build Step 2, BEFORE source exists. Claude Code harness — two
files in the TARGET repo, script first: Claude Code picks up settings changes
mid-session, and once the settings entry is live a missing script blocks
every call.

`.claude/hooks/guard_artifacts.py` (stdin receives the tool call JSON; exit 2
blocks):

```python
import json, os, re, sys

BLOCKED_PREFIXES = ("evals/", "docs/agent/")
ALLOWED = ("docs/agent/build.md",)
SPEC = "docs/agent/spec.md"
HOOKS = ".claude/hooks/"            # the guard protects itself
# Folders that hold a frozen path: removing or moving one takes it along.
HOLDERS = ("", "docs", "evals", "docs/agent", ".claude", ".claude/hooks")
WRITE = re.compile(
    r">|\bsed\s+-i|\bgit\s+(checkout|restore|rm|mv|clean)\b"
    r"|(^|[\s;&|(`])(tee|cp|mv|rm|rmdir|touch|truncate|del|move|copy|ren"
    r"|remove-item|move-item|copy-item|set-content|add-content|out-file"
    r"|new-item)(\s|$)", re.IGNORECASE)
CD = ("cd", "pushd", "chdir", "set-location", "sl")
WORD = re.compile(r"\"([^\"]*)\"|'([^']*)'|([^\s\"'`;|&()<>=,]+)")
# A here-document body is data (a commit message, build.md's text), not paths.
HEREDOC = re.compile(r"<<-?[ \t]*(['\"]?)(\w+)\1([^\n]*)\n.*?\n[ \t]*\2[ \t]*(?=\n|$)",
                     re.DOTALL)


def resolve(raw, base):
    p = os.path.expanduser(os.path.expandvars(str(raw))).replace("\\", "/")
    drive = re.match(r"/(?:cygdrive/|mnt/)?([a-zA-Z])(?:/|$)(.*)", p)
    if os.name == "nt" and drive:      # Git Bash /c/x means C:/x
        p = drive.group(1) + ":/" + drive.group(2)
    return os.path.normpath(os.path.join(base, p))


def rel_to_repo(raw, base=None):
    if not raw:
        return None
    try:
        rp = os.path.relpath(resolve(raw, base or cwd), os.path.normpath(root))
    except ValueError:
        return None      # different drive -> not this repo
    rp = rp.replace("\\", "/").lower()
    if rp == ".." or rp.startswith("../"):
        return None      # outside the repo
    return "" if rp == "." else rp


def frozen(rel):
    return (rel is not None and rel not in ALLOWED
            and rel.startswith(BLOCKED_PREFIXES + (HOOKS,)))


def cells(line):
    s = line.strip()
    if len(s) < 2 or not (s.startswith("|") and s.endswith("|")):
        return []
    return [c.strip() for c in re.split(r"(?<!\\)\|", s[1:-1])]


def only_test_cells(old, new):
    """True when new differs from old only in Test cells of the section 6
    Traceability table: same lines, every changed one a BHV-NNN row outside
    code fences whose 4th cell is the only cell that changed."""
    a = old.replace("\r\n", "\n").rstrip("\n").split("\n")
    b = new.replace("\r\n", "\n").rstrip("\n").split("\n")
    if len(a) != len(b):
        return False
    section, fence = None, False
    for x, y in zip(a, b):
        if re.match(r"\s*(`{3}|~{3})", x):     # a code fence opens or closes
            fence = not fence
        elif not fence and x.startswith("## "):
            section = re.sub(r"^\d+\.\s*", "", x[3:].strip())
        if x == y:
            continue
        cx, cy = cells(x), cells(y)
        if (fence or section != "Traceability" or len(cx) < 4
                or len(cx) != len(cy) or not re.fullmatch(r"BHV-\d{3}", cx[0])
                or cx[:3] + cx[4:] != cy[:3] + cy[4:]):
            return False
    return True


def test_column_fill(path):
    """The spec's Test column is filled with the hook on: apply the call to
    the spec on disk and let it through only if nothing else changes."""
    try:
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read().replace("\r\n", "\n")
    except OSError:
        return False
    if tool == "Write":
        new = ti.get("content")
        return isinstance(new, str) and only_test_cells(text, new)
    edits = ti.get("edits") if tool == "MultiEdit" else [ti]
    if not isinstance(edits, list):
        return False
    new = text
    for e in edits:
        old, rep = (e.get("old_string"), e.get("new_string")) \
            if isinstance(e, dict) else (None, None)
        # A "$&"-style pattern could be expanded by the tool that applies it.
        if not (isinstance(old, str) and isinstance(rep, str)) or not old \
                or re.search(r"\$[$&`'\d]", rep):
            return False
        old, rep = old.replace("\r\n", "\n"), rep.replace("\r\n", "\n")
        if old not in new:
            return False
        new = new.replace(old, rep) if e.get("replace_all") \
            else new.replace(old, rep, 1)
    return only_test_cells(text, new)


def shell_hits(command):
    if not WRITE.search(command):
        return []
    command = HEREDOC.sub(lambda m: m.group(3), command)
    words = [next(g for g in m.groups() if g is not None)
             for m in WORD.finditer(command)]
    dirs, operands, skip = [cwd], [], False
    for i, w in enumerate(words):
        if skip:
            skip = False
        elif w.lower() in CD and i + 1 < len(words) \
                and not words[i + 1].startswith("-"):
            dirs.append(resolve(words[i + 1], dirs[-1]))
            skip = True
        elif w:
            operands.append(w)
    hits = []
    for d in dirs:      # cd evals && rm config.yaml
        rel = rel_to_repo(d)
        if rel is not None and frozen(rel + "/"):
            hits.append("a shell write from inside " + rel)
    for w in operands:  # rm -rf docs/agent, mv docs old, rm -rf *
        for d in dirs:
            rel = rel_to_repo(w, d)
            if rel is not None and rel.endswith("*"):
                rel = rel[:-1].rstrip("/")
            if frozen(rel) or rel in HOLDERS:
                hits.append("a shell write on " + (rel or "the repo root"))
    return hits


# The call arrives as UTF-8; Windows would read it in its own code page.
sys.stdin.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
try:
    call = json.load(sys.stdin)
    tool = call.get("tool_name", "")
    ti = call.get("tool_input") or {}
    # Claude Code runs hooks from the session's current directory, which
    # moves with `cd`; the payload's cwd says where that is. The repo root is
    # the project dir, never the current directory.
    cwd = call.get("cwd") or os.getcwd()
    root = os.environ.get("CLAUDE_PROJECT_DIR") or cwd
    hits = []
    for raw in (ti.get("file_path"), ti.get("notebook_path")):
        rel = rel_to_repo(raw)
        if frozen(rel) and not (rel == SPEC and tool in ("Edit", "MultiEdit", "Write")
                                and test_column_fill(resolve(raw, cwd))):
            hits.append(rel)

    command = str(ti.get("command", "")).replace("\\", "/")
    if command and any(p in command for p in BLOCKED_PREFIXES):
        if WRITE.search(command) and "docs/agent/build.md" not in command:
            hits.append("shell write touching a frozen path")
    if command:
        hits += shell_hits(command)
except Exception as exc:      # fail closed: an unreadable call is not a pass
    hits = ["could not inspect the call (%s)" % exc]

if hits:
    print("BLOCKED by agent-cycle anti-gaming rail: " + "; ".join(sorted(set(hits)))
          + " — frozen pipeline artifacts. Changes go through the re-entry"
          " ladder (dispute -> re-open the owning phase), never through the"
          " builder.", file=sys.stderr)
    sys.exit(2)
sys.exit(0)
```

Then `.claude/settings.json` (merge if it exists):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash|PowerShell",
        "hooks": [
          {
            "type": "command",
            "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/guard_artifacts.py\""
          }
        ]
      }
    ]
  }
}
```

The script path goes through `$CLAUDE_PROJECT_DIR` because Claude Code runs
hooks from the session's current directory, which moves with `cd`. With a
relative path, one `cd src` leaves Python unable to find the script; it exits
2, and from then on every call is blocked, including the `cd ..` that would
undo it.

What it blocks:
- Edit / Write / MultiEdit / NotebookEdit on `evals/**`, `docs/agent/**`
  (except `docs/agent/build.md`) and `.claude/hooks/**` — the hook guards
  itself.
- Shell writes that name one of those paths, or a folder that holds them (the
  repo root, `docs`, `evals`, `docs/agent`, `.claude`, `.claude/hooks`, `*`),
  or that run from inside a frozen folder (`cd evals && rm config.yaml`).
  Paths are resolved from the directory Claude is in (the payload's `cwd`) and
  judged against the project root. Here-document bodies are data, not paths.
- A call it cannot read: blocked, not waved through.

What it cannot see: a script file that writes (`python fix.py`), a glob that
hides the name (`rm ev*/x`), a path assembled in a variable. Those are what
/ship's diff audit is for.

The spec §6 Test column exception: the column is filled at build Step 9 AFTER
the suite is green, WITH THE HOOK ON. The hook lets an Edit, MultiEdit or
Write of `docs/agent/spec.md` through only when it changes nothing but Test
cells: it applies the call to the spec on disk and checks that every changed
line is a `| BHV-NNN |` row of the §6 Traceability table, outside code fences,
whose fourth cell is the only one that changed. Anything else in the spec
stays blocked. Procedure, stated at the gate: (1) announce the sanctioned edit
to the human; (2) make the column edit; (3) confirm the hook still bites —
attempt a dummy edit to `evals/config.yaml` and see it blocked. A build.md DoD
line records both. The builder never disables or moves the hook (Claude
Code's auto mode can refuse that as weakening security anyway); re-entry
under the hook is the human's: they rename the script to
`guard_artifacts.py.off` and back from their own terminal. Additionally, the
hook is a first layer, not the only one: /ship's git-diff audit from
build.md's `build_start` to HEAD (evals/, design.md and spec.md minus the
allow-list must show zero diffs) is the standing second layer on every build,
hook or no hook.

## Disputes

The builder believing an eval or scenario is wrong is NOT a license to edit
it. Raise the dispute: name the case id, the two readings, the evidence from
the trace. The human routes it (fix-eval via /evals, fix-spec via /spec, or
overrule). The hook makes the wrong path mechanical to catch; the dispute
makes the right path cheap to take.
