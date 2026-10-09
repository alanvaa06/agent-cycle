"""Tests for skills/build/assets/guard_artifacts.py -- the anti-gaming hook."""
import json
import os
import subprocess
import sys
from collections.abc import Mapping
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


def run(root: Path, tool: str, tool_input: Mapping[str, object], cwd: Path | None = None) -> list[str]:
    payload: dict[str, object] = {"tool_name": tool, "tool_input": dict(tool_input), "cwd": str(cwd or root)}
    return guard.evaluate(payload, str(root))


# --- single-agent repo: file tools

def test_single_prebuild_evals_editable(tmp_path: Path) -> None:
    make_agent(tmp_path)
    hits = run(tmp_path, "Edit",
               {"file_path": str(tmp_path / "evals/config.yaml"), "old_string": "k: 1", "new_string": "k: 2"})
    assert hits == []


def test_single_build_started_freezes_evals_and_design(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Write", {"file_path": str(tmp_path / "evals/config.yaml"), "content": "k: 2\n"})
    assert run(tmp_path, "Write", {"file_path": str(tmp_path / "docs/agent/design.md"), "content": "x\n"})


def test_draft_allows_test_column_fill_only(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    spec = str(tmp_path / "docs/agent/spec.md")
    assert run(tmp_path, "Edit", {"file_path": spec, **TEST_FILL}) == []
    assert run(tmp_path, "Edit", {"file_path": spec, **CAPABILITY_EDIT})


def test_multiedit_test_column_fill_allowed(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    hits = run(tmp_path, "MultiEdit", {"file_path": str(tmp_path / "docs/agent/spec.md"), "edits": [TEST_FILL]})
    assert hits == []


def test_approved_freezes_spec_and_build_md(tmp_path: Path) -> None:
    make_agent(tmp_path, status="approved")
    assert run(tmp_path, "Edit", {"file_path": str(tmp_path / "docs/agent/spec.md"), **TEST_FILL})
    assert run(tmp_path, "Write", {"file_path": str(tmp_path / "docs/agent/build.md"), "content": "x\n"})


def test_draft_build_md_is_editable(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    hits = run(tmp_path, "Edit",
               {"file_path": str(tmp_path / "docs/agent/build.md"), "old_string": "# build",
                "new_string": "# build\nsuite green"})
    assert hits == []


def test_garbled_build_md_freezes_everything(tmp_path: Path) -> None:
    base = make_agent(tmp_path)
    (base / "docs/agent/build.md").write_text("no frontmatter\n", encoding="utf-8")
    assert run(tmp_path, "Edit", {"file_path": str(tmp_path / "docs/agent/spec.md"), **TEST_FILL})
    assert run(tmp_path, "Write", {"file_path": str(tmp_path / "docs/agent/build.md"), "content": "x\n"})


def test_later_phase_files_stay_free(tmp_path: Path) -> None:
    make_agent(tmp_path, status="approved")
    assert run(tmp_path, "Write", {"file_path": str(tmp_path / "docs/agent/interop.md"), "content": "x\n"}) == []


def test_hook_dir_always_protected(tmp_path: Path) -> None:
    make_agent(tmp_path)
    assert run(tmp_path, "Write", {"file_path": str(tmp_path / ".claude/hooks/guard_artifacts.py"), "content": ""})
    assert run(tmp_path, "Bash", {"command": "mv .claude/hooks/guard_artifacts.py /tmp/"})


def test_notebook_edit_on_frozen_blocked(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "NotebookEdit", {"notebook_path": str(tmp_path / "evals/x.ipynb")})


def test_relative_path_from_moved_cwd(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Edit",
               {"file_path": "../evals/config.yaml", "old_string": "k: 1", "new_string": "k: 2"}, cwd=tmp_path / "src")


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
    assert run(tmp_path, "Bash", {"command": command})


@pytest.mark.parametrize("command", [
    'git commit -m "rm stale docs"',
    "python -m pytest tests -q",
    "cat <<'EOF' > notes.md\nevals/config.yaml is frozen\nEOF",
    "echo hi > src/notes.txt",
])
def test_everyday_shell_allowed(tmp_path: Path, command: str) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Bash", {"command": command}) == []


def test_shell_prebuild_evals_delete_allowed(tmp_path: Path) -> None:
    make_agent(tmp_path)
    assert run(tmp_path, "Bash", {"command": "rm -rf evals"}) == []


# --- workspace

def test_workspace_freezes_per_agent(tmp_path: Path) -> None:
    make_workspace(tmp_path, {"agent-a": "draft", "agent-b": None})
    assert run(tmp_path, "Write", {"file_path": str(tmp_path / "agents/agent-a/evals/config.yaml"), "content": "x\n"})
    assert run(tmp_path, "Write",
               {"file_path": str(tmp_path / "agents/agent-b/evals/config.yaml"), "content": "x\n"}) == []


def test_workspace_root_level_evals_is_not_an_agent(tmp_path: Path) -> None:
    make_workspace(tmp_path, {"agent-a": "approved"})
    (tmp_path / "evals").mkdir()
    assert run(tmp_path, "Write", {"file_path": str(tmp_path / "evals/x.yaml"), "content": "x\n"}) == []


def test_workspace_freeze_ignores_the_list(tmp_path: Path) -> None:
    make_workspace(tmp_path, {"agent-a": "draft", "agent-b": None})
    (tmp_path / "agent-cycle.yaml").write_text("layout: workspace\nagents: [agent-b]\n", encoding="utf-8")
    assert run(tmp_path, "Write", {"file_path": str(tmp_path / "agents/agent-a/evals/config.yaml"), "content": "x\n"})


def test_workspace_test_column_per_agent(tmp_path: Path) -> None:
    make_workspace(tmp_path, {"agent-a": "draft", "agent-b": "approved"})
    assert run(tmp_path, "Edit", {"file_path": str(tmp_path / "agents/agent-a/docs/agent/spec.md"), **TEST_FILL}) == []
    assert run(tmp_path, "Edit", {"file_path": str(tmp_path / "agents/agent-b/docs/agent/spec.md"), **TEST_FILL})


@pytest.mark.parametrize("command", [
    "rm -rf agents/agent-a",
    "rm -rf agents",
    "mv agents/agent-a agents/old",
    "cd agents/agent-a && rm evals/config.yaml",
    "echo x >> agent-cycle.yaml",
])
def test_workspace_shell_writes_blocked(tmp_path: Path, command: str) -> None:
    make_workspace(tmp_path, {"agent-a": "draft"})
    assert run(tmp_path, "Bash", {"command": command})


def test_workspace_shell_write_in_other_agent_src_allowed(tmp_path: Path) -> None:
    make_workspace(tmp_path, {"agent-a": "approved", "agent-b": None})
    assert run(tmp_path, "Bash", {"command": "echo hi > agents/agent-b/src/notes.txt"}) == []


# --- agent-cycle.yaml is append-only

@pytest.mark.parametrize(("content", "allowed"), [
    ("layout: workspace\nagents: [agent-a, agent-b, agent-c]\n", True),
    ("layout: workspace\nagents: [agent-a]\n", False),
    ("layout: single\nagents: [agent-a, agent-b]\n", False),
    ("layout: workspace\nagents: [agent-a, agent-b]\nowner: x\n", False),
    ("layout: workspace\nagents:\n  - agent-a\n", False),
])
def test_marker_is_append_only(tmp_path: Path, content: str, allowed: bool) -> None:
    make_workspace(tmp_path, {"agent-a": "draft", "agent-b": None})
    hits = run(tmp_path, "Write", {"file_path": str(tmp_path / "agent-cycle.yaml"), "content": content})
    assert (hits == []) is allowed


def test_marker_creation_blocked_in_built_single_repo(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Write",
               {"file_path": str(tmp_path / "agent-cycle.yaml"), "content": "layout: workspace\nagents: [agent-c]\n"})


def test_marker_creation_allowed_in_unbuilt_single_repo(tmp_path: Path) -> None:
    make_agent(tmp_path)
    hits = run(tmp_path, "Write",
               {"file_path": str(tmp_path / "agent-cycle.yaml"), "content": "layout: workspace\nagents: [agent-c]\n"})
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


# --- hardening: helpers

GUARD_COMMAND = "python -I -S \"$CLAUDE_PROJECT_DIR/.claude/hooks/guard_artifacts.py\""
OLD_GUARD_COMMAND = "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/guard_artifacts.py\""
GUARD_ENTRY: dict[str, object] = {
    "matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash|PowerShell",
    "hooks": [{"type": "command", "command": GUARD_COMMAND}],
}
OLD_GUARD_ENTRY: dict[str, object] = {**GUARD_ENTRY, "hooks": [{"type": "command", "command": OLD_GUARD_COMMAND}]}
SETTINGS_WITH_GUARD = {"hooks": {"PreToolUse": [GUARD_ENTRY]}}


def _run_hook_bytes(payload: Mapping[str, object], project_dir: Path,
                    cwd: Path | None = None) -> subprocess.CompletedProcess[bytes]:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project_dir)}
    return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload).encode("utf-8"),
                          capture_output=True, env=env, cwd=cwd, check=False)


