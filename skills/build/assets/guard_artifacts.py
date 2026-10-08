"""agent-cycle anti-gaming hook for Claude Code (PreToolUse).

Reads the tool call JSON on stdin; exit 2 blocks the call, exit 0 lets it
through. agent-cycle:build copies this file to <repo>/.claude/hooks/ and
registers it through $CLAUDE_PROJECT_DIR (forge-delegation.md).

What is frozen is decided from each agent's state on disk at call time:
- Agent roots: the repo root when agent-cycle.yaml is absent (one agent);
  every directory agents/<name>/ when it is present (workspace).
- Once <agent>/docs/agent/build.md exists, the agent's evals/**,
  docs/agent/design.md and docs/agent/spec.md are frozen. While build.md says
  status: draft, the spec's section 6 Test column may be filled and build.md
  may be edited with file tools; shell writes never touch build.md.
- agent-cycle.yaml is append-only; .claude/hooks/ is always protected.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum, auto

HOOK_VERSION = 2
MARKER = "agent-cycle.yaml"
AGENTS_DIR = "agents"
HOOKS_DIR = ".claude/hooks"
BUILD_MD = "docs/agent/build.md"
SPEC_MD = "docs/agent/spec.md"
DESIGN_MD = "docs/agent/design.md"
DOCS_AGENT = "docs/agent"
EVALS_DIR = "evals"
FILE_TOOLS = ("Edit", "MultiEdit", "Write")
AGENT_NAME = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")

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


class Rule(Enum):
    FREE = auto()
    FROZEN = auto()
    TEST_COLUMN_ONLY = auto()
    BUILD_DRAFT = auto()
    APPEND_ONLY = auto()


@dataclass(frozen=True)
class Call:
    tool: str
    tool_input: dict[str, object]
    cwd: str
    root: str


# --- paths

def resolve(raw: str, base: str) -> str:
    path = os.path.expanduser(os.path.expandvars(str(raw))).replace("\\", "/")
    drive = re.match(r"/(?:cygdrive/|mnt/)?([a-zA-Z])(?:/|$)(.*)", path)
    if os.name == "nt" and drive:      # Git Bash /c/x means C:/x
        path = drive.group(1) + ":/" + drive.group(2)
    return os.path.normpath(os.path.join(base, path))


def rel_to_repo(raw: object, base: str, root: str) -> str | None:
    """Lower-case '/'-joined path relative to root; '' for root; None outside."""
    if not raw:
        return None
    try:
        rel = os.path.relpath(resolve(str(raw), base), os.path.normpath(root))
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
    try:
        with open(path, encoding="utf-8", newline="") as handle:
            return handle.read().replace("\r\n", "\n")
    except (OSError, UnicodeDecodeError):
        return None


def agent_prefixes(root: str) -> list[str]:
    """'' for a one-agent repo; 'agents/<name>/' per directory in a workspace."""
    if not os.path.isfile(os.path.join(root, MARKER)):
        return [""]
    base = os.path.join(root, AGENTS_DIR)
    try:
        names = sorted(n for n in os.listdir(base) if os.path.isdir(os.path.join(base, n)))
    except OSError:
        return []
    return [f"{AGENTS_DIR}/{name.lower()}/" for name in names]


def build_status(root: str, prefix: str) -> str | None:
    """None while build.md is absent; else its frontmatter status ('' if unreadable)."""
    path = os.path.join(root, prefix, BUILD_MD)
    if not os.path.isfile(path):
        return None
    text = read_text(path)
    if text is None or not text.startswith("---\n"):
        return ""
    for line in text.split("\n")[1:]:
        if line.strip() == "---":
            break
        key, sep, value = line.partition(":")
        if sep and key.strip() == "status":
            return re.split(r"\s+#", value.strip(), maxsplit=1)[0].strip()
    return ""


def built_prefixes(root: str) -> list[str]:
    return [p for p in agent_prefixes(root) if build_status(root, p) is not None]


def classify(rel: str, root: str) -> Rule:
    if under(rel, HOOKS_DIR):
        return Rule.FROZEN
    if rel == MARKER:
        return Rule.APPEND_ONLY
    for prefix in agent_prefixes(root):
        if not rel.startswith(prefix):
            continue
        status = build_status(root, prefix)
        if status is None:
            return Rule.FREE           # build not started: earlier phases may write
        sub = rel[len(prefix):]
        if sub == BUILD_MD:
            return Rule.BUILD_DRAFT if status == "draft" else Rule.FROZEN
        if sub == SPEC_MD:
            return Rule.TEST_COLUMN_ONLY if status == "draft" else Rule.FROZEN
        if sub == DESIGN_MD or under(sub, EVALS_DIR):
            return Rule.FROZEN
        return Rule.FREE
    return Rule.FREE


def holder_dirs(root: str) -> set[str]:
    """Folders a shell write may not target: removing one takes frozen files along."""
    holders = {"", ".claude", HOOKS_DIR}
    if agent_prefixes(root) != [""]:
        holders.add(AGENTS_DIR)
    for prefix in built_prefixes(root):
        holders |= {prefix.rstrip("/"), prefix + "docs", prefix + DOCS_AGENT, prefix + EVALS_DIR}
    return holders


def inside_frozen_dir(rel: str, root: str) -> bool:
    if under(rel, HOOKS_DIR):
        return True
    return any(under(rel, prefix + EVALS_DIR) or under(rel, prefix + DOCS_AGENT)
               for prefix in built_prefixes(root))


def protected_strings(root: str) -> list[str]:
    strings = [HOOKS_DIR, MARKER]
    for prefix in built_prefixes(root):
        strings += [prefix + EVALS_DIR + "/", prefix + DESIGN_MD, prefix + SPEC_MD, prefix + BUILD_MD]
    return strings


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
    for x, y in zip(before, after):
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


def marker_change_ok(current: str | None, new: str, root: str) -> bool:
    proposed = parse_marker(new)
    if proposed is None:
        return False
    if current is None:                # creating the marker
        return build_status(root, "") is None   # a built one-agent root moves by hand
    existing = parse_marker(current)
    if existing is None:
        return False
    return existing[1] == proposed[1] and set(existing[0]) <= set(proposed[0])


# --- the two kinds of call

def file_hits(call: Call) -> list[str]:
    hits: list[str] = []
    for key in ("file_path", "notebook_path"):
        raw = call.tool_input.get(key)
        rel = rel_to_repo(raw, call.cwd, call.root)
        if rel is None:
            continue
        rule = classify(rel, call.root)
        if rule is Rule.FREE or (rule is Rule.BUILD_DRAFT and call.tool in FILE_TOOLS):
            continue
        path = resolve(str(raw), call.cwd)
        if rule is Rule.TEST_COLUMN_ONLY and call.tool in FILE_TOOLS:
            current = read_text(path)
            new = proposed_text(call, current or "")
            if current is not None and new is not None and only_test_cells(current, new):
                continue
        if rule is Rule.APPEND_ONLY and call.tool in FILE_TOOLS:
            current = read_text(path)
            new = proposed_text(call, current or "")
            if new is not None and marker_change_ok(current, new, call.root):
                continue
        hits.append(rel)
    return hits


def shell_words(command: str) -> Iterable[str]:
    for match in WORD.finditer(command):
        yield next(group for group in match.groups() if group is not None)


def shell_hits(call: Call) -> list[str]:
    command = str(call.tool_input.get("command", "")).replace("\\", "/")
    if not command or not WRITE.search(command):
        return []
    command = HEREDOC.sub(lambda m: m.group(3), command)
    hits = [f"a shell write naming {s}" for s in protected_strings(call.root) if s in command.lower()]
    words = list(shell_words(command))
    dirs, operands, skip = [resolve(call.cwd, call.cwd)], [], False
    for i, word in enumerate(words):
        if skip:
            skip = False
        elif word.lower() in CD and i + 1 < len(words) and not words[i + 1].startswith("-"):
            dirs.append(resolve(words[i + 1], dirs[-1]))
            skip = True
        elif word:
            operands.append(word)
    holders = holder_dirs(call.root)
    for folder in dirs:                # cd evals && rm config.yaml
        rel = rel_to_repo(folder, folder, call.root)
        if rel is not None and inside_frozen_dir(rel, call.root):
            hits.append("a shell write from inside " + rel)
    for word in operands:              # rm -rf evals, mv docs old, rm -rf *
        for folder in dirs:
            rel = rel_to_repo(word, folder, call.root)
            if rel is None:
                continue
            if rel.endswith("*"):
                rel = rel[:-1].rstrip("/")
            if classify(rel, call.root) is not Rule.FREE or rel in holders:
                hits.append("a shell write on " + (rel or "the repo root"))
    return hits


def evaluate(payload: dict[str, object], project_dir: str | None) -> list[str]:
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        raise ValueError("tool_input is not an object")
    cwd = str(payload.get("cwd") or os.getcwd())
    call = Call(str(payload.get("tool_name", "")), tool_input, cwd, project_dir or cwd)
    return file_hits(call) + shell_hits(call)


def main() -> int:
    # The call arrives as UTF-8; Windows would read it in its own code page.
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
        hits = evaluate(payload, os.environ.get("CLAUDE_PROJECT_DIR"))
    except Exception as exc:  # entry point: an unreadable call is not a pass
        hits = [f"could not inspect the call ({exc})"]
    if hits:
        print("BLOCKED by agent-cycle anti-gaming rail: " + "; ".join(sorted(set(hits)))
              + " -- frozen pipeline artifacts. Changes go through the re-entry ladder"
              " (dispute -> re-open the owning phase), never through the builder.",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
