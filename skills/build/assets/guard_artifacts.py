"""agent-cycle anti-gaming hook for Claude Code (PreToolUse).

Reads the tool call JSON on stdin; exit 2 blocks the call, exit 0 lets it
through. agent-cycle:build copies this file to <repo>/.claude/hooks/ and
registers it through $CLAUDE_PROJECT_DIR (forge-delegation.md). Upgrading it
is a human step: build never writes .claude/hooks/.

What is frozen is decided from each agent's state on disk at call time:
- Agents: the repo root ("") and every directory agents/<name>/, always --
  never from agent-cycle.yaml, so deleting, renaming or creating that file
  changes nothing. The longest matching agent owns a path.
- Once <agent>/docs/agent/build.md exists, the agent's evals/**,
  docs/agent/design.md and docs/agent/spec.md are frozen. While build.md says
  status: draft, the spec's section 6 Test column may be filled and build.md
  may be edited with file tools; shell writes never touch build.md.
- Ratchet: every agent whose build.md the hook has seen is recorded in
  .claude/hooks/built-agents.txt (one prefix per line, "." for the root). A
  recorded agent whose build.md is gone stays frozen as if its status were
  unreadable. Human re-entry: rename this file to guard_artifacts.py.off,
  make the change, remove the agent's line from built-agents.txt, rename back.
- agent-cycle.yaml is append-only; .claude/hooks/ is always protected;
  .claude/settings.json and settings.local.json must keep this hook's
  PreToolUse entry and may not set disableAllHooks.

Shell commands are read heuristically. Known blind spots (ship's diff from
build_start covers them; the ratchet covers build.md): a script that writes
(python fix.py, python -c), paths assembled in variables, backslash escapes
inside names, brace expansion, encoded commands.
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
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum, auto
from typing import cast

HOOK_VERSION = 2
HOOK_FILE = "guard_artifacts.py"
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

_GIT = r"\bgit(?:\s+(?:-C|-c|--git-dir|--work-tree)\s*\S+|\s+--[\w-]+)*\s+"
_LEAD = r"(?:^|[\s;&|(`])"
WRITE = re.compile(
    _LEAD + r"(?:tee|cp|mv|rm|rmdir|touch|truncate|del|erase|rd|move|copy|ren|rename|ri|rni"
    r"|rename-item|remove-item|move-item|mi|copy-item|cpi|set-content|sc|add-content|ac"
    r"|clear-content|clc|out-file|new-item|ni|robocopy|xcopy|ln|mklink|unlink|shred|rsync|dd)(?:\s|$)"
    + r"|" + _GIT + r"(?:checkout|restore|rm|mv|clean|reset|revert|stash|apply|am|switch"
    r"|cherry-pick|merge|pull)\b"
    r"|\bsed\b[^\n;&|]*?\s(?:-[a-zA-Z]*i|--in-place)"
    r"|\bperl\b[^\n;&|]*?\s-[a-zA-Z]*i"
    r"|\bg?awk\s+(?:[^\n;&|]*?\s)?-i\b"
    r"|\s-delete\b"
    r"|\]::(?:Write|Append|Delete|Move|Copy|Create|Replace|Open)", re.IGNORECASE)
# Removing or moving one of these takes whatever it holds along.
DESTRUCTIVE = re.compile(
    _LEAD + r"(?:rm|rmdir|mv|move|ren|rename|rename-item|ri|rni|remove-item|move-item|mi|del"
    r"|erase|rd|robocopy|unlink|shred)(?:\s|$)"
    + r"|" + _GIT + r"(?:clean|rm|mv)\b|\s-delete\b", re.IGNORECASE)
# Redirects that only move or drop a stream write no file: 2>&1, >/dev/null, 2>NUL.
FD_REDIRECT = re.compile(
    r"(?:\d|&|\*)?>>?\s*(?:/dev/null|nul|\$null)(?![\w./:-])|(?:\d|\*)?>&\s*(?:\d+|-)(?![\w.])",
    re.IGNORECASE)
CD = ("cd", "pushd", "chdir", "set-location", "sl", "push-location")
SHELLS = ("bash", "sh", "zsh", "dash", "ksh", "pwsh", "powershell", "cmd")
SHELL_FLAGS = ("-c", "-command", "/c", "/k")
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
    r"|\"(?P<dq>[^\"]*)\"|'(?P<sq>[^']*)'"
    r"|(?P<bare>[^\s\"'`;|&()<>=,]+)"
    r"|(?P<other>\S)")
GLOB = re.compile(r"[*?\[]")


class Rule(Enum):
    FREE = auto()
    FROZEN = auto()
    TEST_COLUMN_ONLY = auto()
    BUILD_DRAFT = auto()
    APPEND_ONLY = auto()
    SETTINGS = auto()


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
    holders: frozenset[str]
    frozen_dirs: tuple[str, ...]
    protected_strings: tuple[str, ...]
    protected_paths: tuple[str, ...]

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
    words: tuple[Word, ...]
    targets: tuple[Word, ...]            # redirect targets


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
    frozen_dirs = [HOOKS_DIR]
    strings = [HOOKS_DIR, ".claude/settings", MARKER]
    paths = [HOOKS_DIR, *SETTINGS, MARKER]
    for prefix in built:
        holders |= {prefix.rstrip("/"), prefix + "docs", prefix + DOCS_AGENT, prefix + EVALS_DIR}
        if prefix:
            holders.add(AGENTS_DIR)
        frozen_dirs += [prefix + EVALS_DIR, prefix + DOCS_AGENT]
        strings += [prefix + EVALS_DIR + "/", prefix + DESIGN_MD, prefix + SPEC_MD, prefix + BUILD_MD]
        paths += [prefix + EVALS_DIR, prefix + DESIGN_MD, prefix + SPEC_MD, prefix + BUILD_MD]
    return Snapshot(root, agents, frozenset(holders), tuple(frozen_dirs), tuple(strings), tuple(paths))


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


def settings_change_ok(current: str | None, new: str | None) -> bool:
    """Valid JSON that keeps every guard entry and does not disable hooks."""
    if new is None:
        return False
    try:
        proposed = json.loads(new)
    except ValueError:
        return False
    if not isinstance(proposed, dict) or proposed.get("disableAllHooks", False) is not False:
        return False
    try:
        before = guard_entries(json.loads(current)) if current else set()
    except ValueError:
        before = set()                 # an invalid file registers nothing to drop
    return before <= guard_entries(proposed)


def user_settings(path: str) -> bool:
    home = canonical(os.path.join(os.path.expanduser("~"), CLAUDE_DIR, "settings.json"))
    return os.path.normcase(path) == os.path.normcase(home)


# --- the two kinds of call

def content_change_ok(rule: Rule, call: Call, path: str, snap: Snapshot) -> bool:
    if rule is Rule.FREE or (rule is Rule.BUILD_DRAFT and call.tool in FILE_TOOLS):
        return True
    if call.tool not in FILE_TOOLS or rule not in (Rule.TEST_COLUMN_ONLY, Rule.APPEND_ONLY, Rule.SETTINGS):
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
    return settings_change_ok(current, new)


def file_hits(call: Call, snap: Snapshot) -> list[str]:
    hits: list[str] = []
    for key in ("file_path", "notebook_path"):
        raw = call.tool_input.get(key)
        if raw is None or raw == "":
            continue
        if not isinstance(raw, str):
            raise ValueError(f"{key} is not a string")
        if alternate_stream(raw):
            hits.append("unsafe path " + raw)
            continue
        path = file_tool_path(raw, call.cwd)
        rel = rel_to_repo(path, snap.root)
        if rel is None:
            if user_settings(path) and not content_change_ok(Rule.SETTINGS, call, path, snap):
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
    """Split on ; && || & and newlines (a pipeline stays one segment)."""
    found: list[Segment] = []
    words: list[Word] = []
    targets: list[Word] = []
    pieces: list[tuple[str, bool]] = []
    start, last_end, want_target = 0, -1, False

    def flush_word() -> None:
        nonlocal want_target
        if pieces:
            word = Word("".join(text for text, _ in pieces), len(pieces) == 1 and pieces[0][1])
            words.append(word)
            if want_target:
                targets.append(word)
                want_target = False
            pieces.clear()

    def flush_segment(end: int) -> None:
        nonlocal want_target
        flush_word()
        if words or targets:
            found.append(Segment(command[start:end], tuple(words), tuple(targets)))
        words.clear()
        targets.clear()
        want_target = False

    for match in TOKEN.finditer(command):
        kind = match.lastgroup
        if kind in ("dq", "sq", "bare"):
            if match.start() != last_end:
                flush_word()
            pieces.append((match.group(kind), kind != "bare"))
            last_end = match.end()
            continue
        flush_word()
        last_end = -1
        if kind == "sep":
            flush_segment(match.start())
            start = match.end()
        elif kind == "redir":
            want_target = True
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


def glob_reaches(pattern: str, target: str) -> bool:
    """Could a glob path reach target, a path inside it, or a folder holding it?"""
    return all(fnmatch.fnmatchcase(part, glob)
               for glob, part in zip(pattern.split("/"), target.split("/"), strict=False))


def word_hits(word: Word, dirs: list[str], snap: Snapshot, destructive: bool) -> list[str]:
    hits: list[str] = []
    for folder in dirs:
        for path in shell_paths(word.text, folder):
            rel = rel_to_repo(path, snap.root)
            if rel is None:
                continue
            if GLOB.search(rel):
                reach = list(snap.protected_paths)
                if destructive:
                    reach += [holder for holder in snap.holders if holder]
                hits += [f"a shell glob reaching {target}" for target in reach if glob_reaches(rel, target)]
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
        words = segment.words
        for i, word in enumerate(words[:-1]):          # bash -c "...", pwsh -Command "..."
            name = os.path.basename(word.text.lower()).removesuffix(".exe")
            if name in SHELLS:
                flag = next((j for j in range(i + 1, len(words)) if words[j].text.lower() in SHELL_FLAGS), None)
                if flag is not None and flag + 1 < len(words):
                    hits += command_hits(words[flag + 1].text, dirs, snap)
        if WRITE.search(segment.raw):
            checked = words
            destructive = DESTRUCTIVE.search(segment.raw) is not None
            for folder in dirs:                        # cd evals && rm config.yaml
                rel = rel_to_repo(folder, snap.root)
                if rel is not None and any(under(rel, d) for d in snap.frozen_dirs):
                    hits.append("a shell write from inside " + rel)
        elif segment.targets:                          # a redirect is the only write
            checked, destructive = segment.targets, False
        else:
            continue
        for word in checked:
            if not word.quoted:
                hits += [f"a shell write naming {s}" for s in snap.protected_strings if s in word.text.lower()]
            hits += word_hits(word, dirs, snap, destructive)
    return hits


def shell_hits(call: Call, snap: Snapshot) -> list[str]:
    command = call.tool_input.get("command")
    if command is None:
        return []
    if not isinstance(command, str):
        raise ValueError("command is not a string")
    return command_hits(command, [canonical(call.cwd)], snap)


def evaluate(payload: dict[str, object], project_dir: str | None) -> list[str]:
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
