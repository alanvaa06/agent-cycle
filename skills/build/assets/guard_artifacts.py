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
  bisect, reset --hard, stash pop/apply, checkout/restore from a tree-ish
  over a protected path) are the human's. A move to another revision
  (checkout, switch, reset, read-tree, a ref update of what is checked out)
  passes only when that revision's frozen files equal HEAD's, and a rewrite
  of the working tree from HEAD or the index (checkout -f, stash, restore .)
  only when the frozen files on disk and in the index are HEAD's: git itself
  is asked, and a comparison that cannot run is a block.
- While any agent is built, git config entries, options and GIT_* variables
  that run a command or point git at another tree are the human's, and so
  are .git/hooks, config, info, HEAD and the refs.
- On Windows a write path that names a UNC share or a device is refused,
  unless the repository itself lives on that UNC path.

Shell commands are read heuristically: per command, the writing verb and its
write targets are parsed from the words; sources that are only read are not
judged. A copy into a folder is judged where it lands, an extraction by the
folder it fills, and the literal text of an echo/printf that a shell runs is
read as a command. Known blind spots (ship's diff from build_start and
ship's re-run of the suite from the committed tree cover them; the ratchet
covers build.md): a script that writes (python fix.py, python -c) or that a
shell reads from a file or the network (curl ... | sh), paths assembled in
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
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum, auto
from typing import cast

HOOK_VERSION = 3
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
# Copy/move verbs that land a source in a destination: the destination is judged, and when it is a
# folder, <destination>/<basename of each source> too (a recursive copy or a move at holder level).
COPY_VERBS = frozenset({"cp", "copy", "copy-item", "cpi", "install", "xcopy", "robocopy", "rsync",
                        "scp"})
# Copies that drop a source folder's contents into the destination, not the folder itself.
CONTENT_COPIES = frozenset({"xcopy", "robocopy"})
PS_COPIES = frozenset({"copy", "copy-item", "cpi"})
CP_RECURSIVE = re.compile(r"-[a-z]*[rRa][a-z]*|--recursive|--archive", re.IGNORECASE)
PS_RECURSE = re.compile(r"-r(?:e(?:c(?:u(?:r(?:s(?:e)?)?)?)?)?)?$", re.IGNORECASE)
TARGET_DIR_FLAG = re.compile(r"-t|--target-directory")
# cp -T: the destination is not a folder to drop the source into, it becomes the source itself.
NO_TARGET_DIR_FLAG = re.compile(r"-[a-zA-Z]*T[a-zA-Z]*|--no-target-directory")
INSTALL_DIRS_FLAG = re.compile(r"-[a-zA-Z]*d[a-zA-Z]*|--directory")
# Archive tools that unpack into a destination folder (judged at holder level), by each one's mode.
EXTRACTORS = frozenset({"tar", "bsdtar", "jar", "unzip", "7z", "7za", "7zr", "cpio",
                        "expand-archive"})
# tar's mode: the first word when it is a bundle of letters (tar xzf), else a dash option.
TAR_BUNDLE_EXTRACT = re.compile(r"[A-Za-z]*x[A-Za-z]*")
TAR_OPTION_EXTRACT = re.compile(r"--extract|--get|-[A-Za-z]*x[A-Za-z]*")
# A shell word that, run as the destination, means "the folder in effect": a trailing slash, . or ..
FOLDER_WORD = re.compile(r".*/$|(?:^|/)\.\.?$")
HERESTRING = re.compile(r"<<<\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s\"'|&;<>()]+))")
# Commands that run the text another command prints: a shell reading its standard input (a pipe, a
# <<< here-string, a <(...)), source/. and the eval verbs over a <(...), $(...) or backticks. Only
# an echo/printf is read as that text: literal words are rescanned, text that cannot be read (a $,
# a backtick, a printf format, a backslash escape) is refused while an agent is built. Any other
# producer (cat, curl, base64) is a script the hook cannot see, like `sh script.sh`.
SOURCE_VERBS = frozenset({"source", "."})
INLINE_PRODUCERS = frozenset({"echo", "printf"})
STDIN_FILES = frozenset({"-", "/dev/stdin", "/dev/fd/0", "/proc/self/fd/0"})
SUBSTITUTION = re.compile(r"<\(|\$\(|`")
ECHO_FLAG = re.compile(r"-[neE]+")
# git: global options that take a value; verbs that rewrite the tree (the human's once built).
GIT_VALUE_OPTIONS = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env"})
GIT_TREE_VERBS = frozenset({"apply", "am", "revert", "cherry-pick", "merge", "pull", "rebase", "bisect",
                            "sparse-checkout"})
STASH_ACTIONS = frozenset({"push", "save", "pop", "apply", "branch", "drop", "list", "show", "clear",
                           "create", "store"})