# --- C1: the layout comes from directories, never from agent-cycle.yaml

def test_deleting_the_marker_does_not_unfreeze_workspace_agents(tmp_path: Path) -> None:
    make_workspace(tmp_path, {"agent-a": "draft"})
    (tmp_path / "agent-cycle.yaml").unlink()
    assert run(tmp_path, "Write", {"file_path": str(tmp_path / "agents/agent-a/evals/config.yaml"), "content": "x\n"})


def test_creating_the_marker_does_not_unfreeze_the_root_agent(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    (tmp_path / "agent-cycle.yaml").write_text("layout: workspace\nagents: [agent-c]\n", encoding="utf-8")
    assert run(tmp_path, "Write", {"file_path": str(tmp_path / "evals/config.yaml"), "content": "x\n"})
    assert run(tmp_path, "Edit", {"file_path": str(tmp_path / "docs/agent/spec.md"), **CAPABILITY_EDIT})


def test_agent_dirs_freeze_without_any_marker(tmp_path: Path) -> None:
    make_agent(tmp_path, "agents/agent-a", "approved")
    assert run(tmp_path, "Write", {"file_path": str(tmp_path / "agents/agent-a/evals/config.yaml"), "content": "x\n"})


def test_longest_prefix_wins_over_a_built_root(tmp_path: Path) -> None:
    make_agent(tmp_path, status="approved")
    make_agent(tmp_path, "agents/agent-c")
    assert run(tmp_path, "Write",
               {"file_path": str(tmp_path / "agents/agent-c/evals/config.yaml"), "content": "x\n"}) == []
    assert run(tmp_path, "Write", {"file_path": str(tmp_path / "evals/config.yaml"), "content": "x\n"})


@pytest.mark.parametrize("command", [
    "rm *.yaml",
    "rm agent-cycle.*",
    "Rename-Item agent-cycle.yaml old.yaml",
])
def test_marker_removal_by_shell_blocked(tmp_path: Path, command: str) -> None:
    make_workspace(tmp_path, {"agent-a": "draft"})
    assert run(tmp_path, "Bash", {"command": command})


# --- C2: the build.md ratchet

def test_ratchet_build_md_deleted_after_a_prior_call_stays_frozen(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Bash", {"command": "ls"}) == []
    (tmp_path / "docs/agent/build.md").unlink()
    assert run(tmp_path, "Write", {"file_path": str(tmp_path / "evals/config.yaml"), "content": "x\n"})
    assert run(tmp_path, "Edit", {"file_path": str(tmp_path / "docs/agent/spec.md"), **TEST_FILL})
    assert run(tmp_path, "Write",
               {"file_path": str(tmp_path / "docs/agent/build.md"), "content": "---\nstatus: draft\n---\n"})


def test_ratchet_recorded_agent_without_build_md_blocks_test_column(tmp_path: Path) -> None:
    make_workspace(tmp_path, {"agent-a": None})
    (tmp_path / ".claude/hooks").mkdir(parents=True)
    (tmp_path / ".claude/hooks/built-agents.txt").write_text("agents/agent-a/\n", encoding="utf-8")
    assert run(tmp_path, "Edit", {"file_path": str(tmp_path / "agents/agent-a/docs/agent/spec.md"), **TEST_FILL})
    assert run(tmp_path, "Write", {"file_path": str(tmp_path / "agents/agent-a/evals/config.yaml"), "content": "x\n"})


def test_ratchet_workspace_build_md_deleted_by_glob(tmp_path: Path) -> None:
    make_workspace(tmp_path, {"agent-a": "draft", "agent-b": None})
    assert run(tmp_path, "Bash", {"command": "rm agents/agent-a/docs/agent/b*.md"})
    (tmp_path / "agents/agent-a/docs/agent/build.md").unlink()   # an invisible form did it
    assert run(tmp_path, "Write", {"file_path": str(tmp_path / "agents/agent-a/evals/config.yaml"), "content": "x\n"})
    assert run(tmp_path, "Write",
               {"file_path": str(tmp_path / "agents/agent-b/evals/config.yaml"), "content": "x\n"}) == []


def test_ratchet_renamed_agent_folder_stays_frozen(tmp_path: Path) -> None:
    make_workspace(tmp_path, {"agent-a": "approved"})
    assert run(tmp_path, "Bash", {"command": "ls"}) == []
    (tmp_path / "agents/agent-a").rename(tmp_path / "agents/old")
    (tmp_path / "agents/agent-a/evals").mkdir(parents=True)
    assert run(tmp_path, "Write", {"file_path": str(tmp_path / "agents/agent-a/evals/config.yaml"), "content": "x\n"})
    assert run(tmp_path, "Write", {"file_path": str(tmp_path / "agents/old/evals/config.yaml"), "content": "x\n"})


def test_ratchet_file_lists_built_agents(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    make_agent(tmp_path, "agents/agent-a", "approved")
    make_agent(tmp_path, "agents/agent-b")
    run(tmp_path, "Bash", {"command": "ls"})
    text = (tmp_path / ".claude/hooks/built-agents.txt").read_text(encoding="utf-8")
    assert text.split() == [".", "agents/agent-a/"]


def test_ratchet_file_is_protected(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    ratchet = tmp_path / ".claude/hooks/built-agents.txt"
    assert run(tmp_path, "Write", {"file_path": str(ratchet), "content": ""})
    assert run(tmp_path, "Bash", {"command": "echo > .claude/hooks/built-agents.txt"})


def test_ratchet_write_failure_still_decides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_agent(tmp_path, status="draft")

    def refuse(src: str, dst: str) -> None:
        raise PermissionError(dst)

    monkeypatch.setattr(os, "replace", refuse)
    hits = run(tmp_path, "Write", {"file_path": str(tmp_path / "evals/config.yaml"), "content": "x\n"})
    assert hits == ["evals/config.yaml"]


def test_ratchet_unreadable_blocks_through_main(tmp_path: Path) -> None:
    make_agent(tmp_path)
    (tmp_path / ".claude/hooks").mkdir(parents=True)
    (tmp_path / ".claude/hooks/built-agents.txt").write_bytes(b"\xff\xfe\x00bad")
    payload = {"tool_name": "Write", "cwd": str(tmp_path),
               "tool_input": {"file_path": str(tmp_path / "src/a.py"), "content": "x"}}
    assert _run_hook_bytes(payload, tmp_path).returncode == 2


# --- I1: canonical file-tool paths

@pytest.mark.skipif(os.name != "nt", reason="alternate data streams are an NTFS feature")
def test_alternate_data_stream_suffix_blocked(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    hits = run(tmp_path, "Write", {"file_path": str(tmp_path / "docs/agent/design.md") + "::$DATA", "content": "x\n"})
    assert hits and "unsafe path" in hits[0]


def test_device_prefix_is_stripped(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Write", {"file_path": "\\\\?\\" + str(tmp_path / "evals" / "config.yaml"), "content": "x\n"})
    assert run(tmp_path, "Write", {"file_path": "//?/" + (tmp_path / "evals/config.yaml").as_posix(), "content": "x\n"})


def test_file_tool_paths_are_not_variable_expanded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_agent(tmp_path, status="draft")
    monkeypatch.setenv("GUARD_NESTED", "a/b")
    path = str(tmp_path) + "/$GUARD_NESTED/../evals/config.yaml"
    assert run(tmp_path, "Write", {"file_path": path, "content": "x\n"})


@pytest.mark.skipif(os.name != "nt", reason="Win32 drops trailing dots and spaces")
@pytest.mark.parametrize("suffix", ["docs/agent/design.md.", "evals./config.yaml", "evals /config.yaml"])
def test_trailing_dots_and_spaces_resolve(tmp_path: Path, suffix: str) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Write", {"file_path": str(tmp_path) + "/" + suffix, "content": "x\n"})


def _can_make_junction() -> bool:
    try:
        import _winapi
    except ImportError:
        return False
    return hasattr(_winapi, "CreateJunction")


@pytest.mark.skipif(not _can_make_junction(), reason="needs Windows junctions")
def test_junction_outside_the_repo_resolves(tmp_path: Path) -> None:
    import _winapi
    repo = tmp_path / "repo"
    make_agent(repo, status="draft")
    (tmp_path / "out").mkdir()
    _winapi.CreateJunction(str(repo / "evals"), str(tmp_path / "out" / "link"))
    assert run(repo, "Write", {"file_path": str(tmp_path / "out/link/config.yaml"), "content": "x\n"})


def _short_name(path: Path) -> str | None:
    if os.name != "nt":
        return None
    import ctypes
    buffer = ctypes.create_unicode_buffer(1024)
    if not ctypes.windll.kernel32.GetShortPathNameW(str(path), buffer, 1024):
        return None
    return buffer.value if Path(buffer.value).name.lower() != path.name.lower() else None


def test_short_8dot3_name_resolves(tmp_path: Path) -> None:
    make_workspace(tmp_path, {"customer-support": "draft"})
    short = _short_name(tmp_path / "agents/customer-support")
    if short is None:
        pytest.skip("8.3 names are not available on this volume")
    assert run(tmp_path, "Write", {"file_path": short + "\\evals\\config.yaml", "content": "x\n"})


# --- I2: shell detector gaps

@pytest.mark.parametrize("command", [
    "Rename-Item docs/agent/build.md old.md",
    "ri -Recurse evals",
    "rni evals old",
    "Clear-Content evals/config.yaml",
    "clc evals/config.yaml",
    "sc evals/config.yaml x",
    "ac evals/config.yaml x",
    "ni evals/new.yaml",
    "erase evals\\config.yaml",
    "rd /s /q evals",
    "robocopy empty evals /MIR",
    "xcopy /y x.yaml evals\\",
    "ln -sf /tmp/x evals/config.yaml",
    "mklink evals\\x.yaml y.yaml",
    "perl -pi -e s/1/2/ evals/config.yaml",
    "perl -i.bak -pe s/1/2/ evals/config.yaml",
    "awk -i inplace 1 evals/config.yaml",
    "sed -e s/1/2/ -i evals/config.yaml",
    "sed --in-place s/1/2/ evals/config.yaml",
    "sed -Ei s/1/2/ evals/config.yaml",
    "git stash push -- evals/config.yaml",
    "git reset --hard HEAD~1 -- evals/config.yaml",
    "git -C evals rm config.yaml",
    "git -C evals checkout HEAD~1 -- config.yaml",
    "git --no-pager checkout HEAD~1 -- evals/config.yaml",
    "bash <<'EOF'\nrm -rf evals\nEOF",
    "cat <<EOF | sh\nrm -rf evals\nEOF",
    "cat <<EOF > out.txt\nEOF\nrm -rf evals\nEOF",
    "rm -rf \\\n  evals",
    "bash -c 'rm -rf evals'",
    "pwsh -Command \"Remove-Item -Recurse evals\"",
    "cmd /c \"del evals\\config.yaml\"",
    "find evals -delete",
    "find . -name '*.yaml' -delete",
    "find evals -name x | xargs rm",
    "rm ev*/config.yaml",
    "rm docs/*/spec.md",
    "rm e\"\"vals/config.yaml",
    "cd /d evals && del config.yaml",
    "Set-Location -Path evals; Remove-Item config.yaml",
    "[IO.File]::WriteAllText(\"evals/config.yaml\", \"x\")",
])
def test_shell_detector_gaps_blocked(tmp_path: Path, command: str) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Bash", {"command": command})


def test_git_dash_c_resolves_from_its_dir(tmp_path: Path) -> None:
    make_workspace(tmp_path, {"agent-a": "draft", "agent-b": None})
    assert run(tmp_path, "Bash", {"command": "git -C agents/agent-a checkout HEAD~1 -- evals/config.yaml"})
    assert run(tmp_path, "Bash", {"command": "git -C agents/agent-b checkout HEAD~1 -- evals/config.yaml"}) == []


# --- I3: no false blocks on everyday build commands

@pytest.mark.parametrize("command", [
    "uv pip install -e . 2>&1 | tail -5",
    "ruff check . 2>&1",
    "python -m pytest . -q 2>&1",
    "cat evals/config.yaml 2>/dev/null",
    "ls evals 2>&1",
    "python run_evals.py evals/ > results.txt",
    "git diff HEAD -- evals/ > /tmp/d.txt",
    'git commit -m "fill Test column in docs/agent/spec.md; rm dead code"',
    "python run_evals.py evals/ && rm -rf build",
    "type evals\\config.yaml 2>NUL",
    "cat <<EOF > notes.txt\nEOF",
    "python -m pytest . -q 2>&1 | tee pytest.log",
    "cp README.md docs/",
])
def test_everyday_build_shell_allowed(tmp_path: Path, command: str) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Bash", {"command": command}) == []


@pytest.mark.parametrize("command", [
    "uv run pytest agents/agent-a 2>&1",
    "cd agents/agent-a && uv pip install -e . 2>&1",
])
def test_everyday_workspace_shell_allowed(tmp_path: Path, command: str) -> None:
    make_workspace(tmp_path, {"agent-a": "draft"})
    assert run(tmp_path, "Bash", {"command": command}) == []


# --- I4: the hook cannot be unregistered

def _settings(root: Path, name: str, content: object) -> Path:
    path = root / ".claude" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2), encoding="utf-8")
    return path


@pytest.mark.parametrize(("content", "allowed"), [
    ({"hooks": {"PreToolUse": [GUARD_ENTRY]}, "permissions": {"allow": ["Bash(ls)"]}}, True),
    ({"permissions": {"allow": ["Bash(ls)"]}}, False),
    ({**SETTINGS_WITH_GUARD, "disableAllHooks": True}, False),
    ({"hooks": {"PreToolUse": [{**GUARD_ENTRY, "matcher": "Read"}]}}, False),
])
def test_settings_json_keeps_the_guard(tmp_path: Path, content: object, allowed: bool) -> None:
    make_agent(tmp_path)
    path = _settings(tmp_path, "settings.json", SETTINGS_WITH_GUARD)
    hits = run(tmp_path, "Write", {"file_path": str(path), "content": json.dumps(content)})
    assert (hits == []) is allowed


def test_settings_json_invalid_json_blocked(tmp_path: Path) -> None:
    make_agent(tmp_path)
    path = _settings(tmp_path, "settings.json", SETTINGS_WITH_GUARD)
    assert run(tmp_path, "Write", {"file_path": str(path), "content": "{not json"})


def test_settings_json_edit_dropping_the_guard_blocked(tmp_path: Path) -> None:
    make_agent(tmp_path)
    path = _settings(tmp_path, "settings.json", SETTINGS_WITH_GUARD)
    assert run(tmp_path, "Edit", {"file_path": str(path), "old_string": "guard_artifacts.py", "new_string": "noop.py"})


def test_settings_json_install_allowed(tmp_path: Path) -> None:
    make_agent(tmp_path)
    hits = run(tmp_path, "Write",
               {"file_path": str(tmp_path / ".claude/settings.json"), "content": json.dumps(SETTINGS_WITH_GUARD)})
    assert hits == []


@pytest.mark.parametrize(("content", "allowed"), [
    ({"permissions": {"allow": ["Bash(ls)"]}}, True),
    ({"disableAllHooks": True}, False),
])
def test_settings_local_json(tmp_path: Path, content: object, allowed: bool) -> None:
    make_agent(tmp_path)
    hits = run(tmp_path, "Write",
               {"file_path": str(tmp_path / ".claude/settings.local.json"), "content": json.dumps(content)})
    assert (hits == []) is allowed


def test_user_settings_cannot_disable_hooks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, home = tmp_path / "repo", tmp_path / "home"
    make_agent(repo)
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("HOME", str(home))
    path = str(home / ".claude/settings.json")
    assert run(repo, "Write", {"file_path": path, "content": '{"disableAllHooks": true}'})
    assert run(repo, "Write", {"file_path": path, "content": '{"model": "x"}'}) == []


@pytest.mark.parametrize("command", [
    "echo {} > .claude/settings.json",
    "rm .claude/settings.local.json",
    "cp x.json .claude/settings.json",
    "echo '{\"disableAllHooks\": true}' > ~/.claude/settings.json",
])
def test_shell_writes_on_settings_blocked(tmp_path: Path, command: str) -> None:
    make_agent(tmp_path)
    assert run(tmp_path, "Bash", {"command": command})


# --- M1, M2: reading state

def test_unreadable_marker_blocks_any_change(tmp_path: Path) -> None:
    make_workspace(tmp_path, {"agent-a": None})
    (tmp_path / "agent-cycle.yaml").write_bytes(b"layout: workspace\nagents: [agent-a]\n\xff\n")
    assert run(tmp_path, "Write",
               {"file_path": str(tmp_path / "agent-cycle.yaml"),
                "content": "layout: workspace\nagents: [agent-a, agent-c]\n"})


def test_read_text_missing_vs_unreadable(tmp_path: Path) -> None:
    assert guard.read_text(str(tmp_path / "missing.md")) is None
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(guard.Unreadable):
        guard.read_text(str(bad))


@pytest.mark.parametrize("frontmatter", [
    "﻿---\nstatus: draft\n---\n",
    "---\nstatus: \"draft\"\n---\n",
    "---\nstatus: 'draft'  # still drafting\n---\n",
])
def test_build_status_variants_read_as_draft(tmp_path: Path, frontmatter: str) -> None:
    make_agent(tmp_path)
    (tmp_path / "docs/agent/build.md").write_text(frontmatter, encoding="utf-8")
    assert run(tmp_path, "Edit", {"file_path": str(tmp_path / "docs/agent/spec.md"), **TEST_FILL}) == []


# --- M3, M5, M6

def test_snapshot_keeps_the_on_disk_case(tmp_path: Path) -> None:
    make_agent(tmp_path, "agents/Agent-A", "draft")
    snapshot = guard.take_snapshot(str(tmp_path))
    folders = {agent.prefix: agent.folder for agent in snapshot.agents}
    assert folders["agents/agent-a/"] == "agents/Agent-A/"
    assert run(tmp_path, "Write", {"file_path": str(tmp_path / "agents/Agent-A/evals/config.yaml"), "content": "x\n"})


@pytest.mark.parametrize("tool_input", [
    {"command": ["rm", "-rf", "evals"]},
    {"file_path": ["evals/config.yaml"], "content": "x"},
    {"file_path": 7, "content": "x"},
])
def test_non_string_inputs_fail_closed(tmp_path: Path, tool_input: dict[str, object]) -> None:
    make_agent(tmp_path, status="draft")
    with pytest.raises(ValueError):
        guard.evaluate({"tool_name": "Bash", "tool_input": tool_input, "cwd": str(tmp_path)}, str(tmp_path))


def test_one_disk_snapshot_per_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_workspace(tmp_path, {"agent-a": "draft", "agent-b": None})
    calls: list[str] = []
    original = guard.build_status

    def counting(root: str, folder: str) -> str | None:
        calls.append(folder)
        return original(root, folder)

    monkeypatch.setattr(guard, "build_status", counting)
    assert run(tmp_path, "Bash", {"command": "rm a b c d e f g h agents/agent-a/evals/config.yaml"})
    assert len(calls) == 3


# --- the entry point, through main()

def test_main_reads_utf8_bytes_and_answers_in_ascii(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    blocked = {"tool_name": "Write", "cwd": str(tmp_path),
               "tool_input": {"file_path": str(tmp_path / "evals/configuración.yaml"), "content": "ñ"}}
    proc = _run_hook_bytes(blocked, tmp_path)
    assert proc.returncode == 2
    message = proc.stderr.decode("ascii")
    assert "configuraci\\xf3n" in message
    allowed = {"tool_name": "Write", "cwd": str(tmp_path),
               "tool_input": {"file_path": str(tmp_path / "src/módulo.py"), "content": "ñ"}}
    assert _run_hook_bytes(allowed, tmp_path).returncode == 0


def test_main_resolves_from_the_payload_cwd(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    make_workspace(repo, {"agent-a": "draft", "agent-b": None})
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    blocked = {"tool_name": "Bash", "cwd": str(repo / "agents/agent-a"),
               "tool_input": {"command": "rm evals/config.yaml"}}
    assert _run_hook_bytes(blocked, repo, cwd=elsewhere).returncode == 2
    allowed = {"tool_name": "Bash", "cwd": str(repo / "agents/agent-b"),
               "tool_input": {"command": "rm evals/config.yaml"}}
    assert _run_hook_bytes(allowed, repo, cwd=elsewhere).returncode == 0


def test_fd_redirects_are_not_file_writes() -> None:
    for command in ("x 2>&1", "x >&2", "x 2>/dev/null", "x &>/dev/null", "x 2> NUL", "x *>$null",
                    "x >/dev/null 2>&1"):
        assert ">" not in guard.FD_REDIRECT.sub(" ", command), command
    assert ">" in guard.FD_REDIRECT.sub(" ", "x > nul.txt")


@pytest.mark.skipif(os.name != "nt", reason="NUL is a Windows device name")
def test_nul_device_is_outside_the_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_agent(tmp_path, status="draft")
    monkeypatch.chdir(tmp_path / "evals")
    assert guard.rel_to_repo(guard.canonical(str(tmp_path / "NUL")), guard.canonical(str(tmp_path))) is None
    assert run(tmp_path, "Bash", {"command": "echo x > NUL"}) == []


@pytest.mark.parametrize(("raw", "expected"), [
    ("//?/C:/repo/evals", "C:/repo/evals"),
    ("//./c:/repo", "c:/repo"),
    ("//?/UNC/server/share/x", "//server/share/x"),
    ("//./NUL", "//./NUL"),
    ("C:/repo", "C:/repo"),
])
def test_strip_device_prefix(raw: str, expected: str) -> None:
    assert guard.strip_device_prefix(raw) == expected


# === round 2: second security re-review

# --- C1: path-less destructive git verbs act on the current directory

def test_stub_revert_then_git_clean_blocked_at_the_clean_step(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Bash", {"command": "ls"}) == []
    assert run(tmp_path, "Bash", {"command": "git revert --no-edit HEAD"})
    (tmp_path / "docs/agent/build.md").unlink()        # the revert happened anyway
    assert run(tmp_path, "Bash", {"command": "git clean -fdx"})


@pytest.mark.parametrize("command", [
    "git clean -fdx",
    "git clean -n",
    "git -C . clean -fd",
    "git stash -u",
    "git stash push --include-untracked",
    "git stash --all",
    "git stash push -a -m wip",
    "git reset --hard",
])
def test_pathless_destructive_git_blocked(tmp_path: Path, command: str) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Bash", {"command": command})


def test_git_clean_in_an_agent_folder_blocked(tmp_path: Path) -> None:
    make_workspace(tmp_path, {"agent-a": "draft"})
    assert run(tmp_path, "Bash", {"command": "git clean -fd"}, cwd=tmp_path / "agents/agent-a")


@pytest.mark.parametrize("command", [
    "git clean -fd src",
    "git stash",
    "git stash list",
    "git reset HEAD~1",
])
def test_scoped_or_safe_git_allowed(tmp_path: Path, command: str) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Bash", {"command": command}) == []


# --- C2: git verbs that rewrite the tree are the human's while any agent is built

@pytest.mark.parametrize("command", [
    "git checkout HEAD~1 -- .",
    "git checkout HEAD~1 -- docs",
    "git checkout main -- evals/config.yaml",
    "git checkout HEAD~1 docs/agent/spec.md",
    "git checkout HEAD~1 -- ':/'",
    "git restore --source HEAD~1 .",
    "git restore -s HEAD~1 evals/",
    "git restore --source=HEAD~1 docs/agent/spec.md",
    "git apply fix.patch",
    "git am fix.mbox",
    "git reset --hard HEAD~1",
    "git revert HEAD",
    "git cherry-pick abc123",
    "git merge main",
    "git pull",
    "git rebase main",
    "git stash pop",
    "git stash apply",
])
def test_tree_rewriting_git_blocked_while_built(tmp_path: Path, command: str) -> None:
    make_workspace(tmp_path, {"agent-a": "draft", "agent-b": None})
    assert run(tmp_path, "Bash", {"command": command}, cwd=tmp_path / "agents/agent-a")


@pytest.mark.parametrize("command", [
    "git restore src/app.py",
    "git checkout -- src/x.py",
    "git checkout main",
    "git checkout -b feature",
    "git switch main",
    "git restore --source HEAD~1 src/app.py",
    "git checkout HEAD~1 -- src/app.py",
    "git restore --staged evals/config.yaml",
])
def test_scoped_git_checkout_allowed_while_built(tmp_path: Path, command: str) -> None:
    make_agent(tmp_path, status="draft")
    hits = run(tmp_path, "Bash", {"command": command})
    if command.endswith("--staged evals/config.yaml"):
        assert hits                    # the pathspec still names a frozen file
    else:
        assert hits == []


@pytest.mark.parametrize("command", ["git pull", "git merge main", "git stash pop", "git apply fix.patch"])
def test_tree_rewriting_git_allowed_before_any_build(tmp_path: Path, command: str) -> None:
    make_agent(tmp_path)
    assert run(tmp_path, "Bash", {"command": command}, cwd=tmp_path / "src") == []


# --- I1: the pinned, isolated registration

def test_main_runs_isolated(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)}
    blocked = json.dumps({"tool_name": "Write", "cwd": str(tmp_path),
                          "tool_input": {"file_path": str(tmp_path / "evals/config.yaml"), "content": "x"}})
    proc = subprocess.run([sys.executable, "-I", "-S", str(HOOK)], input=blocked.encode("utf-8"),
                          capture_output=True, env=env, check=False)
    assert proc.returncode == 2
    assert b"evals/config.yaml" in proc.stderr


def test_hook_pins_the_registration_command() -> None:
    assert GUARD_COMMAND == guard.GUARD_COMMAND


@pytest.mark.parametrize(("before", "after", "allowed"), [
    (SETTINGS_WITH_GUARD, {"hooks": {"PreToolUse": [OLD_GUARD_ENTRY]}}, False),   # flags stripped
    ({}, {"hooks": {"PreToolUse": [OLD_GUARD_ENTRY]}}, False),                    # install, unpinned
    ({}, SETTINGS_WITH_GUARD, True),                                              # install, pinned
    ({"hooks": {"PreToolUse": [OLD_GUARD_ENTRY]}}, SETTINGS_WITH_GUARD, False),   # upgrade: the human's
    (SETTINGS_WITH_GUARD, {**SETTINGS_WITH_GUARD, "env": {"PYTHONPATH": "x"}}, False),
    ({**SETTINGS_WITH_GUARD, "env": {"A": "1"}}, {**SETTINGS_WITH_GUARD, "env": {"A": "2"}}, False),
    ({**SETTINGS_WITH_GUARD, "env": {"A": "1"}}, {**SETTINGS_WITH_GUARD, "env": {"A": "1"}, "model": "x"}, True),
])
def test_settings_pin_the_guard_and_env(tmp_path: Path, before: object, after: object, allowed: bool) -> None:
    make_agent(tmp_path)
    path = _settings(tmp_path, "settings.json", before)
    hits = run(tmp_path, "Write", {"file_path": str(path), "content": json.dumps(after)})
    assert (hits == []) is allowed


def test_settings_local_env_blocked(tmp_path: Path) -> None:
    make_agent(tmp_path)
    hits = run(tmp_path, "Write", {"file_path": str(tmp_path / ".claude/settings.local.json"),
                                   "content": json.dumps({"env": {"PYTHONSTARTUP": "x.py"}})})
    assert hits


# --- I2: the writing verb comes from parsed words

@pytest.mark.parametrize("command", [
    "/bin/rm -rf evals",
    "rm.exe -rf evals",
    "\"rm\" -rf evals",
    "r''m -rf evals",
    "\\rm -rf evals",
    "C:/Windows/System32/robocopy.exe empty evals /MIR",
    "FOO=1 rm -rf evals",
    "sudo -u root rm -rf evals",
    "env rm -rf evals",
    "timeout 5 rm -rf evals",
    "echo $(rm -rf evals)",
    "eval 'rm -rf evals'",
    "Invoke-Expression 'Remove-Item -Recurse evals'",
    "Get-ChildItem evals | Remove-Item",
    "Remove-Item (Join-Path evals config.yaml)",
    "ls | xargs rm -rf",
    "find . -name x -exec rm {} +",
])
def test_writing_verb_from_parsed_words(tmp_path: Path, command: str) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Bash", {"command": command})


# --- I3: glob reach by depth

@pytest.mark.parametrize("command", ["rm -rf */__pycache__", "rm -rf **/__pycache__"])
def test_deep_globs_allowed_before_build(tmp_path: Path, command: str) -> None:
    make_agent(tmp_path)
    assert run(tmp_path, "Bash", {"command": command}) == []


@pytest.mark.parametrize("command", ["rm -rf docs/_build/*", "rm docs/*.html"])
def test_deep_globs_allowed_after_build(tmp_path: Path, command: str) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Bash", {"command": command}) == []


@pytest.mark.parametrize("command", [
    "rm -rf agents/*/__pycache__",
    "rm -rf agents/*/node_modules",
    "cd agents/agent-a && rm -f *.log",
])
def test_deep_globs_allowed_in_a_workspace(tmp_path: Path, command: str) -> None:
    make_workspace(tmp_path, {"agent-a": "draft", "agent-b": "approved"})
    assert run(tmp_path, "Bash", {"command": command}) == []


@pytest.mark.parametrize("command", ["rm -rf ev*", "rm docs/agent/*.md", "rm agent-cycle.*", "rm -rf d*"])
def test_shallow_globs_still_blocked(tmp_path: Path, command: str) -> None:
    make_agent(tmp_path, status="draft")
    (tmp_path / "agent-cycle.yaml").write_text("layout: workspace\nagents: []\n", encoding="utf-8")
    assert run(tmp_path, "Bash", {"command": command})


# --- I4: hard links to frozen files

def _hard_link(source: Path, link: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, link)
    except OSError as exc:
        pytest.skip(f"hard links are not available here ({exc})")


def test_hard_link_to_a_frozen_file_blocked(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    _hard_link(tmp_path / "evals/config.yaml", tmp_path / "src/link.yaml")
    assert run(tmp_path, "Write", {"file_path": str(tmp_path / "src/link.yaml"), "content": "x\n"})
    assert run(tmp_path, "Bash", {"command": "echo x > src/link.yaml"})


def test_hard_link_between_free_files_allowed(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    (tmp_path / "src").mkdir()
    (tmp_path / "src/a.txt").write_text("a\n", encoding="utf-8")
    _hard_link(tmp_path / "src/a.txt", tmp_path / "src/b.txt")
    assert run(tmp_path, "Write", {"file_path": str(tmp_path / "src/b.txt"), "content": "x\n"}) == []


@pytest.mark.parametrize("command", [
    "fsutil hardlink create src/l.yaml evals/config.yaml",
    "ln evals/config.yaml src/l.yaml",
])
def test_creating_links_to_frozen_files_blocked(tmp_path: Path, command: str) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Bash", {"command": command})


# --- M1: ANSI-C quoting

def test_ansi_c_quoted_names_are_read(tmp_path: Path) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Bash", {"command": "rm -rf $'evals'"})


# --- M2, M3: only write targets are judged

@pytest.mark.parametrize("command", [
    "cp ~/.claude/settings.json ~/backup.json",
    "Get-Content evals/config.yaml | Out-File out.txt",
    "cp evals/config.yaml /tmp/",
    "cp -r evals /tmp/evals-copy",
    "Copy-Item evals/config.yaml -Destination /tmp/x.yaml",
    "robocopy evals /tmp/backup",
    "cat evals/config.yaml | tee /tmp/x.txt",
    "Set-Content out.txt -Value evals/config.yaml",
    "dd if=evals/config.yaml of=/tmp/x",
    "echo rm -rf evals",
])
def test_reading_frozen_files_allowed(tmp_path: Path, command: str) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Bash", {"command": command}) == []


@pytest.mark.parametrize("command", [
    "cp .claude/settings.example.json .claude/settings.local.json",
    "Copy-Item x.yaml -Destination evals/x.yaml",
    "Copy-Item x.yaml evals/x.yaml",
    "cp -t evals x.yaml",
    "Set-Content -Path evals/config.yaml -Value x",
    "Out-File -FilePath docs/agent/design.md",
    "robocopy evals /tmp/b /MOV",
    "dd if=/tmp/x of=evals/config.yaml",
    "rsync -a /tmp/x/ evals/",
])
def test_write_targets_still_blocked(tmp_path: Path, command: str) -> None:
    make_agent(tmp_path, status="draft")
    assert run(tmp_path, "Bash", {"command": command})


# === final review: the user settings file guards only PATH and PYTHON* in env

@pytest.mark.parametrize(("before", "after", "allowed"), [
    ({"env": {"FOO": "1"}}, {"env": {"FOO": "1", "BAR": "2"}}, True),
    ({"env": {"PATH": "/usr/bin"}}, {"env": {"PATH": "/tmp/evil:/usr/bin"}}, False),
    ({"env": {"FOO": "1"}}, {"env": {"FOO": "1", "PYTHONPATH": "/tmp/x"}}, False),
    ({"env": {"PYTHONSTARTUP": "x.py"}}, {"env": {}}, False),
])
def test_user_settings_env_rule(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                before: object, after: object, allowed: bool) -> None:
    repo, home = tmp_path / "repo", tmp_path / "home"
    make_agent(repo)
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("HOME", str(home))
    path = home / ".claude/settings.json"
    path.write_text(json.dumps(before), encoding="utf-8")
    hits = run(repo, "Write", {"file_path": str(path), "content": json.dumps(after)})
    assert (hits == []) is allowed


def test_repo_settings_env_rule_unchanged(tmp_path: Path) -> None:
    make_agent(tmp_path)
    path = _settings(tmp_path, "settings.json", {"env": {"FOO": "1"}})
    assert run(tmp_path, "Write", {"file_path": str(path), "content": json.dumps({"env": {"FOO": "1", "BAR": "2"}})})
