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