STASH_RESTORES = frozenset({"pop", "apply", "branch"})
# git subcommands that write the working tree whole from the index or another commit: the human's.
GIT_OWNER_VERBS = frozenset({"checkout-index", "filter-branch", "filter-repo"})
GIT_HARD_RESET = re.compile(r"--(?:hard|keep|merge)$")
# checkout/switch options that throw local changes away: the tree is rewritten from HEAD.
GIT_DISCARD = re.compile(r"-f|--force|--discard-changes")
# Options that take a value, per subcommand: the value is not an operand.
GIT_VALUED: dict[str, re.Pattern[str]] = {
    "update-ref": re.compile(r"-m"),
    "symbolic-ref": re.compile(r"-m"),
    "worktree": re.compile(r"-b|-B|--reason"),
    "submodule": re.compile(r"-b|--branch|--reference|--name|--depth"),
    "clone": re.compile(r"-b|--branch|-o|--origin|-u|--upload-pack|--reference|--reference-if-able"
                        r"|--separate-git-dir|--depth|--shallow-since|--shallow-exclude|-c|--config"
                        r"|--template|-j|--jobs|--filter|--bundle-uri|--server-option|--revision"),
    "init": re.compile(r"-b|--initial-branch|--template|--separate-git-dir|--object-format|--ref-format"),
}
# A -c key / git config key that runs a command or points git at another tree, hook or index.
GIT_CONFIG_OWNED = re.compile(
    r"alias\."
    r"|core\.(?:worktree|hookspath|fsmonitor|pager|editor|sshcommand|askpass)$"
    r"|filter\..+\.(?:smudge|clean|process)$"
    r"|diff\.(?:external$|.+\.(?:textconv|command)$)"
    r"|merge\..+\.driver$"
    r"|(?:include\.path$|includeif\.)"
    r"|sequence\.editor$"
    r"|pager\."
    r"|credential\.(?:.+\.)?helper$"
    r"|gpg\.(?:.+\.)?program$"
    r"|core\.gitproxy$"
    r"|(?:difftool|mergetool)\..+\.cmd$"
    r"|init\.templatedir$", re.IGNORECASE)
# Entries whose value is a program: a known viewer or editor with dash options (cat, less -FRX,
# true) is free. Any other name is not: an interpreter would run the file git hands it.
GIT_CONFIG_PROGRAM = re.compile(r"core\.(?:pager|editor)|pager\..+|sequence\.editor", re.IGNORECASE)
PLAIN_PROGRAM = re.compile(
    r"(?:true|false|cat|less|more|vi|vim|nvim|nano|emacs|code|notepad|ed|)(?: --?[A-Za-z-]+)*|:")
# git config: forms that only read, forms that write, options that take a value.
GIT_CONFIG_READ_FLAG = re.compile(r"--get(?:-all|-regexp|-urlmatch|-color|-colorbool)?|-l|--list")
GIT_CONFIG_READ_ACTIONS = frozenset({"get", "list"})
GIT_CONFIG_WRITE_FLAG = re.compile(r"--add|--replace-all|--unset|--unset-all|--rename-section"
                                   r"|--remove-section|-e|--edit")
GIT_CONFIG_WRITE_ACTIONS = frozenset({"set", "unset", "rename-section", "remove-section", "edit"})
GIT_CONFIG_VALUED = re.compile(r"-f|--file|--blob|-t|--type|--default|--comment|--value")
# Environment variables that do what the options above do: point git at another tree, index,
# config or program. Judged on any unquoted NAME=value word (a prefix, export, env, $env:).
GIT_ENV_OWNED = re.compile(
    r"(?:\$env:)?(GIT_DIR|GIT_WORK_TREE|GIT_INDEX_FILE|GIT_COMMON_DIR|GIT_OBJECT_DIRECTORY"
    r"|GIT_ALTERNATE_OBJECT_DIRECTORIES|GIT_NAMESPACE|GIT_CONFIG(?!_NOSYSTEM)\w*|GIT_EXTERNAL_DIFF"
    r"|GIT_SSH|GIT_SSH_COMMAND|GIT_ASKPASS|GIT_PROXY_COMMAND|GIT_EXEC_PATH|GIT_TEMPLATE_DIR)=",
    re.IGNORECASE)
GIT_ENV_PROGRAM = re.compile(r"(?:\$env:)?(GIT_EDITOR|GIT_SEQUENCE_EDITOR|GIT_PAGER)=(.*)",
                             re.IGNORECASE | re.DOTALL)
# .git internals that run commands, redirect git or say what is checked out: hooks, config, info,
# a submodule's config, HEAD and the refs.
GITDIR_PROTECTED = re.compile(
    r"(?:^|/)\.git/(?:hooks/|config$|info/|modules/.+/config$|HEAD$|packed-refs$|refs/)", re.IGNORECASE)
GIT_SUBPROCESS_TIMEOUT = 3


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


def win_unsafe_path(raw: str, base: str, root: str) -> bool:
    """On Windows, a write path naming a UNC share or a device: realpath keeps its form, so the
    guard cannot canonicalise it and compare it with a drive path. It is refused as unsafe rather
    than judged, unless the repository itself lives on a UNC path and this is one of its files."""
    if os.name != "nt" or DEVICE_OR_UNC.match(raw) is None:
        return False
    if DEVICE_OR_UNC.match(root) is None:
        return True
    return rel_to_repo(canonical(os.path.join(base, raw.replace("\\", "/"))), root) is None


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
    # While an agent is built, .git internals that run commands or redirect git are the human's.
    if snap.any_built and GITDIR_PROTECTED.search(rel):
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
        if alternate_stream(raw) or win_unsafe_path(raw, call.cwd, snap.root):
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
    if verb == "install":
        if any(INSTALL_DIRS_FLAG.fullmatch(w.text) for w in args if not w.quoted):
            return [w for w in args if not (w.text.startswith("-") and len(w.text) > 1)], False, True
        return cp_target(args), False, True
    if verb == "scp":
        return [w for w in args if not (w.text.startswith("-") and len(w.text) > 1)][-1:], False, True
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


# --- git comparisons (only run for a tree-moving verb while an agent is built)

