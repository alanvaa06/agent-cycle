"""agent-cycle anti-gaming hook for Claude Code (PreToolUse).

Reads the tool call JSON on stdin; exit 2 blocks the call, exit 0 lets it
through. agent-cycle:build copies this file to <repo>/.claude/hooks/, seeds
.claude/hooks/built-agents.txt, registers the hook in .claude/settings.json
with exactly GUARD_COMMAND (python -I -S, through $CLAUDE_PROJECT_DIR) and
commits the three together (forge-delegation.md). Upgrading the hook is a
human step: build never writes .claude/hooks/ once the hook exists.

What is frozen is decided from each agent's state on disk at call time:
- Agents: the repo root ("") and every directory agents/<name>/, always --
  never from agent-cycle.yaml, so deleting, renaming or creating that file
  changes nothing. The longest matching agent owns a path.
- Once <agent>/docs/agent/build.md exists, the agent's evals/**,
  docs/agent/design.md and docs/agent/spec.md are frozen. While build.md says
  status: draft, the spec's section 6 Test column may be filled and build.md
  may be edited with file tools; shell writes never touch build.md.
- Ratchet: every agent whose build.md the hook has seen is recorded in the
  tracked file .claude/hooks/built-agents.txt (one prefix per line, "." for
  the root). A recorded agent whose build.md is gone stays frozen as if its
  status were unreadable. Human re-entry: rename this file to
  guard_artifacts.py.off, make the change, remove the agent's line from
  built-agents.txt, rename back.
- agent-cycle.yaml is append-only; .claude/hooks/ is always protected; a
  file that is a hard link to a protected file is protected too.
- .claude/settings.json and settings.local.json: the guard's PreToolUse entry
  and the env key may not change, disableAllHooks may not be set.
- While any agent is built, git verbs that rewrite the working tree from
  another commit (apply, am, revert, cherry-pick, merge, pull, rebase,
  reset --hard, stash pop/apply, checkout/restore from a tree-ish over a
  protected path) are the human's.

Shell commands are read heuristically: per command, the writing verb and its
write targets are parsed from the words; sources that are only read are not
judged. Known blind spots (ship's diff from build_start and ship's re-run of
the suite from the committed tree cover them; the ratchet covers build.md):
a script that writes (python fix.py, python -c), paths assembled in
variables, backslash escapes inside names, brace expansion, encoded
commands, tools that rewrite files in place (ruff format ., prettier --write).
"""
from __future__ import annotations

import contextlib
import fnmatch
import io
import json
import os
import re
import sys
import tempfile
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum, auto
from typing import cast

HOOK_VERSION = 2
HOOK_FILE = "guard_artifacts.py"
GUARD_MATCHER = "Edit|Write|MultiEdit|NotebookEdit|Bash|PowerShell"
GUARD_COMMAND = 'python -I -S "$CLAUDE_PROJECT_DIR/.claude/hooks/guard_artifacts.py"'
MARKER = "agent-cycle.yaml"
AGENTS_DIR = "agents"
CLAUDE_DIR = ".claude"
HOOKS_DIR = ".claude/hooks"
RATCHET = ".claude/hooks/built-agents.txt"
SETTINGS = (".claude/settings.json", ".claude/settings.local.json")
BUILD_MD = "docs/agent/build.md"
SPEC_MD = "docs/agent/spec.md"
DESIGN_MD = "docs/agent/design.md"
DOCS_AGENT = "docs/agent"
EVALS_DIR = "evals"
FILE_TOOLS = ("Edit", "MultiEdit", "Write")
AGENT_NAME = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
RATCHET_LINE = re.compile(r"agents/[^/\s]+/")

# Redirects that only move or drop a stream write no file: 2>&1, >/dev/null, 2>NUL.
FD_REDIRECT = re.compile(
    r"(?:\d|&|\*)?>>?\s*(?:/dev/null|nul|\$null)(?![\w./:-])|(?:\d|\*)?>&\s*(?:\d+|-)(?![\w.])",
    re.IGNORECASE)
CD = ("cd", "pushd", "chdir", "set-location", "sl", "push-location")
SHELLS = ("bash", "sh", "zsh", "dash", "ksh", "pwsh", "powershell", "cmd")
SHELL_FLAGS = ("-c", "-command", "/c", "/k")
EVAL_VERBS = frozenset({"eval", "iex", "invoke-expression"})
INTERPRETER = re.compile(
    r"(?:^|[\s|(/])(?:bash|sh|zsh|dash|ksh|pwsh|powershell|python[\d.]*|node|perl|ruby)"
    r"(?:\.exe)?(?=\s|$)", re.IGNORECASE)
HEREDOC = re.compile(r"<<-?[ \t]*(['\"]?)(\w+)\1([^\n]*)\n(?:.*?\n)??[ \t]*\2[ \t]*(?=\n|$)",
                     re.DOTALL)
SEGMENT_END = re.compile(r"&&|\|\||;|\n|&(?![>&])")
TOKEN = re.compile(
    r"(?P<sep>&&|\|\||;|\n|&(?![>&]))"
    r"|(?P<pipe>\|)"
    r"|(?P<redir>(?:\d|&|\*)?>>?[|&]?)"
    r"|(?P<input><<-?|<)"
    r"|\$'(?P<ansi>[^']*)'"
    r"|\"(?P<dq>[^\"]*)\"|'(?P<sq>[^']*)'"
    r"|(?P<bare>[^\s\"'`;|&()<>,]+)"
    r"|(?P<other>\S)")
