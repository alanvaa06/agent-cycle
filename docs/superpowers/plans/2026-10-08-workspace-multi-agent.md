# agent-cycle v0.12 — Workspace Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let one repository hold several independent agents (`agents/<name>/`), each with its own design → ship cycle, guarded by one persistent state-driven hook, with single-agent repos unchanged.

**Architecture:** A workspace marker (`agent-cycle.yaml`) plus one shared resolution rule (`references/agent-root.md`) gives every skill an `AGENT_ROOT`; existing relative paths become relative to it. The anti-gaming hook moves out of a Markdown code block into a real, pytest-tested Python file whose freezing is decided from each agent's state on disk. Git-level steps (build baseline, ship diff) are prefixed with `AGENT_ROOT`.

**Tech Stack:** Claude Code plugin (Markdown/JSON); Python 3.11+ stdlib for the hook; pytest.

**Spec:** `docs/superpowers/specs/2026-10-08-workspace-multi-agent-design.md`

---

## Conventions used by every task

**Branch.** `feat/v0.12-workspace` (already created from `feat/v0.11-stack-decision`). Never commit to `main`; never switch branches.

**Commit trailer.** End every commit message with the `Co-Authored-By:` line your own harness attribution reminder specifies.

**Checks** (run from the repo root before every commit):

```bash
python -m pytest tests -q
python scripts/check_catalog.py --root .
python -c "import json,glob; [json.load(open(p,encoding='utf-8')) for p in glob.glob('skills/*/evals/cases.json')]; print('[ok] all cases.json parse')"
```

**Plugin paths.** Skills run in the TARGET repo; refer to plugin files as "the agent-cycle plugin's `<path>`".

**Console output** of any Python stays ASCII-only.

**Line endings.** The index stores LF; the working tree may be CRLF. Preserve each file's existing endings.

---

### Task 1: The hook as a real, tested file

**Files:**
- Create: `skills/build/assets/guard_artifacts.py`
- Create: `tests/test_guard_artifacts.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Make the hook importable from the tests**

Replace the body of `tests/conftest.py` with:

```python
"""Make scripts/ and the build skill's assets/ importable from the tests."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "build" / "assets"))
```

- [ ] **Step 2: Write the failing tests**

Write `tests/test_guard_artifacts.py`:

```python
"""Tests for skills/build/assets/guard_artifacts.py -- the anti-gaming hook."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import guard_artifacts as guard

HOOK = Path(__file__).resolve().parent.parent / "skills" / "build" / "assets" / "guard_artifacts.py"

SPEC = (
    "# Spec\n\n## 6. Traceability\n\n"
    "| BHV | Capability | Eval | Test |\n|---|---|---|---|\n"
    "| BHV-001 | answer | EV-1 | - |\n"
)
TEST_FILL = {
    "old_string": "| BHV-001 | answer | EV-1 | - |",
    "new_string": "| BHV-001 | answer | EV-1 | tests/test_answer.py |",
}
CAPABILITY_EDIT = {"old_string": "| BHV-001 | answer |", "new_string": "| BHV-001 | reply |"}


def make_agent(root: Path, prefix: str = "", status: str | None = None) -> Path:
    base = root / prefix
    (base / "docs" / "agent").mkdir(parents=True, exist_ok=True)
    (base / "evals").mkdir(parents=True, exist_ok=True)
    (base / "docs" / "agent" / "design.md").write_text("# design\n", encoding="utf-8")
    (base / "docs" / "agent" / "spec.md").write_text(SPEC, encoding="utf-8")
    (base / "evals" / "config.yaml").write_text("k: 1\n", encoding="utf-8")
    if status is not None:
        (base / "docs" / "agent" / "build.md").write_text(
            f"---\nstatus: {status}\n---\n# build\n", encoding="utf-8"
        )
    return base


def make_workspace(root: Path, agents: dict[str, str | None]) -> None:
    names = ", ".join(agents)
    (root / "agent-cycle.yaml").write_text(
        f"layout: workspace\nagents: [{names}]\n", encoding="utf-8"
    )
    for name, status in agents.items():
        make_agent(root, f"agents/{name}", status)


def run(root: Path, tool: str, cwd: Path | None = None, **tool_input: object) -> list[str]:
    payload = {"tool_name": tool, "tool_input": tool_input, "cwd": str(cwd or root)}
    return guard.evaluate(payload, str(root))


# --- single-agent repo: file tools

def test_single_prebuild_evals_editable(tmp_path: Path) -> None:
    make_agent(tmp_path)
    hits = run(tmp_path, "Edit", file_path=str(tmp_path / "evals/config.yaml"),
               old_string="k: 1", new_string="k: 2")
    assert hits == []