class Cmp(Enum):
    """What comparing the frozen files of two sides of a repository found."""
    SAME = auto()
    DIFFER = auto()
    NO_REPO = auto()      # not a git repository: there is nothing for git to rewrite
    UNKNOWN = auto()      # git could not run, or a side could not be read: never a pass


def run_git(root: str, args: Sequence[str]) -> subprocess.CompletedProcess[str] | None:
    """The finished git process, or None when git cannot run (missing, timed out)."""
    try:
        return subprocess.run(["git", "-C", root, *args], capture_output=True, encoding="utf-8",
                              errors="replace", timeout=GIT_SUBPROCESS_TIMEOUT, check=False)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def git_code(root: str, args: Sequence[str]) -> int | None:
    done = run_git(root, args)
    return None if done is None else done.returncode


def repo_state(root: str) -> Cmp | None:
    """NO_REPO outside a repository, UNKNOWN when git could not run, None inside one."""
    code = git_code(root, ["rev-parse", "--git-dir"])
    if code is None:
        return Cmp.UNKNOWN
    return None if code == 0 else Cmp.NO_REPO


def frozen_whole(snap: Snapshot) -> list[str]:
    """Paths of built agents that no build step changes: evals and design always, the spec and the
    build record once the build is no longer a draft."""
    paths: list[str] = []
    for agent in snap.agents:
        if agent.built:
            paths += [agent.folder + EVALS_DIR, agent.folder + DESIGN_MD]
            if agent.status != "draft":
                paths += [agent.folder + SPEC_MD, agent.folder + BUILD_MD]
    return paths


def draft_specs(snap: Snapshot) -> list[str]:
    """Specs whose Test column a draft build may still fill: compared cell by cell."""
    return [agent.folder + SPEC_MD for agent in snap.agents if agent.status == "draft"]


def side_text(root: str, side: str | None, path: str) -> str | None:
    """A file's text on one side: a revision, "" for the index, None for the working tree. None
    when the file is absent there; raises Unreadable when it cannot be read."""
    if side is None:
        return read_text(os.path.join(root, path))
    done = run_git(root, ["show", f"{side}:./{path}"])
    if done is None:
        raise Unreadable("git could not run")
    return done.stdout.replace("\r\n", "\n").removeprefix("\ufeff") if done.returncode == 0 else None


def compare(snap: Snapshot, diff_args: Sequence[str], whole: Sequence[str],
            left: str | None, right: str | None) -> Cmp:
    """Compare two sides of the repository (as `git diff <diff_args>` names them; `left`/`right`
    name the same sides for side_text): the `whole` paths byte for byte, each draft spec outside
    its Test column. Assumes a repository."""
    root, specs = snap.root, draft_specs(snap)
    code = git_code(root, ["diff", "--quiet", *diff_args, "--", *whole, *specs])
    if code == 0:
        return Cmp.SAME
    if code != 1:
        return Cmp.UNKNOWN
    code = git_code(root, ["diff", "--quiet", *diff_args, "--", *whole])
    if code != 0:
        return Cmp.DIFFER if code == 1 else Cmp.UNKNOWN
    try:
        for path in specs:
            old, new = side_text(root, left, path), side_text(root, right, path)
            if old != new and (old is None or new is None or not only_test_cells(old, new)):
                return Cmp.DIFFER
    except Unreadable:
        return Cmp.UNKNOWN
    return Cmp.SAME


def rev_state(snap: Snapshot, rev: str) -> Cmp:
    """HEAD against a revision: the guard folder, the settings and the built agents' frozen files."""
    return compare(snap, ["HEAD", rev], [HOOKS_DIR, *SETTINGS, *frozen_whole(snap)], "HEAD", rev)


def frozen_at_rest(snap: Snapshot) -> Cmp:
    """SAME when the frozen files on disk and in the index are HEAD's: a git command that rewrites
    the working tree from HEAD or the index then changes none of them, whatever moved HEAD. The
    ratchet (the hook updates it) and the settings (free keys may change) are left out."""
    outside = repo_state(snap.root)
    if outside is not None:
        return outside
    steady = [HOOKS_DIR, ":(exclude)" + RATCHET, *frozen_whole(snap)]
    on_disk = compare(snap, ["HEAD"], steady, "HEAD", None)
    return on_disk if on_disk is not Cmp.SAME else compare(snap, ["--cached", "HEAD"], steady, "HEAD", "")


def tree_write_block(snap: Snapshot, what: str) -> list[str]:
    """The owner-only block for a git command that rewrites the working tree from HEAD or the index."""
    state = frozen_at_rest(snap)
    if state in (Cmp.SAME, Cmp.NO_REPO):
        return []
    if state is Cmp.DIFFER:
        return [f"{what} would rewrite frozen files: on disk or in the index they differ from HEAD "
                "(the human runs it)"]
    return [f"{what}: git could not compare the frozen files with HEAD (the human runs it)"]


def rev_target_block(snap: Snapshot, sub: str, target: str) -> list[str]:
    """The owner-only block for a verb that moves HEAD, the branch or the index/tree to `target`:
    none when its frozen files equal HEAD's or this is not a repository, a block when they differ
    or cannot be compared."""
    state = repo_state(snap.root)
    if state is None:
        mapped = "@{-1}" if target == "-" else target
        state = rev_state(snap, mapped)
        if state is Cmp.UNKNOWN and "/" not in mapped:
            state = rev_state(snap, "origin/" + mapped)
    if state in (Cmp.SAME, Cmp.NO_REPO):
        return []
    if state is Cmp.DIFFER:
        return [f"git {sub} {target} moves to a revision whose frozen files differ from HEAD "
                "(the human runs it)"]
    return [f"git {sub} {target}: its tree cannot be compared with HEAD (the human runs it)"]