GLOB = re.compile(r"[*?\[]")
ASSIGNMENT = re.compile(r"[A-Za-z_]\w*=")
DOTNET = re.compile(r"\]::(Write|Append|Delete|Move|Copy|Create|Replace|Open)", re.IGNORECASE)
CMD_FLAG = re.compile(r"/[a-z?+-]+(?::[^/]*)?", re.IGNORECASE)   # /y, /MIR, /R:3

# Words in front of the real verb, with their flags that take a value.
WRAPPERS: dict[str, frozenset[str]] = {
    "sudo": frozenset({"-u", "-g", "-h", "-p", "-C", "-D", "-U", "-r", "-t"}),
    "doas": frozenset({"-u", "-C"}),
    "env": frozenset({"-u", "-C", "-S"}),
    "nice": frozenset({"-n"}),
    "ionice": frozenset({"-c", "-n"}),
    "stdbuf": frozenset({"-i", "-o", "-e"}),
    "timeout": frozenset({"-s", "-k"}),
    "xargs": frozenset({"-I", "-n", "-P", "-L", "-s", "-E", "-d", "-a"}),
    "exec": frozenset({"-a"}),
    **{name: frozenset() for name in ("nohup", "time", "command", "builtin", "!", "{", "}", "if",
                                      "then", "else", "elif", "do", "while", "until")},
}
# Every argument of these is a write target; the first two kinds remove or move it.
DELETE_VERBS = frozenset({"rm", "rmdir", "del", "erase", "rd", "unlink", "shred", "remove-item", "ri"})
MOVE_VERBS = frozenset({"mv", "move", "ren", "rename", "rename-item", "rni", "move-item", "mi"})
OPERAND_VERBS = frozenset({"touch", "truncate", "tee", "ln", "mklink", "fsutil", "new-item", "ni",
                           "clear-content", "clc"})
# PowerShell content cmdlets write their -Path (or first positional) only.
CONTENT_VERBS = frozenset({"set-content", "sc", "add-content", "ac", "out-file"})
PS_SWITCHES = frozenset({"-force", "-append", "-noclobber", "-nonewline", "-passthru", "-whatif",
                         "-confirm", "-recurse", "-container", "-asbytestream"})
PATH_FLAGS = ("-path", "-literalpath", "-filepath", "-pspath", "-lp")
DEST_FLAGS = ("-destination",)
# git: global options that take a value; verbs that rewrite the tree (the human's once built).
GIT_VALUE_OPTIONS = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace"})
GIT_TREE_VERBS = frozenset({"apply", "am", "revert", "cherry-pick", "merge", "pull", "rebase"})
STASH_ACTIONS = frozenset({"push", "save", "pop", "apply", "branch", "drop", "list", "show", "clear",
                           "create", "store"})


class Rule(Enum):
    FREE = auto()
    FROZEN = auto()
    TEST_COLUMN_ONLY = auto()
    BUILD_DRAFT = auto()
    APPEND_ONLY = auto()
    SETTINGS = auto()
    USER_SETTINGS = auto()


class Unreadable(Exception):
    """A file exists but cannot be read or decoded: never treated as absent."""


@dataclass(frozen=True)
class Call:
    tool: str
    tool_input: dict[str, object]
    cwd: str
    root: str


@dataclass(frozen=True)
class Agent:
    prefix: str          # lower-case, '/'-terminated; '' for the repo root
    folder: str          # the same folder in its on-disk case, for file access
    status: str | None   # None: build not started; '': frozen whatever it says

    @property
    def built(self) -> bool:
        return self.status is not None


@dataclass(frozen=True)
class Snapshot:
    """The repo's state, read once per call."""
    root: str
    agents: tuple[Agent, ...]            # longest prefix first; the root last
    holders: frozenset[str]            # folders a destructive verb may not take along
    protected_dirs: tuple[str, ...]     # frozen folders: nothing inside may be written
    protected_files: tuple[str, ...]    # single frozen or content-checked files
    protected_strings: tuple[str, ...]

    @property
    def any_built(self) -> bool:
        return any(agent.built for agent in self.agents)

    def agent_for(self, rel: str) -> Agent:
        return next(agent for agent in self.agents if rel.startswith(agent.prefix))

    @property
    def root_agent(self) -> Agent:
        return self.agents[-1]


@dataclass(frozen=True)
class Word:
    text: str
    quoted: bool         # one quoted string: data, not a path someone typed bare


@dataclass(frozen=True)
class Segment:
    raw: str
    commands: tuple[tuple[Word, ...], ...]     # split on pipes, ( ) and backticks
    targets: tuple[Word, ...]                  # redirect targets

    @property
    def words(self) -> tuple[Word, ...]:
        return tuple(word for command in self.commands for word in command)


DOT = Word(".", quoted=False)


# --- paths

def strip_device_prefix(path: str) -> str:
    """'/'-separated path without a \\\\?\\ or \\\\.\\ prefix before a drive or UNC
    share; a device such as \\\\.\\NUL is kept (it is outside every repo)."""
    match = re.match(r"//[?.]/(unc/|(?=[a-zA-Z]:))", path, re.IGNORECASE)
    if match is None:
        return path
    return ("//" if match.group(1) else "") + path[match.end():]


def posix_drive(path: str) -> str:
    drive = re.match(r"/(?:cygdrive/|mnt/)?([a-zA-Z])(?:/|$)(.*)", path)
    if os.name == "nt" and drive:      # Git Bash /c/x means C:/x
        return drive.group(1) + ":/" + drive.group(2)
    return path