def test_single_build_started_freezes_evals_and_design(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Write", file_path=str(tmp_path / "evals/config.yaml"), content="k: 2\n")
    assert run(tmp_path, "Write", file_path=str(tmp_path / "docs/agent/design.md"), content="x\n")


def test_draft_allows_test_column_fill_only(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    spec = str(tmp_path / "docs/agent/spec.md")
    assert run(tmp_path, "Edit", file_path=spec, **TEST_FILL) == []
    assert run(tmp_path, "Edit", file_path=spec, **CAPABILITY_EDIT)


def test_multiedit_test_column_fill_allowed(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    hits = run(tmp_path, "MultiEdit", file_path=str(tmp_path / "docs/agent/spec.md"), edits=[TEST_FILL])
    assert hits == []


def test_approved_freezes_spec_and_build_md(tmp_path: Path) -> None:
    make_agent(tmp_path, status="approved")
    assert run(tmp_path, "Edit", file_path=str(tmp_path / "docs/agent/spec.md"), **TEST_FILL)
    assert run(tmp_path, "Write", file_path=str(tmp_path / "docs/agent/build.md"), content="x\n")


def test_draft_build_md_is_editable(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    hits = run(tmp_path, "Edit", file_path=str(tmp_path / "docs/agent/build.md"),
               old_string="# build", new_string="# build\nsuite green")
    assert hits == []


def test_garbled_build_md_freezes_everything(tmp_path: Path) -> None:
    base = make_agent(tmp_path)
    (base / "docs/agent/build.md").write_text("no frontmatter\n", encoding="utf-8")
    assert run(tmp_path, "Edit", file_path=str(tmp_path / "docs/agent/spec.md"), **TEST_FILL)
    assert run(tmp_path, "Write", file_path=str(tmp_path / "docs/agent/build.md"), content="x\n")


def test_later_phase_files_stay_free(tmp_path: Path) -> None:
    make_agent(tmp_path, status="approved")
    assert run(tmp_path, "Write", file_path=str(tmp_path / "docs/agent/interop.md"), content="x\n") == []


def test_hook_dir_always_protected(tmp_path: Path) -> None:
    make_agent(tmp_path)
    assert run(tmp_path, "Write", file_path=str(tmp_path / ".claude/hooks/guard_artifacts.py"), content="")
    assert run(tmp_path, "Bash", command="mv .claude/hooks/guard_artifacts.py /tmp/")


def test_notebook_edit_on_frozen_blocked(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "NotebookEdit", notebook_path=str(tmp_path / "evals/x.ipynb"))


def test_relative_path_from_moved_cwd(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Edit", cwd=tmp_path / "src", file_path="../evals/config.yaml",
               old_string="k: 1", new_string="k: 2")


# --- single-agent repo: shell

@pytest.mark.parametrize("command", [
    "rm -rf evals",
    "rm docs/agent/build.md",
    "cd evals && rm config.yaml",
    "mv docs docs_old",
    "rm -rf *",
    "Remove-Item -Recurse docs\\agent",
])
def test_shell_writes_on_frozen_blocked(tmp_path: Path, command: str) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Bash", command=command)


@pytest.mark.parametrize("command", [
    'git commit -m "rm stale docs"',
    "python -m pytest tests -q",
    "cat <<'EOF' > notes.md\nevals/config.yaml is frozen\nEOF",
    "echo hi > src/notes.txt",
])
def test_everyday_shell_allowed(tmp_path: Path, command: str) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Bash", command=command) == []


def test_shell_prebuild_evals_delete_allowed(tmp_path: Path) -> None:
    make_agent(tmp_path)
    assert run(tmp_path, "Bash", command="rm -rf evals") == []


# --- workspace

def test_workspace_freezes_per_agent(tmp_path: Path) -> None:
    make_workspace(tmp_path, {"ventas": "draft", "soporte": None})
    assert run(tmp_path, "Write", file_path=str(tmp_path / "agents/ventas/evals/config.yaml"), content="x\n")
    assert run(tmp_path, "Write", file_path=str(tmp_path / "agents/soporte/evals/config.yaml"), content="x\n") == []


def test_workspace_root_level_evals_is_not_an_agent(tmp_path: Path) -> None:
    make_workspace(tmp_path, {"ventas": "approved"})
    (tmp_path / "evals").mkdir()
    assert run(tmp_path, "Write", file_path=str(tmp_path / "evals/x.yaml"), content="x\n") == []


def test_workspace_freeze_ignores_the_list(tmp_path: Path) -> None:
    make_workspace(tmp_path, {"ventas": "draft", "soporte": None})
    (tmp_path / "agent-cycle.yaml").write_text("layout: workspace\nagents: [soporte]\n", encoding="utf-8")
    assert run(tmp_path, "Write", file_path=str(tmp_path / "agents/ventas/evals/config.yaml"), content="x\n")


def test_workspace_test_column_per_agent(tmp_path: Path) -> None:
    make_workspace(tmp_path, {"ventas": "draft", "soporte": "approved"})
    assert run(tmp_path, "Edit", file_path=str(tmp_path / "agents/ventas/docs/agent/spec.md"), **TEST_FILL) == []
    assert run(tmp_path, "Edit", file_path=str(tmp_path / "agents/soporte/docs/agent/spec.md"), **TEST_FILL)


@pytest.mark.parametrize("command", [
    "rm -rf agents/ventas",
    "rm -rf agents",
    "mv agents/ventas agents/old",
    "cd agents/ventas && rm evals/config.yaml",
    "echo x >> agent-cycle.yaml",
])
def test_workspace_shell_writes_blocked(tmp_path: Path, command: str) -> None:
    make_workspace(tmp_path, {"ventas": "draft"})
    assert run(tmp_path, "Bash", command=command)


def test_workspace_shell_write_in_other_agent_src_allowed(tmp_path: Path) -> None:
    make_workspace(tmp_path, {"ventas": "approved", "soporte": None})
    assert run(tmp_path, "Bash", command="echo hi > agents/soporte/src/notes.txt") == []


# --- agent-cycle.yaml is append-only

@pytest.mark.parametrize(("content", "allowed"), [
    ("layout: workspace\nagents: [ventas, soporte, nuevo]\n", True),
    ("layout: workspace\nagents: [ventas]\n", False),
    ("layout: single\nagents: [ventas, soporte]\n", False),
    ("layout: workspace\nagents: [ventas, soporte]\nowner: x\n", False),
    ("layout: workspace\nagents:\n  - ventas\n", False),
])
def test_marker_is_append_only(tmp_path: Path, content: str, allowed: bool) -> None:
    make_workspace(tmp_path, {"ventas": "draft", "soporte": None})
    hits = run(tmp_path, "Write", file_path=str(tmp_path / "agent-cycle.yaml"), content=content)
    assert (hits == []) is allowed


def test_marker_creation_blocked_in_built_single_repo(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Write", file_path=str(tmp_path / "agent-cycle.yaml"),
               content="layout: workspace\nagents: [nuevo]\n")


def test_marker_creation_allowed_in_unbuilt_single_repo(tmp_path: Path) -> None:
    make_agent(tmp_path)
    hits = run(tmp_path, "Write", file_path=str(tmp_path / "agent-cycle.yaml"),
               content="layout: workspace\nagents: [nuevo]\n")
    assert hits == []


# --- the entry point

def _run_hook(stdin: str, project_dir: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project_dir)}
    return subprocess.run([sys.executable, str(HOOK)], input=stdin, capture_output=True,
                          text=True, env=env, check=False)


def test_main_fails_closed_on_bad_json(tmp_path: Path) -> None:
    proc = _run_hook("not json", tmp_path)
    assert proc.returncode == 2
    assert "could not inspect" in proc.stderr
    proc.stderr.encode("ascii")


def test_main_allows_free_call(tmp_path: Path) -> None:
    make_agent(tmp_path)
    payload = json.dumps({"tool_name": "Write", "cwd": str(tmp_path),
                          "tool_input": {"file_path": str(tmp_path / "src/a.py"), "content": "x"}})
    assert _run_hook(payload, tmp_path).returncode == 0


def test_hook_version_is_declared() -> None:
    assert isinstance(guard.HOOK_VERSION, int) and guard.HOOK_VERSION >= 2
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python -m pytest tests/test_guard_artifacts.py -q`
Expected: collection error `ModuleNotFoundError: No module named 'guard_artifacts'`.

- [ ] **Step 4: Write the hook**

Write `skills/build/assets/guard_artifacts.py`:

```python
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
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests -q`
Expected: `305 passed` (39 existing + 266 hook tests). The listing above is the hook's first version (42 tests, `81 passed`). Two hardening follow-ups replaced it: layout from directories, the build.md ratchet, path canonicalisation, detector gaps, false blocks and settings protection; then write targets parsed per command, human-only git verbs, glob depth, hard links and the pinned `-I -S` registration. The current source is `skills/build/assets/guard_artifacts.py`. If a test fails, fix the hook — never weaken a test without reporting it.

- [ ] **Step 6: Mutation spot-check**

Temporarily change `return Rule.FREE           # build not started` to `return Rule.FROZEN`; run `python -m pytest tests/test_guard_artifacts.py -q`; expected: `test_single_prebuild_evals_editable` and `test_workspace_freezes_per_agent` FAIL. Revert; re-run; expected all pass.

- [ ] **Step 7: Commit**

```bash
git add skills/build/assets/guard_artifacts.py tests/test_guard_artifacts.py tests/conftest.py
git commit -m "feat(build): anti-gaming hook as a tested file, state-driven per agent"
```

---

### Task 2: EDD eval cases — before any skill text changes

**Files:**
- Modify: `skills/design/evals/cases.json`, `skills/spec/evals/cases.json`, `skills/build/evals/cases.json`, `skills/ship/evals/cases.json`
- Modify: `skills/design/evals/README.md`, `skills/build/evals/README.md`, `skills/ship/evals/README.md`

- [ ] **Step 1: Append to `skills/design/evals/cases.json` `cases`:**

```json
{
  "id": "DES-E07",
  "type": "edge-workspace-new-agent",
  "input": "Design a second agent for this client: a support agent that answers order-status questions. (Fixture: a workspace repo with agent-cycle.yaml listing [ventas] and agents/ventas/ already designed.)",
  "expected": {
    "fires": true,
    "checks": [
      "Resolves the workspace per the agent-cycle plugin's references/agent-root.md and creates the new agent under agents/<name>/ — design.md is written to agents/<name>/docs/agent/design.md, never to the repo root",
      "agent-cycle.yaml gains <name> in agents: and nothing else in it changes",
      "If the proposed name is already listed or agents/<name>/ exists, it stops and asks one question before writing anything",
      "Nothing under agents/ventas/ is modified"
    ]
  }
},
{
  "id": "DES-E08",
  "type": "edge-single-to-workspace",
  "input": "Design a second agent in this repo. (Fixture: a single-agent repo — docs/agent/, evals/, src/ at the root, no agent-cycle.yaml.)",
  "expected": {
    "fires": true,
    "checks": [
      "Does NOT create the second agent's files and does not move anything",
      "Shows the conversion commands for the human to run as one dedicated commit: git mv of the existing agent's files into agents/<existing-name>/ and creation of agent-cycle.yaml, with the commit message prefix 'agent-cycle: workspace move'",
      "States that after the move the existing agent keeps its frozen state (build.md moves with it) and that ship accepts the pure-rename commit",
      "No files are created or modified — verified on the filesystem afterward"
    ]
  }
}
```

- [ ] **Step 2: Append to `skills/spec/evals/cases.json` `cases`:**

```json
{
  "id": "SPC-E05",
  "type": "edge-workspace-ambiguous",
  "input": "Write the spec. (Fixture: workspace with agents [ventas, soporte], both with approved design.md; session started at the repo root; the request names no agent.)",
  "expected": {
    "fires": true,
    "checks": [
      "Asks exactly one question listing the agents as lettered options before reading any design.md",
      "After the answer, reads and writes only inside agents/<chosen>/"
    ]
  }
}
```

- [ ] **Step 3: Append to `skills/build/evals/cases.json` `cases`:**

```json
{
  "id": "BLD-E06",
  "type": "edge-workspace-second-build",
  "input": "Build the soporte agent. (Fixture: workspace with agents [ventas, soporte]; ventas already built with the hook installed at .claude/hooks/; soporte has approved design, spec and evals.)",
  "expected": {
    "fires": true,
    "checks": [
      "The baseline commit contains only agents/soporte/ artifacts (design.md, spec.md, evals/) plus agent-cycle.yaml if soporte's entry was uncommitted; build_start recorded in agents/soporte/docs/agent/build.md",
      "agents/soporte/docs/agent/build.md stub (status: draft, build_start) is committed on its own before the first source file",
      "The hook is NOT reinstalled when its HOOK_VERSION matches the plugin's; it is verified active (a dummy edit to agents/soporte/evals/config.yaml is blocked)",
      "Every source, test, lockfile and deploy file is written inside agents/soporte/",
      "Queue/stream name, database schema and service.name carry the soporte prefix"
    ]
  }
}
```

- [ ] **Step 4: Append to `skills/ship/evals/cases.json` `cases`:**

```json
{
  "id": "SHP-E05",
  "type": "edge-workspace-ship",
  "input": "Run the ship audit for soporte. (Fixture: workspace; ventas commits interleaved with soporte's build range; one commit in the range touches agents/soporte/src/ and agents/ventas/src/ together; one earlier 'agent-cycle: workspace move' pure-rename commit.)",
  "expected": {
    "fires": true,
    "checks": [
      "The anti-gaming diff covers only agents/soporte/evals/, docs/agent/design.md and docs/agent/spec.md (plus their pre-move root paths when a workspace-move commit is in range), command cited",
      "Commits touching only agents/ventas/ are ignored",
      "The commit touching both agents is a finding routed to build",
      "The pure-rename workspace-move commit is accepted as sanctioned and recorded",
      "The lockfile checked is agents/soporte/'s"
    ]
  }
}
```

- [ ] **Step 5: README fixtures.** Append to `skills/design/evals/README.md`, `skills/build/evals/README.md`, `skills/ship/evals/README.md` a "Workspace cases (v0.12)" section naming the fixture each new case needs (as in the case `input`), built in a scratch git repo — never this repo.

- [ ] **Step 6: Run the checks; commit**

```bash
git add skills/design/evals skills/spec/evals skills/build/evals skills/ship/evals
git commit -m "test(evals): v0.12 workspace eval cases (EDD first)"
```

---

### Task 3: Agent-root resolution rule

**Files:**
- Create: `references/agent-root.md`

- [ ] **Step 1: Write `references/agent-root.md`:**

````markdown
# Agent root — which agent a skill is working on

Every agent-cycle skill resolves `AGENT_ROOT` before touching any path. All
paths the skills name (`docs/agent/...`, `evals/...`, `src/...`, `tests/...`)
are relative to `AGENT_ROOT`; git commands that take paths prefix them with it.

## Layouts

- **One-agent repo:** no `agent-cycle.yaml` at the repo root. `AGENT_ROOT` is
  the repo root. This is the layout every repo had before v0.12.
- **Workspace:** `agent-cycle.yaml` at the repo root:

  ```yaml
  layout: workspace
  agents: [ventas, soporte]      # each lives at agents/<name>/
  ```

  `<name>` is the design's `agent_name` (kebab-case). The path is always
  `agents/<name>/`; there are no configurable paths.

## Resolution order

1. No `agent-cycle.yaml` -> `AGENT_ROOT` = repo root.
2. The working directory is inside `agents/<name>/` -> that agent.
3. The user's request names an agent in `agents:` -> that agent.
4. `agents:` has exactly one entry -> that agent.
5. Otherwise -> ONE question listing the agents as lettered options.

## Rules

- A skill reads and writes only inside `AGENT_ROOT`, except: design appends a
  new agent's name to `agent-cycle.yaml`; build's baseline commit may include
  `agent-cycle.yaml`; ship reads other agents' paths only to detect commits
  that touch two agents.
- The anti-gaming hook (the agent-cycle plugin's
  `skills/build/assets/guard_artifacts.py`) takes its agents from the
  directories (the repo root and every `agents/<dir>/`), never from this
  file. An agent's `evals/`, `docs/agent/design.md` and `docs/agent/spec.md`
  freeze once its `docs/agent/build.md` exists, and the agent stays frozen
  even if build.md later disappears (ratchet). `agent-cycle.yaml` is
  append-only.
- Agents in one workspace share no code. They may share infrastructure at
  deploy time (one Postgres, one reverse proxy); resource names carry the
  agent prefix (build's adapter bindings).
````

- [ ] **Step 2: Run the checks; commit**

```bash
git add references/agent-root.md
git commit -m "feat: agent-root resolution rule for workspace mode"
```

---

### Task 4: `design` — new agents in a workspace, conversion

**Files:**
- Modify: `skills/design/SKILL.md`, `skills/design/references/interview-guide.md`

- [ ] **Step 1: SKILL.md.** Add as the first workflow step: `0. Resolve AGENT_ROOT per the agent-cycle plugin's references/agent-root.md. In a workspace, a new agent's AGENT_ROOT is agents/<agent_name>/.` Replace the write-scope rule ("Write ONLY `docs/agent/design.md` ...") with:

```markdown
8. Write ONLY `<AGENT_ROOT>/docs/agent/design.md`. In a workspace, a NEW agent
   also appends its name to `agents:` in `agent-cycle.yaml` (nothing else in
   that file changes); a name already listed or an existing `agents/<name>/`
   -> stop and ask. In a one-agent repo that already holds an agent, a second
   agent is never created here: show the conversion (interview-guide
   "Second agent in a one-agent repo") and stop. Re-verification only reads.
```

Add to "Failure modes to avoid": `- Writing a workspace agent's design.md at the repo root, or editing another agent's files (rule 8).`

- [ ] **Step 2: interview-guide.md.** Append a section:

````markdown
## Second agent in a one-agent repo

The repo has `docs/agent/` at its root and no `agent-cycle.yaml`. Do not move
or create anything. Show the human these commands to run from their own
terminal as ONE commit (the anti-gaming hook only governs Claude's tool calls),
listing the existing agent's actual paths found in the repo:

```bash
# 1. If .claude/hooks/guard_artifacts.py exists, upgrade it to the plugin's
#    current version first -- an older hook does not protect agents/*/:
mv .claude/hooks/guard_artifacts.py .claude/hooks/guard_artifacts.py.off
cp <plugin>/skills/build/assets/guard_artifacts.py .claude/hooks/guard_artifacts.py.off
mv .claude/hooks/guard_artifacts.py.off .claude/hooks/guard_artifacts.py
# 2. Move the existing agent:
mkdir -p agents/<existing-name>/docs
git mv docs/agent agents/<existing-name>/docs/agent
git mv evals src tests agents/<existing-name>/   # plus its lockfile, pyproject, Dockerfile, compose, .env.example as present
printf 'layout: workspace\nagents: [<existing-name>]\n' > agent-cycle.yaml
git add agent-cycle.yaml
git commit -m "agent-cycle: workspace move <existing-name>"
# 3. If .claude/hooks/built-agents.txt has a "." line, replace it with
#    agents/<existing-name>/ and commit the file (it is tracked):
#    git commit -m "agent-cycle: ratchet follows the move" -- .claude/hooks/built-agents.txt
```

Say: the existing agent keeps its frozen state (its build.md moves with it);
ship accepts this pure-rename commit and records it. After the commit, run
this skill again for the new agent.
````

- [ ] **Step 3: Run the checks; commit**

```bash
git add skills/design
git commit -m "feat(design): workspace agents and one-agent-repo conversion"
```

---

### Task 5: `build` — per-agent rails and the hook file

**Files:**
- Modify: `skills/build/SKILL.md`, `skills/build/references/build-guide.md`, `skills/build/references/forge-delegation.md`, `skills/build/references/adapter-bindings.md`

- [ ] **Step 1: forge-delegation.md.** Replace everything from the line after `## The anti-gaming hook` up to (not including) `## Disputes` with:

````markdown
The hook is the agent-cycle plugin's `skills/build/assets/guard_artifacts.py`
(tested in the plugin's `tests/test_guard_artifacts.py`). Installing it writes
three things in the TARGET repo and commits them together in ONE commit:
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
plugin's, STOP and ask the human to upgrade it from their own terminal: rename
it to `guard_artifacts.py.off`, copy the plugin's file, then rename it back.
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
- **Settings.** `.claude/settings.json` and `settings.local.json` must stay
  valid JSON. The pinned PreToolUse entry and the `env` key must not change,
  and `disableAllHooks` must never be set. Any shell write whose target names
  `.claude/settings` is blocked.
- **Shell writes.** The hook judges only write targets, parsed per command:
  - the verb is the word's basename, so `/bin/rm`, `rm.exe` and `"rm"` count;
  - the target is the destination of `cp`, `Copy-Item` or `robocopy`, the
    `-Path` of `Set-Content`, a redirect's target, or every argument of `rm`,
    `mv`, `touch` and `tee`.

  Reading a frozen file is not a write. Blocked:
  - a write whose target is a frozen path;
  - a destructive verb (`rm`, `mv`, `Remove-Item`, `robocopy /MIR`,
    `git clean/rm/mv`, `find -delete`, ...) whose target is a folder holding
    frozen files: the repo root, `agents/`, an agent folder, its `docs`,
    `docs/agent` or `evals`;
  - a glob that reaches one by depth: a protected file at its own depth, a
    protected folder at its depth or deeper, a holder at its depth or above.
- **Git (the human runs these while any agent is built).** Blocked outright:
  - `git apply`, `am`, `revert`, `cherry-pick`, `merge`, `pull`, `rebase`;
  - `git reset --hard`, `git stash pop`/`apply`;
  - `git checkout`/`restore` from another commit (`<tree-ish> --`,
    `--source`/`-s`) over `.`, `:/`, a holder or a frozen path.

  Path-less `git clean`, `git stash -u`/`-a` and `git reset --hard` act on the
  current directory, so they are blocked at the root and in an agent folder.
  Still allowed: `git checkout <branch>`, `git checkout -b`, `git switch`,
  `git restore src/app.py`, `git checkout -- src/x`, `git clean -fd src`.
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

What it cannot see:
- a script that writes (`python fix.py`, `python -c`);
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
````

- [ ] **Step 2: build-guide.md.** At the top of Step 0 add: `Resolve AGENT_ROOT per the agent-cycle plugin's references/agent-root.md; every path below is relative to it.` In Step 2, replace the baseline `git add`/`git commit` lines with the AGENT_ROOT-prefixed form and add the stub step:

```markdown
- `git status --porcelain -- <AGENT_ROOT>/docs/agent/design.md <AGENT_ROOT>/docs/agent/spec.md <AGENT_ROOT>/evals/`
  prints anything, or `git ls-files` misses one -> commit exactly those paths
  (plus `agent-cycle.yaml` when this agent's entry is uncommitted):
  `git commit -m "Approved design, spec and evals (<agent_name>)" -- <paths>`.
- Record `git rev-parse --short HEAD` as `build_start`.
- Write `<AGENT_ROOT>/docs/agent/build.md` as a stub (`status: draft`,
  `build_start`) and commit it alone. Its existence freezes this agent's
  evals, design and spec.
- Hook: install when absent: the script, `.claude/hooks/built-agents.txt`
  seeded with this agent's prefix, and the pinned `python -I -S` registration
  in `.claude/settings.json`, all committed together in ONE commit. If the
  installed `HOOK_VERSION` is lower than the plugin's, STOP and ask the human
  to upgrade it from their own terminal (rename to `.off`, copy the plugin's
  file, rename back). Build never writes `.claude/hooks/` once the hook
  exists. Otherwise verify it is active, and commit `built-agents.txt` when
  the hook has added this agent's line (forge-delegation.md). While any agent
  is built, the git verbs that rewrite the tree (merge, pull, rebase, revert,
  cherry-pick, apply, am, reset --hard, stash pop/apply) are the human's.
```

In Step 3 add: `Every file this build writes lives inside AGENT_ROOT (source, tests, lockfile, deploy recipe). Shared infrastructure is reached through configuration, never written outside AGENT_ROOT.`

- [ ] **Step 3: adapter-bindings.md.** Add to the universal rules: `- In a workspace, every resource name carries the agent prefix: queue/stream name, database schema, service.name (telemetry), so agents sharing one Postgres, Redis or collector cannot collide.`

- [ ] **Step 4: SKILL.md.** Rule 3: replace the hook parenthetical with `(freezes this agent's evals/, design.md and spec.md once its build.md exists; per forge-delegation.md)`. Rule 10 (writes): prefix every path with `AGENT_ROOT/` and add `.claude/hooks/ (script + seeded built-agents.txt) and .claude/settings.json only when installing an absent hook, in one commit (upgrades and registration changes are the human's)`. Add the Step 0 resolution line to the workflow.

- [ ] **Step 5: Verify no stale hook wording.** Run: `grep -n "BLOCKED_PREFIXES\|blocks evals/ and docs/agent/" skills/build/` — expected: no output.

- [ ] **Step 6: Run the checks; commit**

```bash
git add skills/build
git commit -m "feat(build): per-agent rails, hook from the tested file, resource prefixes"
```

---

### Task 6: `ship` — per-agent audit

**Files:**
- Modify: `skills/ship/SKILL.md`, `skills/ship/references/audit-guide.md`

- [ ] **Step 1: audit-guide.md Section 0.** Add first: `Resolve AGENT_ROOT per the agent-cycle plugin's references/agent-root.md; every path below is relative to it.`

- [ ] **Step 2: Section 4 (anti-gaming).** Replace the diff command with:

```markdown
`git diff --word-diff --find-renames <build_start>..HEAD -- <AGENT_ROOT>/evals/ <AGENT_ROOT>/docs/agent/design.md <AGENT_ROOT>/docs/agent/spec.md`
plus, when a commit in the range has a message starting `agent-cycle: workspace move`
and `git show --name-status <sha>` lists only `R100` entries, the same three
pre-move paths (repo root) in the pathspec, so the move shows as renames. That
commit is sanctioned: record its sha. Apply the same pathspec to the
"first entered git inside the range" check (`--diff-filter=A --find-renames`).

Mixed-agent commits (workspace only):
`git log --format=%h <build_start>..HEAD -- <AGENT_ROOT>` then, per commit,
`git show --name-only --format= <sha>`: a commit that touches `<AGENT_ROOT>`
and any other `agents/<name>/` is a finding routed to build. Commits touching
only other agents are their work and are ignored.
```

- [ ] **Step 3: Section 3 lockfile.** Replace "the lockfile" with "the lockfile under `<AGENT_ROOT>`".

- [ ] **Step 4: SKILL.md.** Rule 7: `word-diff from build_start to HEAD on <AGENT_ROOT>'s evals/, design.md and spec.md (workspace moves and mixed-agent commits per audit-guide Section 4)`. Add the resolution line to the workflow.

- [ ] **Step 5: Run the checks; commit**

```bash
git add skills/ship
git commit -m "feat(ship): per-agent anti-gaming audit, workspace moves, mixed-agent commits"
```

---

### Task 7: The other skills resolve AGENT_ROOT

**Files:**
- Modify: `skills/spec/SKILL.md`, `skills/evals/SKILL.md`, `skills/interop/SKILL.md`, `skills/skills/SKILL.md`, `skills/blueprint/SKILL.md`, `skills/economics/SKILL.md`, `skills/review/SKILL.md`, `skills/refresh/references/refresh-guide.md`

- [ ] **Step 1:** In each of the seven SKILL.md files, add as the first workflow step (renumber if numbered): `0. Resolve AGENT_ROOT per the agent-cycle plugin's references/agent-root.md (one question when several agents match); every path below is relative to it and this skill writes only inside it.` In review's SKILL.md add: `In a workspace, review assesses one agent at a time.`

- [ ] **Step 2:** In `skills/refresh/references/refresh-guide.md` Step 3 (harvest), add: `In a workspace project, harvest every agents/*/docs/agent/design.md and agents/*/docs/agent/build.md (same claims rules).`

- [ ] **Step 3: Run the checks; commit**

```bash
git add skills/spec skills/evals skills/interop skills/skills skills/blueprint skills/economics skills/review skills/refresh
git commit -m "feat: every skill resolves AGENT_ROOT first"
```

---

### Task 8: Release v0.12.0

**Files:**
- Modify: `CHANGELOG.md`, `README.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`

- [ ] **Step 1:** plugin.json `"version": "0.12.0"`; append to the description (both manifests, identical): ` Workspace mode: several agents per repository.`

- [ ] **Step 2: CHANGELOG.** Change the header rule line to `Semver: minor = new pipeline skill or new pipeline capability, patch = fixes.` Insert above `## [0.11.0]`:

```markdown
## [0.12.0] — <release date>

### Added
- **Workspace mode:** several independent agents per repository under
  `agents/<name>/`, declared by `agent-cycle.yaml`; one-agent repos are
  unchanged. Every skill resolves `AGENT_ROOT` first
  (`references/agent-root.md`).
- **The anti-gaming hook is a tested file** (`skills/build/assets/guard_artifacts.py`,
  `tests/test_guard_artifacts.py`): freezing is decided per agent from its
  state (build.md present; draft vs approved). Agents come from the
  directories (the root and every `agents/<dir>/`), never from
  `agent-cycle.yaml`, which is append-only.
- **build.md ratchet:** the hook records every built agent in
  `.claude/hooks/built-agents.txt`, so deleting or moving a build.md by any
  route never unfreezes the agent.
- **Settings protection:** the hook is registered as
  `python -I -S "$CLAUDE_PROJECT_DIR/.claude/hooks/guard_artifacts.py"`. It
  blocks any change to that entry or to the `env` key of
  `.claude/settings.json` / `settings.local.json`, and `disableAllHooks`.
- **Tracked ratchet and human-only git:** `built-agents.txt` is committed with
  the hook, so a fresh clone stays frozen. While any agent is built, merge,
  pull, rebase, revert, cherry-pick, apply, am, reset --hard, stash pop/apply,
  and checkout/restore from another commit over protected paths are the
  human's.
- **Hardened paths and shell reading:** file-tool paths are canonicalised
  (junctions, 8.3 names, `\\?\`, trailing dots, NTFS streams). More write
  forms are recognised: PowerShell aliases, `sed`/`perl`/`awk` in-place,
  `git -C`, interpreter here-docs, `bash -c`, globs matched by depth, hard
  links. Only write targets are judged, so reading frozen files (`2>&1`,
  `> results.txt`, `cp evals/x /tmp/`, commit messages naming frozen paths)
  no longer trips it.
- design: new agents in a workspace; conversion commands for a one-agent repo.
- Eval cases DES-E07, DES-E08, SPC-E05, BLD-E06, SHP-E05.

### Changed
- build: per-agent baseline commit, build.md stub committed first, writes
  only inside AGENT_ROOT, resource names prefixed per agent.
- ship: anti-gaming diff limited to the agent; workspace-move commits
  accepted; commits touching two agents are findings.

### Upgrade notes
- The hook is now persistent and narrower: only `evals/`, `docs/agent/design.md`
  and `docs/agent/spec.md` freeze (no longer all of `docs/agent/`), from the
  moment build.md exists.
- Hook upgrades are a human step: build never writes `.claude/hooks/`. When
  the installed `HOOK_VERSION` is lower than the plugin's, build stops and
  asks you to rename the hook to `.off`, copy the plugin's file, and rename it
  back. An older hook does not protect `agents/*/`, so upgrade before
  converting a repo to a workspace.
- Repos whose `.claude/settings.json` registers the hook without `-I -S`:
  update the command to
  `python -I -S "$CLAUDE_PROJECT_DIR/.claude/hooks/guard_artifacts.py"` and
  commit `.claude/hooks/built-agents.txt` (both by hand; the hook blocks the
  builder from doing either through its own registration).
- Re-entry on a built agent: rename the hook to `.off`, make the change,
  remove the agent's line from `.claude/hooks/built-agents.txt` when its
  build.md is deleted or moved, then rename the hook back.
- Shell writes to an existing build.md are blocked (edit it with file tools).

### Pending graduation
- A real workspace with two agents both taken through build and ship.
```

Replace `<release date>` with the commit date.

- [ ] **Step 3: README.** Add a short "Several agents in one repo" subsection after the skills section: one paragraph on `agents/<name>/`, `agent-cycle.yaml`, and the conversion path; update the Versioning rule line to match the CHANGELOG and the Status line to `v0.12.0`.

- [ ] **Step 4: Full verification**

Run the three checks from Conventions. Expected: `305 passed`; `PASS: 9 card(s); ...`; `[ok] all cases.json parse`.

- [ ] **Step 5: Commit**

```bash
git add CHANGELOG.md README.md .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore: release v0.12.0 (workspace mode)"
```

- [ ] **Step 6: Hand off.** Report the branch, `git log --oneline feat/v0.11-stack-decision..HEAD`, and the verification outputs. Merging, pushing and the PR are the owner's call.