def resolve_commit(root: str, word: str) -> str | None:
    """The form of `word` that names a commit, read as git does (itself, then origin/<word>, and -
    as @{-1}); None when none resolves. Tells a one-word checkout from a pathspec."""
    candidates = ["@{-1}"] if word in ("-", "@{-1}") else [word, "origin/" + word]
    for candidate in candidates:
        if git_code(root, ["rev-parse", "--verify", "-q", candidate + "^{commit}"]) == 0:
            return candidate
    return None


def moves_head(root: str, ref: str) -> bool:
    """Does writing `ref` move what is checked out: HEAD itself or the branch it points at. True
    when git cannot say."""
    if ref == "HEAD":
        return True
    done = run_git(root, ["symbolic-ref", "-q", "HEAD"])
    if done is None:
        return True
    return done.returncode == 0 and done.stdout.strip() == ref


def git_toplevel(folder: str) -> str | None:
    done = run_git(folder, ["rev-parse", "--show-toplevel"])
    if done is None or done.returncode != 0:
        return None
    return os.path.normcase(canonical(done.stdout.strip()))


def elsewhere(snap: Snapshot, dirs: Sequence[str]) -> bool:
    """The git command runs in another repository than the project's (git -C x, cd x): its
    revisions and its tree are not this repository's."""
    here = dirs[-1]
    if os.path.normcase(here) == os.path.normcase(snap.root):
        return False
    top = git_toplevel(here)
    return top is not None and top != git_toplevel(snap.root)


def git_operands(rest: Sequence[Word], valued: re.Pattern[str] | None = None) -> list[Word]:
    """The path words of a git subcommand: neither an option, an option's value, nor `--`."""
    out: list[Word] = []
    for i, word in enumerate(rest):
        if word.text == "--" or word.text.startswith("-"):
            continue
        if valued is not None and i > 0 and valued.fullmatch(rest[i - 1].text):
            continue
        out.append(word)
    return out


def git_tree_and_paths(sub: str, before: Sequence[Word], after: Sequence[Word],
                       dashdash: bool, snap: Snapshot) -> tuple[bool, list[Word], bool, str | None]:
    """(reads from another commit, pathspec, full move with no pathspec, source revision) of
    git checkout / restore."""
    tree, positional, source = False, [], None
    i = 0
    while i < len(before):
        text = before[i].text
        if sub == "restore" and text in ("--source", "-s"):
            source = before[i + 1].text if i + 1 < len(before) else None
            tree, i = True, i + 2
            continue
        if sub == "restore" and text.startswith("--source="):
            source, tree = text.split("=", 1)[1], True
        elif sub == "restore" and text.startswith("-s") and len(text) > 2:
            source, tree = text[2:], True
        elif not text.startswith("-") or text == "-":
            positional.append(before[i])
        i += 1
    if sub == "restore":
        return tree, positional + list(after), False, source
    if dashdash:
        src = positional[0].text if positional else None
        paths = positional[1:] + list(after)
        return src is not None, paths, src is not None and not paths, src
    if len(positional) >= 2:
        return True, positional[1:], False, positional[0].text
    if len(positional) == 1 and snap.any_built and resolve_commit(snap.root, positional[0].text) is not None:
        return True, [], True, positional[0].text
    return False, positional, False, None       # one word that is not a commit: judged as a path


def config_entry_owned(key: str, value: str | None) -> bool:
    """A config entry that runs a command or redirects git. An editor or pager entry set to a
    plain program name (cat, less -FRX, true) is not."""
    if not GIT_CONFIG_OWNED.search(key):
        return False
    return not (GIT_CONFIG_PROGRAM.fullmatch(key) and value is not None and PLAIN_PROGRAM.fullmatch(value))


def git_config_writes(rest: Sequence[Word], snap: Snapshot) -> tuple[list[Word], bool, list[str]]:
    """git config: a read is free; a write of an owned key is the human's while an agent is built;
    a write to a named file (-f/--file) is a write on that file."""
    operands = git_operands(rest, GIT_CONFIG_VALUED)
    flags = [w.text for w in rest if w.text.startswith("-")]
    writing = any(GIT_CONFIG_WRITE_FLAG.fullmatch(f) for f in flags)
    if any(GIT_CONFIG_READ_FLAG.fullmatch(f) for f in flags) or not operands \
            or operands[0].text.lower() in GIT_CONFIG_READ_ACTIONS or (len(operands) == 1 and not writing):
        return [], False, []
    key = operands[1].text if operands[0].text.lower() in GIT_CONFIG_WRITE_ACTIONS and len(operands) > 1 \
        else operands[0].text
    if GIT_CONFIG_OWNED.search(key) and snap.any_built:
        return [], False, [f"git config {key} sets an entry that can run a command or redirect git"]
    files = [rest[k + 1] for k, w in enumerate(rest[:-1]) if w.text in ("-f", "--file")]
    files += [Word(w.text.split("=", 1)[1], w.quoted) for w in rest if w.text.startswith("--file=")]
    return files, False, []