def win_trim(path: str) -> str:
    """Win32 drops trailing dots and spaces from every path component."""
    if os.name != "nt":
        return path
    return "/".join(part if part in (".", "..") else (part.rstrip(". ") or part)
                    for part in path.split("/"))


def canonical(path: str) -> str:
    """Real path: junctions, symlinks, 8.3 names and on-disk case resolved."""
    return strip_device_prefix(os.path.realpath(path).replace("\\", "/"))


def alternate_stream(raw: str) -> bool:
    """A ':' after the drive letter names an NTFS stream (file::$DATA)."""
    if os.name != "nt":
        return False
    path = strip_device_prefix(raw.replace("\\", "/"))
    return ":" in re.sub(r"^[a-zA-Z]:", "", path)


# A UNC share (\\server\share), a device namespace (\\.\...) or a UNC device path (\\?\UNC\...);
# NOT a \\?\C:\ long-path, which strip_device_prefix turns into a plain drive path.
DEVICE_OR_UNC = re.compile(r"[\\/]{2}(?:[.][\\/]|[?][\\/]unc(?=[\\/])|(?![.?][\\/]))", re.IGNORECASE)


def win_unsafe_path(raw: str) -> bool:
    """On Windows, a file-tool path naming a UNC share or a device: realpath keeps its form, so the
    guard cannot canonicalise and compare it. It is refused as unsafe rather than judged."""
    return os.name == "nt" and DEVICE_OR_UNC.match(raw) is not None


def file_tool_path(raw: str, cwd: str) -> str:
    """A file tool takes its path literally: no $VAR or ~ expansion."""
    path = win_trim(posix_drive(strip_device_prefix(raw.replace("\\", "/"))))
    return canonical(os.path.join(cwd, path))


def shell_paths(word: str, base: str) -> list[str]:
    """Where a shell word may point; also the part before an NTFS stream suffix."""
    path = os.path.expanduser(os.path.expandvars(word)).replace("\\", "/")
    path = win_trim(posix_drive(strip_device_prefix(path)))
    paths = [canonical(os.path.join(base, path))]
    stream = re.match(r"([a-zA-Z]:)?([^:]*):", path)
    if os.name == "nt" and stream:
        paths.append(canonical(os.path.join(base, (stream.group(1) or "") + stream.group(2))))
    return paths


def rel_to_repo(path: str, root: str) -> str | None:
    """Lower-case '/'-joined path of a canonical path relative to root; '' for root."""
    try:
        rel = os.path.relpath(path, root)
    except ValueError:
        return None                    # different drive -> not this repo
    rel = rel.replace("\\", "/").lower()
    if rel == ".." or rel.startswith("../"):
        return None
    return "" if rel == "." else rel


def under(rel: str, folder: str) -> bool:
    return rel == folder or rel.startswith(folder + "/")


# --- agents and their state

def read_text(path: str) -> str | None:
    """None when the file is missing; raises Unreadable when it cannot be read."""
    try:
        with open(path, encoding="utf-8-sig", newline="") as handle:
            return handle.read().replace("\r\n", "\n")
    except (FileNotFoundError, NotADirectoryError):
        return None
    except (OSError, UnicodeDecodeError) as exc:
        raise Unreadable(f"{path} is unreadable ({exc})") from exc


def build_status(root: str, folder: str) -> str | None:
    """None while build.md is absent; else its frontmatter status ('' if unreadable)."""
    try:
        text = read_text(os.path.join(root, folder, BUILD_MD))
    except Unreadable:
        return ""
    if text is None:
        return None
    if not text.startswith("---\n"):
        return ""
    for line in text.split("\n")[1:]:
        if line.strip() == "---":
            break
        key, sep, value = line.partition(":")
        if sep and key.strip() == "status":
            value = re.split(r"\s+#", value.strip(), maxsplit=1)[0].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1].strip()
            return value
    return ""


def agent_folders(root: str) -> list[str]:
    """'agents/<name>/' for every directory under agents/, in on-disk case."""
    base = os.path.join(root, AGENTS_DIR)
    try:
        names = os.listdir(base)
    except (FileNotFoundError, NotADirectoryError):
        return []
    return sorted(f"{AGENTS_DIR}/{name}/" for name in names if os.path.isdir(os.path.join(base, name)))


def read_ratchet(root: str) -> frozenset[str]:
    text = read_text(os.path.join(root, RATCHET))
    if text is None:
        return frozenset()
    recorded: set[str] = set()
    for line in text.split("\n"):
        entry = line.strip().lower()
        if entry == ".":
            recorded.add("")
        elif RATCHET_LINE.fullmatch(entry):
            recorded.add(entry)
    return frozenset(recorded)


def write_ratchet(root: str, prefixes: Iterable[str]) -> bool:
    """Record the built agents; False when the file could not be written.

    A failed write changes nothing for this call, which decides from the
    in-memory union; the next call tries again.
    """
    path = os.path.join(root, RATCHET)
    text = "".join((prefix or ".") + "\n" for prefix in sorted(prefixes))
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        handle, temp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".built-agents.", suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
            os.replace(temp, path)
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.remove(temp)
    except OSError:
        return False
    return True