def git_writes(args: Sequence[Word], dirs: list[str], snap: Snapshot) -> tuple[list[Word], bool, list[str]]:
    """(write targets, destructive, outright blocks) of one git command."""
    i, rerouted = 0, False
    config_sets: list[tuple[str, str | None]] = []
    while i < len(args) and args[i].text.startswith("-"):
        text = args[i].text
        if text in ("-c", "--config-env") and i + 1 < len(args):
            key, _, value = args[i + 1].text.partition("=")
            config_sets.append((key, value if text == "-c" else None))
            i += 2
            continue
        if text.startswith("--config-env="):
            config_sets.append((text.split("=", 2)[1], None))
        if text.startswith(("--git-dir", "--work-tree", "--exec-path=")):
            rerouted = True
        i += 2 if text in GIT_VALUE_OPTIONS else 1
    if i >= len(args):
        return [], False, []
    sub, rest = args[i].text.lower(), args[i + 1:]
    texts = [w.text for w in rest]
    dashdash = "--" in texts
    before = rest[:texts.index("--")] if dashdash else rest
    after = rest[texts.index("--") + 1:] if dashdash else ()
    flags = [w.text for w in before if w.text.startswith("-")]

    def owner(text: str) -> list[str]:
        return [text] if snap.any_built else []

    def foreign() -> bool:
        return elsewhere(snap, dirs)

    human = owner(f"git {sub} while an agent is built (the human runs it)")
    # A --git-dir/--work-tree/--exec-path, or a -c/--config-env that sets a command-running or
    # tree-redirecting config entry, points git at another tree or program: the human's while an
    # agent is built.
    if rerouted and snap.any_built:
        return [], False, [f"git {sub} with a --git-dir, --work-tree or --exec-path option points at "
                           "another tree or program (the human runs it)"]
    owned_c = next((key for key, value in config_sets if config_entry_owned(key, value)), None)
    if owned_c is not None:
        return [], False, owner(f"git -c {owned_c} sets an entry that can run a command or redirect git")
    if sub == "config":
        return git_config_writes(rest, snap)
    if sub in ("rm", "mv"):
        return [w for w in rest if not w.text.startswith("-")], True, []
    if sub == "clean":                 # path-less: the current directory
        paths = list(after) or [w for k, w in enumerate(before) if not w.text.startswith("-")
                                and (k == 0 or before[k - 1].text not in ("-e", "--exclude"))]
        if any(w.text.startswith(":") for w in paths):
            return [], False, owner("git clean with a magic pathspec can reach across the repository")
        return paths or [DOT], True, []
    if sub == "stash":
        words = [w for k, w in enumerate(before) if not w.text.startswith("-")
                 and (k == 0 or before[k - 1].text not in ("-m", "--message"))]
        action = words[0].text.lower() if words and words[0].text.lower() in STASH_ACTIONS else "push"
        if action in STASH_RESTORES:
            return [], False, human
        if action not in ("push", "save"):
            return [], False, []
        # push takes a pathspec; save takes a message
        paths = [] if action == "save" else list(after) or [w for w in words if w.text.lower() != "push"]
        if any(w.text.startswith(":") for w in paths):
            return [], False, owner("git stash with a magic pathspec can reach across the repository")
        # a stash puts the stashed paths back to HEAD
        if snap.any_built and not foreign() and (
                not paths or any(target_hits(w, dirs, snap, destructive=True) for w in paths)):
            blocked = tree_write_block(snap, "git stash")
            if blocked:
                return [], False, blocked
        untracked = any(f in ("--include-untracked", "--all") or re.fullmatch(r"-[a-zA-Z]*[ua][a-zA-Z]*", f)
                        for f in flags)
        return (list(after) or [DOT]) if untracked else list(after), untracked, []
    if sub == "reset":
        if any(GIT_HARD_RESET.fullmatch(f) for f in flags):
            return [DOT], True, human
        if not snap.any_built:
            return [], False, []
        if foreign():
            return [DOT], False, []
        non_flag = [w for w in before if not w.text.startswith("-")]
        commit = (non_flag[0].text if non_flag and resolve_commit(snap.root, non_flag[0].text) is not None
                  else "HEAD")
        return [], False, rev_target_block(snap, sub, commit)
    if sub == "switch":
        if not snap.any_built:
            return [], False, []
        if foreign():
            return [DOT], False, []
        if any(GIT_DISCARD.fullmatch(t) for t in texts):
            blocked = tree_write_block(snap, "git switch --force")
            if blocked:
                return [], False, blocked
        positional = [w for w in rest if w.text == "-" or not w.text.startswith("-")]
        create = any(re.fullmatch(r"-c|-C|--create", w.text) for w in rest)
        target = (positional[1].text if len(positional) >= 2 else None) if create \
            else (positional[0].text if positional else None)
        return ([], False, rev_target_block(snap, sub, target)) if target is not None else ([], False, [])
    if sub in ("checkout", "restore"):
        if any(re.fullmatch(r"-p|--patch|--pathspec-from-file(=.*)?", t) for t in texts):
            return [], False, owner(f"git {sub} -p/--patch or --pathspec-from-file can rewrite frozen files")
        if snap.any_built and foreign():
            return [DOT], False, []
        if sub == "checkout" and snap.any_built and any(GIT_DISCARD.fullmatch(f) for f in flags):
            blocked = tree_write_block(snap, "git checkout --force")
            if blocked:
                return [], False, blocked
        if sub == "checkout":           # checkout -b/-B/--orphan <name> [<start>]: the start moves the tree
            at = next((k for k, w in enumerate(rest) if w.text in ("-b", "-B", "--orphan")), None)
            if at is not None:
                non_flag = [w for w in rest[at + 1:] if w.text != "--" and not w.text.startswith("-")]
                start = non_flag[1].text if len(non_flag) >= 2 else None
                if start is not None and snap.any_built:
                    return [], False, rev_target_block(snap, sub, start)
                return [], False, []
        tree, pathspec, full, source = git_tree_and_paths(sub, before, after, dashdash, snap)
        reaches = any(w.text.startswith(":") or target_hits(w, dirs, snap, destructive=True) for w in pathspec)
        if full and source is not None and snap.any_built:
            return [], False, rev_target_block(snap, sub, source)
        if tree and snap.any_built and reaches:
            return [], False, [f"git {sub} from another commit over protected paths while an agent is "
                               "built (the human runs it)"]
        # from the index into the working tree: the human's unless the frozen files are HEAD's
        if not tree and snap.any_built and reaches:
            blocked = tree_write_block(snap, f"git {sub}")
            if blocked:
                return [], False, blocked
        return pathspec, False, []
    if sub == "read-tree":
        if not snap.any_built:
            return [], False, []
        if foreign():
            return [DOT], False, []
        trees = [w for w in rest if not w.text.startswith("-")]
        blocked = rev_target_block(snap, sub, trees[0].text) if trees else []
        if not blocked and any(re.fullmatch(r"-u|--reset", t) for t in texts):
            blocked = tree_write_block(snap, "git read-tree -u")
        return [], False, blocked
    if sub == "update-ref":
        if not snap.any_built or foreign():
            return [], False, []
        if "--stdin" in texts:
            return [], False, ["git update-ref --stdin moves refs named on its input (the human runs it)"]
        vals = git_operands(rest, GIT_VALUED[sub])
        if len(vals) >= 2 and moves_head(snap.root, vals[0].text):
            return [], False, rev_target_block(snap, sub, vals[1].text)
        return [], False, []
    if sub == "symbolic-ref":
        if not snap.any_built or foreign():
            return [], False, []
        vals = git_operands(rest, GIT_VALUED[sub])
        if len(vals) >= 2 and vals[0].text == "HEAD":
            return [], False, rev_target_block(snap, sub, vals[1].text)
        return [], False, []
    if sub == "branch":
        if not snap.any_built or not any(re.fullmatch(r"-f|--force|-M|-C", w.text) for w in rest) or foreign():
            return [], False, []
        vals = git_operands(rest)
        if len(vals) >= 2 and moves_head(snap.root, "refs/heads/" + vals[0].text):
            return [], False, rev_target_block(snap, sub, vals[1].text)
        return [], False, []
    if sub == "fetch":
        if any(re.fullmatch(r"-[a-zA-Z]*u[a-zA-Z]*|--update-head-ok", f) for f in flags):
            return [], False, owner("git fetch --update-head-ok can move the checked-out branch "
                                    "(the human runs it)")
        return [], False, []
    if sub == "replace":
        if git_operands(rest) or any(re.fullmatch(r"-d|--delete|--graft|--edit|--convert-graft-file", f)
                                     for f in flags):
            return [], False, owner("git replace changes what a revision names (the human runs it)")
        return [], False, []
    if sub == "update-index":
        flag = next((w.text for w in rest if re.fullmatch(r"--cacheinfo|--index-info|--add", w.text)), None)
        if flag is None:
            return [], False, []
        if flag == "--index-info":
            return [], False, owner("git update-index --index-info stages paths from stdin (the human runs it)")
        return git_operands(rest), True, []
    if sub == "worktree":
        operands = git_operands(rest, GIT_VALUED[sub])
        return (operands[1:2], True, []) if operands and operands[0].text.lower() == "add" else ([], False, [])
    if sub == "submodule":
        operands = git_operands(rest, GIT_VALUED[sub])
        return (operands[2:3], True, []) if operands and operands[0].text.lower() == "add" else ([], False, [])
    if sub == "clone":
        operands = git_operands(rest, GIT_VALUED[sub])
        return (operands[1:2], True, []) if len(operands) >= 2 else ([], False, [])
    if sub == "init":
        operands = git_operands(rest, GIT_VALUED[sub])
        return (operands[:1], True, []) if operands else ([], False, [])
    if sub in GIT_OWNER_VERBS:
        return [], False, owner(f"git {sub} writes the working tree from the index or another commit")
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
            if win_unsafe_path(text, folder, snap.root):
                hits.append("unsafe path " + text)
                continue
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