def take_snapshot(root: str) -> Snapshot:
    folders: dict[str, str] = {"": ""}
    for folder in agent_folders(root):
        folders.setdefault(folder.lower(), folder)
    recorded = read_ratchet(root)
    for prefix in recorded:
        folders.setdefault(prefix, prefix)
    statuses = {prefix: build_status(root, folder) for prefix, folder in folders.items()}
    seen = {prefix for prefix, status in statuses.items() if status is not None}
    if not seen <= recorded:
        write_ratchet(root, recorded | seen)
    agents = tuple(sorted(
        (Agent(prefix, folders[prefix], "" if status is None and prefix in recorded else status)
         for prefix, status in statuses.items()),
        key=lambda agent: (-len(agent.prefix), agent.prefix)))
    built = [agent.prefix for agent in agents if agent.built]
    holders = {"", CLAUDE_DIR, HOOKS_DIR}
    dirs = [HOOKS_DIR]
    strings = [HOOKS_DIR, ".claude/settings", MARKER]
    files = [*SETTINGS, MARKER]
    for prefix in built:
        holders |= {prefix.rstrip("/"), prefix + "docs", prefix + DOCS_AGENT, prefix + EVALS_DIR}
        if prefix:
            holders.add(AGENTS_DIR)
        dirs += [prefix + EVALS_DIR, prefix + DOCS_AGENT]
        strings += [prefix + EVALS_DIR + "/", prefix + DESIGN_MD, prefix + SPEC_MD, prefix + BUILD_MD]
        files += [prefix + DESIGN_MD, prefix + SPEC_MD, prefix + BUILD_MD]
    return Snapshot(root, agents, frozenset(holders), tuple(dirs), tuple(files), tuple(strings))


def classify(rel: str, snap: Snapshot) -> Rule:
    if under(rel, HOOKS_DIR):
        return Rule.FROZEN
    if rel in SETTINGS:
        return Rule.SETTINGS
    if rel == MARKER:
        return Rule.APPEND_ONLY
    agent = snap.agent_for(rel)
    if agent.status is None:
        return Rule.FREE               # build not started: earlier phases may write
    sub = rel[len(agent.prefix):]
    if sub == BUILD_MD:
        return Rule.BUILD_DRAFT if agent.status == "draft" else Rule.FROZEN
    if sub == SPEC_MD:
        return Rule.TEST_COLUMN_ONLY if agent.status == "draft" else Rule.FROZEN
    if sub == DESIGN_MD or under(sub, EVALS_DIR):
        return Rule.FROZEN
    return Rule.FREE


# --- proposed content checks

def proposed_text(call: Call, current: str) -> str | None:
    """The file content after the call, or None when it cannot be computed safely."""
    if call.tool == "Write":
        content = call.tool_input.get("content")
        return content.replace("\r\n", "\n") if isinstance(content, str) else None
    edits = call.tool_input.get("edits") if call.tool == "MultiEdit" else [call.tool_input]
    if not isinstance(edits, list):
        return None
    text = current
    for edit in edits:
        if not isinstance(edit, dict):
            return None
        old, new = edit.get("old_string"), edit.get("new_string")
        # A "$&"-style pattern could be expanded by the tool that applies it.
        if not (isinstance(old, str) and isinstance(new, str)) or not old \
                or re.search(r"\$[$&`'\d]", new):
            return None
        old, new = old.replace("\r\n", "\n"), new.replace("\r\n", "\n")
        if old not in text:
            return None
        text = text.replace(old, new) if edit.get("replace_all") else text.replace(old, new, 1)
    return text


def cells(line: str) -> list[str]:
    stripped = line.strip()
    if len(stripped) < 2 or not (stripped.startswith("|") and stripped.endswith("|")):
        return []
    return [c.strip() for c in re.split(r"(?<!\\)\|", stripped[1:-1])]


def only_test_cells(old: str, new: str) -> bool:
    """True when new differs from old only in Test cells (4th column) of BHV-NNN
    rows of the section 6 Traceability table, outside code fences."""
    before = old.rstrip("\n").split("\n")
    after = new.rstrip("\n").split("\n")
    if len(before) != len(after):
        return False
    section, fence = None, False
    for x, y in zip(before, after, strict=True):
        if re.match(r"\s*(`{3}|~{3})", x):
            fence = not fence
        elif not fence and x.startswith("## "):
            section = re.sub(r"^\d+\.\s*", "", x[3:].strip())
        if x == y:
            continue
        cx, cy = cells(x), cells(y)
        if (fence or section != "Traceability" or len(cx) < 4 or len(cx) != len(cy)
                or not re.fullmatch(r"BHV-\d{3}", cx[0]) or cx[:3] + cx[4:] != cy[:3] + cy[4:]):
            return False
    return True