def basename_of(text: str) -> str:
    """The last path component of a shell word (slashes already '/'); '' when empty."""
    return text.rstrip("/").rsplit("/", 1)[-1]


def ps_destination(verb: str, text: str) -> tuple[bool, str | None]:
    """(is a PowerShell -Destination flag in any abbreviation, its attached -Destination:value)."""
    name, colon, _ = text.lower().partition(":")
    if verb not in PS_COPIES or len(name) < 2 or not any(flag.startswith(name) for flag in DEST_FLAGS):
        return False, None
    return True, text[len(name) + 1:] if colon else None


def copy_landing(verb: str, args: Sequence[Word], dirs: list[str]) -> list[tuple[Word, bool]]:
    """Where a copy lands besides the destination word itself: when the destination is a folder,
    <destination>/<basename of each source>, judged at holder level for a recursive copy or a
    glob. A recursive copy that would create the destination, or a copy of a folder's contents
    (xcopy, robocopy, cp -T, an rsync source ending in /), judges the destination itself at holder
    level too. Reading a source is never judged here."""
    if verb not in COPY_VERBS:
        return []
    dest: Word | None = None
    flagged = False
    recursive = verb in CONTENT_COPIES
    content = verb in CONTENT_COPIES
    operands: list[Word] = []
    i = 0
    while i < len(args):
        word = args[i]
        text = word.text
        if not word.quoted:
            ps_flag, attached = ps_destination(verb, text)
            if attached is not None:
                dest = Word(attached, quoted=False)
                i += 1
                continue
            if (TARGET_DIR_FLAG.fullmatch(text) or ps_flag) and i + 1 < len(args):
                dest = args[i + 1]
                flagged = flagged or TARGET_DIR_FLAG.fullmatch(text) is not None
                i += 2
                continue
            if text.startswith("--target-directory="):
                dest, flagged = Word(text.split("=", 1)[1], word.quoted), True
                i += 1
                continue
            if CP_RECURSIVE.fullmatch(text) or PS_RECURSE.fullmatch(text):
                recursive = True
            if verb == "cp" and NO_TARGET_DIR_FLAG.fullmatch(text):
                content = True
            if (text.startswith("-") and len(text) > 1) or CMD_FLAG.fullmatch(text):
                i += 1
                continue
        operands.append(word)
        i += 1
    if dest is None:
        if verb in ("robocopy", "xcopy"):
            dest, sources = (operands[1], operands[:1]) if len(operands) >= 2 else (None, [])
        elif len(operands) == 1 and verb in ("copy-item", "cpi"):
            dest, flagged, sources = DOT, True, operands
        elif len(operands) >= 2:
            dest, sources = operands[-1], operands[:-1]
        else:
            dest, sources = None, []
    else:
        sources = operands
    if dest is None:
        return []
    base = dest.text
    on_disk = any(os.path.isdir(p) for folder in dirs for p in shell_paths(base, folder))
    content = content or (verb == "rsync" and any(source.text.endswith("/") for source in sources))
    extra: list[tuple[Word, bool]] = []
    if content or (recursive and not on_disk):
        extra.append((Word(base, quoted=True), True))
    folder_dest = flagged or FOLDER_WORD.match(base) is not None or on_disk or len(sources) > 1
    if folder_dest:
        stem = base.rstrip("/") or base
        for source in sources:
            name = basename_of(source.text)
            if not name:
                continue
            if GLOB.search(name):
                extra.append((Word(stem + "/*", quoted=True), True))
            else:
                extra.append((Word(stem + "/" + name, quoted=True), recursive))
    return extra


def is_extracting(verb: str, args: Sequence[Word]) -> bool:
    texts = [a.text for a in args]
    if verb == "expand-archive":
        return True
    if verb == "unzip":
        return not any(re.match(r"-[ltvz]", t, re.IGNORECASE) for t in texts)
    if verb in ("7z", "7za", "7zr"):
        return any(re.fullmatch(r"[xe]", t, re.IGNORECASE) for t in texts)
    if verb == "cpio":
        return any(re.match(r"--extract$|-[a-z]*i", t, re.IGNORECASE) for t in texts)
    # tar, bsdtar, jar: an x in the mode, never in an operand (tar cf a.tar index creates)
    return (bool(texts) and TAR_BUNDLE_EXTRACT.fullmatch(texts[0]) is not None) \
        or any(TAR_OPTION_EXTRACT.fullmatch(t) for t in texts)


def extract_dest(verb: str, args: Sequence[Word]) -> str:
    """The folder an extraction fills: a -C/-d/-o/--directory/-DestinationPath value, separate or
    attached, else '.', the folder in effect, into which the archive unpacks."""
    tar = verb in ("tar", "bsdtar")
    seven = verb in ("7z", "7za", "7zr")
    for i, word in enumerate(args):
        text = word.text
        if tar and (text == "-C" or re.fullmatch(r"--directory", text, re.IGNORECASE)) and i + 1 < len(args):
            return args[i + 1].text
        if verb == "unzip" and text == "-d" and i + 1 < len(args):
            return args[i + 1].text
        if verb == "expand-archive" and re.fullmatch(r"-destinationpath", text, re.IGNORECASE) \
                and i + 1 < len(args):
            return args[i + 1].text
        attached = ((tar and re.fullmatch(r"-C(.+)", text))
                    or (tar and re.fullmatch(r"--directory=(.+)", text, re.IGNORECASE))
                    or (verb == "unzip" and re.fullmatch(r"-d(.+)", text))
                    or (seven and re.fullmatch(r"-o(.+)", text, re.IGNORECASE))
                    or (verb == "expand-archive" and re.fullmatch(r"-destinationpath[:=](.+)", text, re.IGNORECASE)))
        if attached:
            return attached.group(1)
    return "."


def extraction_writes(verb: str, args: Sequence[Word]) -> list[tuple[Word, bool]]:
    if verb not in EXTRACTORS or not is_extracting(verb, args):
        return []
    return [(Word(extract_dest(verb, args), quoted=True), True)]


def reads_stdin_script(verb: str, args: Sequence[Word]) -> bool:
    """A shell that runs its standard input as a script: no -c/-Command and no script-file word
    other than a name for standard input itself."""
    if verb not in SHELLS:
        return False
    for word in args:
        if word.text.lower() in SHELL_FLAGS:
            return False
        if not word.text.startswith("-") and word.text not in STDIN_FILES:
            return False
    return True