def parse_marker(text: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
    """(agents, other lines) of a valid agent-cycle.yaml, else None."""
    layout, agents, other = None, None, []
    for raw in text.split("\n"):
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        match = re.fullmatch(r"(\w+):\s*(.*)", line)
        if match is None:
            return None
        key, value = match.group(1), match.group(2).strip()
        if key == "layout":
            layout = value
        elif key == "agents":
            listed = re.fullmatch(r"\[(.*)\]", value)
            if listed is None:
                return None
            items = tuple(item.strip() for item in listed.group(1).split(",") if item.strip())
            if not all(AGENT_NAME.fullmatch(item) for item in items):
                return None
            agents = items
        else:
            other.append(line)
    if layout != "workspace" or agents is None:
        return None
    return agents, tuple(other)


def marker_change_ok(current: str | None, new: str | None, snap: Snapshot) -> bool:
    proposed = parse_marker(new) if new is not None else None
    if proposed is None:
        return False
    if current is None:                # creating the marker
        return not snap.root_agent.built   # a built one-agent root moves by hand
    existing = parse_marker(current)
    if existing is None:
        return False
    return existing[1] == proposed[1] and set(existing[0]) <= set(proposed[0])


def guard_entries(settings: object) -> set[tuple[str, str, str]]:
    """(matcher, type, command) of every PreToolUse hook that runs this file."""
    entries: set[tuple[str, str, str]] = set()
    hooks = settings.get("hooks") if isinstance(settings, dict) else None
    groups = hooks.get("PreToolUse") if isinstance(hooks, dict) else None
    for group in groups if isinstance(groups, list) else []:
        inner = group.get("hooks") if isinstance(group, dict) else None
        for hook in inner if isinstance(inner, list) else []:
            command = hook.get("command") if isinstance(hook, dict) else None
            if isinstance(command, str) and HOOK_FILE in command:
                entries.add((json.dumps(group.get("matcher")), json.dumps(hook.get("type")), command))
    return entries


PINNED_ENTRY = (json.dumps(GUARD_MATCHER), json.dumps("command"), GUARD_COMMAND)


def guarded_env(settings: dict[str, object], user_file: bool) -> object:
    """The env entries the rule compares: all of them in the repo's files; in
    the user's file only PATH and PYTHON*, which steer the hook's interpreter."""
    env = settings.get("env")
    if not user_file or not isinstance(env, dict):
        return env
    return {key: value for key, value in env.items()
            if isinstance(key, str) and (key.upper() == "PATH" or key.upper().startswith("PYTHON"))}


def settings_change_ok(current: str | None, new: str | None, user_file: bool = False) -> bool:
    """Valid JSON; the guard entries and env unchanged (or the pinned entry
    installed where there was none); hooks not disabled."""
    if new is None:
        return False
    try:
        proposed = json.loads(new)
    except ValueError:
        return False
    if not isinstance(proposed, dict) or proposed.get("disableAllHooks", False) is not False:
        return False
    try:
        existing = json.loads(current) if current else {}
    except ValueError:
        existing = {}                  # an invalid file registers nothing
    if not isinstance(existing, dict):
        existing = {}
    if guarded_env(proposed, user_file) != guarded_env(existing, user_file):
        return False
    before, after = guard_entries(existing), guard_entries(proposed)
    return after == before or (not before and after == {PINNED_ENTRY})


def frozen_files(snap: Snapshot) -> Iterator[str]:
    """Every file a hard link must not reach."""
    yield os.path.join(snap.root, MARKER)
    for name in SETTINGS:
        yield os.path.join(snap.root, name)
    folders = [HOOKS_DIR]
    for agent in snap.agents:
        if agent.built:
            folders.append(agent.folder + EVALS_DIR)
            for sub in (DESIGN_MD, SPEC_MD, BUILD_MD):
                yield os.path.join(snap.root, agent.folder, sub)
    for folder in folders:
        for current, _, names in os.walk(os.path.join(snap.root, folder)):
            for name in names:
                yield os.path.join(current, name)


def hard_link_hit(path: str, snap: Snapshot) -> str | None:
    """The protected file that path is another name for, if any."""
    try:
        info = os.stat(path)
    except (OSError, ValueError):
        return None
    if info.st_nlink < 2:
        return None
    for frozen in frozen_files(snap):
        try:
            other = os.stat(frozen)
        except OSError:
            continue
        if (other.st_dev, other.st_ino) == (info.st_dev, info.st_ino):
            target = canonical(frozen)
            if os.path.normcase(target) != os.path.normcase(path):
                return rel_to_repo(target, snap.root) or target
    return None


def user_settings(path: str) -> bool:
    home = canonical(os.path.join(os.path.expanduser("~"), CLAUDE_DIR, "settings.json"))
    return os.path.normcase(path) == os.path.normcase(home)


# --- the two kinds of call

def content_change_ok(rule: Rule, call: Call, path: str, snap: Snapshot) -> bool:
    if rule is Rule.FREE or (rule is Rule.BUILD_DRAFT and call.tool in FILE_TOOLS):
        return True
    if call.tool not in FILE_TOOLS or rule not in (Rule.TEST_COLUMN_ONLY, Rule.APPEND_ONLY,
                                                      Rule.SETTINGS, Rule.USER_SETTINGS):
        return False
    try:
        current = read_text(path)
    except Unreadable:
        return False
    new = proposed_text(call, current or "")
    if rule is Rule.TEST_COLUMN_ONLY:
        return current is not None and new is not None and only_test_cells(current, new)
    if rule is Rule.APPEND_ONLY:
        return marker_change_ok(current, new, snap)
    return settings_change_ok(current, new, user_file=rule is Rule.USER_SETTINGS)


def file_hits(call: Call, snap: Snapshot) -> list[str]:
    hits: list[str] = []
    for key in ("file_path", "notebook_path"):
        raw = call.tool_input.get(key)
        if raw is None or raw == "":
            continue
        if not isinstance(raw, str):
            raise ValueError(f"{key} is not a string")
        if alternate_stream(raw) or win_unsafe_path(raw):
            hits.append("unsafe path " + raw)
            continue
        path = file_tool_path(raw, call.cwd)
        link = hard_link_hit(path, snap)
        if link is not None:
            hits.append("a hard link to " + link)
        rel = rel_to_repo(path, snap.root)
        if rel is None:
            if user_settings(path) and not content_change_ok(Rule.USER_SETTINGS, call, path, snap):
                hits.append("the user settings file " + path)
            continue
        if not content_change_ok(classify(rel, snap), call, path, snap):
            hits.append(rel)
    return hits


def interpreter_heredoc(match: re.Match[str]) -> bool:
    """Does the here-document feed a shell or interpreter (its body is code)?"""
    before = SEGMENT_END.split(match.string[:match.start()])[-1]
    return INTERPRETER.search(before + " " + match.group(3)) is not None


def segments(command: str) -> list[Segment]:
    """Split on ; && || & and newlines; a segment's commands split on pipes,
    parentheses and backticks. Adjacent quoted and bare pieces join into one word."""
    found: list[Segment] = []
    commands: list[list[Word]] = [[]]
    targets: list[Word] = []
    pieces: list[tuple[str, bool]] = []
    start, last_end, want_target = 0, -1, False

    def flush_word() -> None:
        nonlocal want_target
        if pieces:
            word = Word("".join(text for text, _ in pieces), len(pieces) == 1 and pieces[0][1])
            if want_target:
                targets.append(word)
                want_target = False
            else:
                commands[-1].append(word)
            pieces.clear()

    def end_command() -> None:
        flush_word()
        if commands[-1]:
            commands.append([])

    def flush_segment(end: int) -> None:
        nonlocal want_target
        flush_word()
        found_commands = tuple(tuple(words) for words in commands if words)
        if found_commands or targets:
            found.append(Segment(command[start:end], found_commands, tuple(targets)))
        commands[:] = [[]]
        targets.clear()
        want_target = False

    for match in TOKEN.finditer(command):
        kind = match.lastgroup
        if kind in ("ansi", "dq", "sq", "bare"):
            if match.start() != last_end:
                flush_word()
            pieces.append((match.group(kind), kind != "bare"))
            last_end = match.end()
            continue
        last_end = -1
        if kind == "sep":
            flush_segment(match.start())
            start = match.end()
        elif kind == "pipe" or (kind == "other" and match.group() in "()`"):
            end_command()
        else:
            flush_word()
            want_target = want_target or kind == "redir"
    flush_segment(len(command))
    return found


def segment_dirs(segment: Segment, dirs: list[str]) -> None:
    """Add the directories a segment moves into (cd x, git -C x) to dirs."""
    words = segment.words
    for i, word in enumerate(words):
        if word.text.lower() in CD and not word.quoted:
            rest = [w for w in words[i + 1:] if not (w.text.startswith("-") or w.text.lower() == "/d")]
            if rest:
                dirs.append(shell_paths(rest[0].text, dirs[-1])[0])
        elif word.text == "-C" and i + 1 < len(words):
            dirs.append(shell_paths(words[i + 1].text, dirs[-1])[0])


def verb_name(text: str) -> str:
    """rm for rm, /bin/rm, rm.exe, RM, C:/Windows/System32/rm.exe."""
    return text.lower().rsplit("/", 1)[-1].removesuffix(".exe")


def split_command(words: Sequence[Word]) -> tuple[str, tuple[Word, ...], bool]:
    """(verb, its arguments, fed by xargs) after assignments and wrappers."""
    i, fed = 0, False
    while i < len(words):
        word = words[i]
        name = verb_name(word.text)
        if not word.quoted and ASSIGNMENT.match(word.text):
            i += 1
            continue
        if name not in WRAPPERS:
            return name, tuple(words[i + 1:]), fed
        fed = fed or name == "xargs"
        i += 1
        while i < len(words) and words[i].text.startswith("-") and len(words[i].text) > 1:
            i += 2 if words[i].text in WRAPPERS[name] else 1
        if name == "timeout" and i < len(words):
            i += 1                     # the duration
    return "", (), fed


def ps_args(words: Sequence[Word]) -> tuple[list[Word], dict[str, list[Word]]]:
    """PowerShell-style (positional, named) arguments; -Name:value is accepted."""
    positional: list[Word] = []
    named: dict[str, list[Word]] = {}
    i = 0
    while i < len(words):
        word = words[i]
        text = word.text.lower()
        if not word.quoted and text.startswith("-") and len(text) > 1:
            name, colon, _ = text.partition(":")
            if colon:
                named.setdefault(name, []).append(Word(word.text[len(name) + 1:], quoted=False))
            elif name not in PS_SWITCHES and i + 1 < len(words):
                named.setdefault(name, []).append(words[i + 1])
                i += 1
        else:
            positional.append(word)
        i += 1
    return positional, named


def named_values(named: dict[str, list[Word]], flags: Sequence[str]) -> list[Word]:
    """Values of the named arguments that abbreviate one of flags."""
    return [value for name, values in named.items() if any(flag.startswith(name) for flag in flags)
            for value in values]


def cp_target(args: Sequence[Word]) -> list[Word]:
    positional: list[Word] = []
    i = 0
    while i < len(args):
        text = args[i].text
        if text.startswith("--target-directory="):
            return [Word(text.split("=", 1)[1], args[i].quoted)]
        if re.fullmatch(r"-[a-zA-Z]*t|--target-directory", text) and i + 1 < len(args):
            return [args[i + 1]]
        if text in ("-S", "--suffix"):
            i += 2
            continue
        if not (text.startswith("-") and len(text) > 1):
            positional.append(args[i])
        i += 1
    return positional[-1:]


def find_writes(args: Sequence[Word]) -> tuple[list[Word], bool, bool]:
    """find's starting points are the targets of -delete or -exec <write verb>."""
    i = 0
    while i < len(args) and not args[i].text.startswith(("-", "!")):
        i += 1
    paths = list(args[:i]) or [DOT]
    expression = args[i:]
    for k, word in enumerate(expression):
        text = word.text.lower()
        if text == "-delete":
            return paths, True, True
        if text in ("-exec", "-execdir", "-ok", "-okdir") and k + 1 < len(expression):
            verb, rest, _ = split_command(expression[k + 1:])
            _, destructive, is_write = verb_writes(verb, rest)
            if is_write or verb == "git":
                return paths, destructive or verb == "git", True
    return [], False, False


def verb_writes(verb: str, args: Sequence[Word]) -> tuple[list[Word], bool, bool]:
    """(write targets, destructive, is a write) for one command. Sources a
    command only reads are not targets."""
    if verb in DELETE_VERBS or verb in MOVE_VERBS:
        return list(args), True, True
    if verb in OPERAND_VERBS:
        return list(args), False, True
    if verb in CONTENT_VERBS:
        positional, named = ps_args(args)
        return named_values(named, PATH_FLAGS) or positional[:1], False, True
    if verb == "cp":
        return cp_target(args), False, True
    if verb in ("copy", "copy-item", "cpi", "xcopy"):
        positional, named = ps_args(args)
        positional = [w for w in positional if not CMD_FLAG.fullmatch(w.text)]
        destination = named_values(named, DEST_FLAGS)
        if verb == "xcopy":
            return positional[1:2] or [DOT], False, True
        return destination or (positional[-1:] if len(positional) > 1 else [DOT]), False, True
    if verb == "robocopy":
        flags = {w.text.lower() for w in args if CMD_FLAG.fullmatch(w.text)}
        positional = [w for w in args if not CMD_FLAG.fullmatch(w.text)]
        moving = bool(flags & {"/mov", "/move"})
        return positional[1:2] + (positional[:1] if moving else []), moving or bool(flags & {"/mir", "/purge"}), True
    if verb == "rsync":
        texts = [w.text for w in args]
        positional = [w for w in args if not w.text.startswith("-")]
        if "--remove-source-files" in texts:
            return positional, True, True
        return positional[-1:], any(t.startswith("--delete") for t in texts), True
    if verb == "dd":
        return [Word(w.text.split("=", 1)[1], w.quoted) for w in args if w.text.lower().startswith("of=")], False, True
    in_place = {"sed": r"-[a-zA-Z]*i|--in-place", "perl": r"-[a-zA-Z]*i", "awk": r"-i$", "gawk": r"-i$"}
    if verb in in_place and any(re.match(in_place[verb], w.text) for w in args if not w.quoted):
        return list(args), False, True
    if verb == "find":
        return find_writes(args)
    return [], False, False


def git_tree_and_paths(sub: str, before: Sequence[Word], after: Sequence[Word],
                       dashdash: bool) -> tuple[bool, list[Word]]:
    """(reads from another commit, pathspec) of git checkout / restore."""
    tree, branching, positional = False, False, []
    i = 0
    while i < len(before):
        text = before[i].text
        if sub == "restore" and text in ("--source", "-s"):
            tree, i = True, i + 2
            continue
        if sub == "restore" and text.startswith("--source="):
            tree = True
        elif sub == "checkout" and text in ("-b", "-B", "--orphan"):
            branching, i = True, i + 2
            continue
        elif not text.startswith("-") or text == "-":
            positional.append(before[i])
        i += 1
    if sub == "restore":
        return tree, positional + list(after)
    if dashdash:
        return bool(positional), positional[1:] + list(after)
    if branching:
        return True, []
    if len(positional) >= 2:
        return True, positional[1:]
    return False, positional       # one word: a branch or a path; judged as a path


def git_writes(args: Sequence[Word], dirs: list[str], snap: Snapshot) -> tuple[list[Word], bool, list[str]]:
    """(write targets, destructive, outright blocks) of one git command."""
    i = 0
    while i < len(args) and args[i].text.startswith("-"):
        i += 2 if args[i].text in GIT_VALUE_OPTIONS else 1
    if i >= len(args):
        return [], False, []
    sub, rest = args[i].text.lower(), args[i + 1:]
    texts = [w.text for w in rest]
    dashdash = "--" in texts
    before = rest[:texts.index("--")] if dashdash else rest
    after = rest[texts.index("--") + 1:] if dashdash else ()
    flags = [w.text for w in before if w.text.startswith("-")]
    human = [f"git {sub} while an agent is built (the human runs it)"] if snap.any_built else []
    if sub in ("rm", "mv"):
        return [w for w in rest if not w.text.startswith("-")], True, []
    if sub == "clean":                 # path-less: the current directory
        paths = list(after) or [w for k, w in enumerate(before) if not w.text.startswith("-")
                                and (k == 0 or before[k - 1].text not in ("-e", "--exclude"))]
        return paths or [DOT], True, []
    if sub == "stash":
        words = [w for k, w in enumerate(before) if not w.text.startswith("-")
                 and (k == 0 or before[k - 1].text not in ("-m", "--message"))]
        action = words[0].text.lower() if words and words[0].text.lower() in STASH_ACTIONS else "push"
        if action in ("pop", "apply", "branch"):
            return [], False, human
        if action not in ("push", "save"):
            return [], False, []
        untracked = any(f in ("--include-untracked", "--all") or re.fullmatch(r"-[a-zA-Z]*[ua][a-zA-Z]*", f)
                        for f in flags)
        return (list(after) or [DOT]) if untracked else list(after), untracked, []
    if sub == "reset":
        if "--hard" in flags:
            return [DOT], True, human
        return [w for w in before if not w.text.startswith("-")] + list(after), False, []
    if sub in ("checkout", "restore"):
        tree, pathspec = git_tree_and_paths(sub, before, after, dashdash)
        if tree and snap.any_built and any(
                w.text.startswith(":") or target_hits(w, dirs, snap, destructive=True) for w in pathspec):
            return [], False, [f"git {sub} from another commit over protected paths while an agent is "
                               "built (the human runs it)"]
        return pathspec, False, []
    if sub in GIT_TREE_VERBS:
        return [], False, human
    return [], False, []


def glob_hits(pattern: str, snap: Snapshot, destructive: bool) -> list[str]:
    """A glob reaches a protected file at its own depth, a protected folder at
    its depth or deeper, and (destructive verbs) a holder at its depth or above."""
    parts = pattern.split("/")

    def reaches(target: str) -> bool:
        return all(fnmatch.fnmatchcase(part, glob)
                   for glob, part in zip(parts, target.split("/"), strict=False))

    def depth(target: str) -> int:
        return target.count("/") + 1

    reached = [f for f in snap.protected_files if depth(f) == len(parts) and reaches(f)]
    reached += [d for d in snap.protected_dirs if depth(d) <= len(parts) and reaches(d)]
    if destructive:
        reached += [h for h in snap.holders if h and len(parts) <= depth(h) and reaches(h)]
    return [f"a shell glob reaching {target}" for target in reached]


def target_hits(word: Word, dirs: list[str], snap: Snapshot, destructive: bool) -> list[str]:
    """Why writing (or, destructive, removing) word would touch a protected path."""
    hits: list[str] = []
    if not word.quoted:
        hits += [f"a shell write naming {s}" for s in snap.protected_strings if s in word.text.lower()]
    texts = [word.text]
    if "=" in word.text[1:]:
        texts.append(word.text.split("=", 1)[1])        # --file=evals/x
    for folder in dirs:
        for text in texts:
            for path in shell_paths(text, folder):
                link = hard_link_hit(path, snap)
                if link is not None:
                    hits.append("a shell write through a hard link to " + link)
                rel = rel_to_repo(path, snap.root)
                if rel is None:
                    continue
                if GLOB.search(rel):
                    hits += glob_hits(rel, snap, destructive)
                if classify(rel, snap) is not Rule.FREE or (destructive and rel in snap.holders):
                    hits.append("a shell write on " + (rel or "the repo root"))
    return hits


def command_hits(command: str, dirs: list[str], snap: Snapshot) -> list[str]:
    command = re.sub(r"\\\r?\n|`\r?\n", "", command)       # line continuations
    command = command.replace("\\", "/")
    # A here-document body is data (a commit message, build.md's text), unless
    # it feeds a shell or an interpreter, where it is code.
    command = HEREDOC.sub(lambda m: m.group(0) if interpreter_heredoc(m) else m.group(3), command)
    command = FD_REDIRECT.sub(" ", command)
    hits: list[str] = []
    dirs = list(dirs)
    for segment in segments(command):
        segment_dirs(segment, dirs)
        writes: list[tuple[Word, bool]] = [(word, False) for word in segment.targets]
        for words in segment.commands:
            verb, args, fed = split_command(words)
            if verb in SHELLS:                         # bash -c "...", pwsh -Command "..."
                flag = next((j for j, w in enumerate(args) if w.text.lower() in SHELL_FLAGS), None)
                if flag is not None and flag + 1 < len(args):
                    hits += command_hits(args[flag + 1].text, dirs, snap)
                continue
            if verb in EVAL_VERBS:
                hits += command_hits(" ".join(w.text for w in args), dirs, snap)
                continue
            if verb == "git":
                targets, destructive, blocked = git_writes(args, dirs, snap)
                hits += blocked
                is_write = bool(targets)
            else:
                targets, destructive, is_write = verb_writes(verb, args)
            if is_write and (fed or not targets):      # targets arrive through a pipe or (...)
                others = [w for other in segment.commands if other is not words for w in other]
                targets = [*targets, *others, *([DOT] if destructive else [])]
            writes += [(target, destructive) for target in targets]
        dotnet = DOTNET.search(segment.raw)
        if dotnet is not None:
            removing = dotnet.group(1).lower() in ("delete", "move")
            writes += [(word, removing) for word in segment.words]
        for word, destructive in writes:
            hits += target_hits(word, dirs, snap, destructive)
    return hits


def shell_hits(call: Call, snap: Snapshot) -> list[str]:
    command = call.tool_input.get("command")
    if command is None:
        return []
    if not isinstance(command, str):
        raise ValueError("command is not a string")
    return command_hits(command, [canonical(call.cwd)], snap)


def evaluate(payload: Mapping[str, object], project_dir: str | None) -> list[str]:
    tool, tool_input = payload.get("tool_name", ""), payload.get("tool_input") or {}
    cwd = payload.get("cwd") or os.getcwd()
    if not isinstance(tool, str) or not isinstance(tool_input, dict) or not isinstance(cwd, str):
        raise ValueError("tool_name, tool_input or cwd has the wrong type")
    root = canonical(project_dir or cwd)
    snap = take_snapshot(root)
    call = Call(tool, cast(dict[str, object], tool_input), cwd, root)
    return file_hits(call, snap) + shell_hits(call, snap)


def main() -> int:
    try:
        # The call arrives as UTF-8; Windows would read it in its own code page.
        cast(io.TextIOWrapper, sys.stdin).reconfigure(encoding="utf-8")
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
        hits = evaluate(payload, os.environ.get("CLAUDE_PROJECT_DIR"))
    except Exception as exc:  # entry point: an unreadable call is not a pass
        hits = [f"could not inspect the call ({exc})"]
    if hits:
        message = ("BLOCKED by agent-cycle anti-gaming rail: " + "; ".join(sorted(set(hits)))
                   + " -- frozen pipeline artifacts. Changes go through the re-entry ladder"
                   " (dispute -> re-open the owning phase), never through the builder.")
        print(message.encode("ascii", "backslashreplace").decode("ascii"), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