def runs_substitution(verb: str, args: Sequence[Word]) -> bool:
    """A command that runs what a <(...), $(...) or backtick substitution prints."""
    return verb in SOURCE_VERBS or verb in EVAL_VERBS or reads_stdin_script(verb, args)


def producer_script(words: Sequence[Word], escaped: bool) -> tuple[str | None, bool]:
    """(script to rescan, unreadable) of a command whose output a shell runs. An echo/printf of
    literal words prints them; one whose text cannot be known here (a $ or a backtick, a printf
    format, a backslash escape somewhere in the command) is unreadable. Any other producer is
    neither: (None, False)."""
    verb, args, _ = split_command(words)
    if verb not in INLINE_PRODUCERS:
        return None, False
    vals = [w for w in args if w.quoted or not ECHO_FLAG.fullmatch(w.text)]
    if escaped or any("$" in w.text or "`" in w.text for w in vals) \
            or (verb == "printf" and bool(vals) and "%" in vals[0].text):
        return None, True
    return " ".join(w.text for w in vals), False


def git_env_hits(words: Sequence[Word]) -> list[str]:
    """Blocks for words that set an environment variable redirecting git or naming a program it
    runs (an editor or pager set to a plain program name is free)."""
    hits: list[str] = []
    for word in words:
        if word.quoted:
            continue
        owned, program = GIT_ENV_OWNED.match(word.text), GIT_ENV_PROGRAM.fullmatch(word.text)
        name = owned.group(1) if owned else (
            program.group(1) if program and not PLAIN_PROGRAM.fullmatch(program.group(2)) else None)
        if name is not None:
            hits.append(f"{name.upper()} points git at another tree, config or program (the human runs it)")
    return hits


def command_hits(command: str, dirs: list[str], snap: Snapshot, escaped: bool = False,
                 substituted: bool = False) -> list[str]:
    """Why the command would touch a protected path. `escaped`: an enclosing command held a
    backslash, so the text an echo/printf prints is not the text read here. `substituted`: the
    command is eval's argument, so what its $(...) prints is run."""
    command = re.sub(r"\\\r?\n|`\r?\n", "", command)       # line continuations
    escaped = escaped or "\\" in command
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
        parsed = [split_command(c) for c in segment.commands]
        herestring_shell = any(
            verb in SHELLS and not any(w.text.lower() in SHELL_FLAGS for w in args)
            for verb, args, _ in parsed)
        # The echo/printf commands whose output this segment runs: the stage piped into a shell
        # that reads its standard input, and every one inside a substitution that a shell,
        # source/. or eval runs (also when eval's own argument is that substitution).
        stdin_shells = [idx for idx, (verb, args, _) in enumerate(parsed)
                        if idx > 0 and reads_stdin_script(verb, args)]
        produced = {idx - 1 for idx in stdin_shells}
        # An echo/printf further up the pipe reaches the shell through another command (cat, rev,
        # base64 -d): what arrives is not the text read here.
        if snap.any_built and any(verb in INLINE_PRODUCERS
                                  for idx in stdin_shells for verb, _, _ in parsed[:idx - 1]):
            hits.append("a shell runs the output of an echo/printf passed through another command")
        if SUBSTITUTION.search(segment.raw) and (
                substituted or any(runs_substitution(verb, args) for verb, args, _ in parsed)):
            produced |= {idx for idx, (verb, _, _) in enumerate(parsed) if verb in INLINE_PRODUCERS}
        for idx in sorted(produced):
            script, unreadable = producer_script(segment.commands[idx], escaped)
            if script is not None:
                hits += command_hits(script, dirs, snap, escaped)
            elif unreadable and snap.any_built:
                hits.append("a shell runs the output of an echo/printf whose text cannot be read "
                            "(a $, a backtick, a printf format or a backslash escape)")
        if snap.any_built:
            hits += git_env_hits(segment.words)
        for words, (verb, args, fed) in zip(segment.commands, parsed, strict=True):
            if verb in SHELLS:                         # bash -c "...", pwsh -Command "..."
                flag = next((j for j, w in enumerate(args) if w.text.lower() in SHELL_FLAGS), None)
                if flag is not None and flag + 1 < len(args):
                    hits += command_hits(args[flag + 1].text, dirs, snap, escaped)
                continue
            if verb in EVAL_VERBS:
                hits += command_hits(" ".join(w.text for w in args), dirs, snap, escaped, substituted=True)
                continue
            if verb == "git":
                targets, destructive, blocked = git_writes(args, dirs, snap)
                hits += blocked
                is_write = bool(targets)
            else:
                targets, destructive, is_write = verb_writes(verb, args)
                writes += copy_landing(verb, args, dirs)
                writes += extraction_writes(verb, args)
            if is_write and (fed or not targets):      # targets arrive through a pipe or (...)
                others = [w for other in segment.commands if other is not words for w in other]
                targets = [*targets, *others, *([DOT] if destructive else [])]
            writes += [(target, destructive) for target in targets]
        # A <<< here-string fed to a shell that reads its input runs as a command.
        if herestring_shell:
            for match in HERESTRING.finditer(segment.raw):
                literal = match.group(1) or match.group(2) or match.group(3) or ""
                if "$" in literal or "`" in literal:
                    if snap.any_built:
                        hits.append("a shell write built from an opaque here-string")
                elif literal:
                    hits += command_hits(literal, dirs, snap, escaped)
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
