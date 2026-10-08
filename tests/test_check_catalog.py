"""Tests for scripts/check_catalog.py — the stack catalog consistency checker."""
from datetime import date
from pathlib import Path

import pytest

import check_catalog

VALID_CARD = """---
id: demo
name: Demo
level: framework
nests_on: none
package: demo-pkg
version_verified: 1.2.3
license: MIT
ts_sdk: none
verified_on: 2026-10-07
status: active
---

# Demo

## 1. What it is
A demo framework used only by the checker tests.

## 2. Filter attributes
| Attribute | Value | Source |
|---|---|---|
| model_portability | any | https://example.com/models |
| a2a | none | https://example.com/a2a |
| mcp_client | native | https://example.com/mcp |
| deploy_constraints | none | https://example.com/deploy |
| default_egress | none | https://example.com/telemetry |
| stability | semver-stable | https://example.com/versioning |

## 3. Seam mapping
| Seam | Support | How | Source |
|---|---|---|---|
| sessions | adapter | Postgres store behind the repository interface | https://example.com/sessions |
| hitl_gate | native | approval flag per tool | https://example.com/hitl |
| step_cap | native | request limit | https://example.com/limits |
| tool_call_cap | custom | counter in the loop | https://example.com/limits |
| model_provider | native | provider:model strings | https://example.com/models |
| telemetry | native | OTel GenAI spans | https://example.com/otel |
| eval_runner | adapter | pytest harness with a model double | https://example.com/testing |
| deploy | native | plain library in a container | https://example.com/deploy |

## 4. Known traps
- [churn] Pin the exact version. Source: https://example.com/releases

## 5. Pick when / avoid when
Pick when running the checker tests. Source: https://example.com/guide

## 6. Build binding
`skills/build/references/bindings/demo.md`
"""

VALID_INDEX = """# Stack catalog index

## Filter table
| id | level | nests_on | model_portability | a2a | mcp_client | stability | default_egress | verified_on |
|---|---|---|---|---|---|---|---|---|
| demo | framework | none | any | none | native | semver-stable | none | 2026-10-07 |
"""

VALID_BINDING = """---
card: demo
version_pinned: 1.2.3
---

# Demo — build binding

## Sessions and state
Postgres.

## HITL gate
Approval flag.

## Caps
Request limit plus own counter.

## Model provider
provider:model.

## Telemetry
OTel.

## Eval runner mapping
pytest harness.

## A2A and MCP
None.

## Pinned version and traps
demo-pkg==1.2.3
"""


def write_catalog(
    root: Path,
    card: str = VALID_CARD,
    index: str = VALID_INDEX,
    binding: str | None = VALID_BINDING,
    card_name: str = "demo.md",
) -> None:
    stacks = root / check_catalog.STACKS_DIR
    bindings = root / check_catalog.BINDINGS_DIR
    stacks.mkdir(parents=True)
    bindings.mkdir(parents=True)
    (stacks / card_name).write_text(card, encoding="utf-8")
    (stacks / check_catalog.INDEX_NAME).write_text(index, encoding="utf-8")
    (stacks / "_card-template.md").write_text("template, ignored", encoding="utf-8")
    if binding is not None:
        (bindings / "demo.md").write_text(binding, encoding="utf-8")


def test_valid_catalog_passes(tmp_path: Path) -> None:
    write_catalog(tmp_path)
    result = check_catalog.check_catalog(tmp_path, as_of=None)
    assert result.problems == []
    assert result.card_count == 1


def test_seam_row_without_url_fails(tmp_path: Path) -> None:
    card = VALID_CARD.replace("| https://example.com/hitl |", "| docs page |")
    write_catalog(tmp_path, card=card)
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("hitl_gate" in p and "URL" in p for p in problems)


def test_missing_seam_fails(tmp_path: Path) -> None:
    card = VALID_CARD.replace(
        "| deploy | native | plain library in a container | https://example.com/deploy |\n", ""
    )
    write_catalog(tmp_path, card=card)
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("seam 'deploy' missing" in p for p in problems)


def test_disallowed_filter_value_fails(tmp_path: Path) -> None:
    card = VALID_CARD.replace("| a2a | none |", "| a2a | maybe |")
    index = VALID_INDEX.replace("| any | none | native |", "| any | maybe | native |")
    write_catalog(tmp_path, card=card, index=index)
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("a2a" in p and "maybe" in p for p in problems)


def test_bad_portability_value_fails(tmp_path: Path) -> None:
    card = VALID_CARD.replace("| model_portability | any |", "| model_portability | anthropic |")
    index = VALID_INDEX.replace("| none | any |", "| none | anthropic |")
    write_catalog(tmp_path, card=card, index=index)
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("model_portability" in p for p in problems)


def test_untagged_trap_fails(tmp_path: Path) -> None:
    card = VALID_CARD.replace("- [churn] Pin", "- Pin")
    write_catalog(tmp_path, card=card)
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("trap" in p for p in problems)


def test_index_value_mismatch_fails(tmp_path: Path) -> None:
    index = VALID_INDEX.replace("| semver-stable |", "| pre-1.0 |")
    write_catalog(tmp_path, index=index)
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("stability" in p and "index" in p for p in problems)


def test_active_card_missing_from_index_fails(tmp_path: Path) -> None:
    index = VALID_INDEX.split("| demo |")[0]
    write_catalog(tmp_path, index=index)
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("demo" in p and "missing from" in p for p in problems)


def test_draft_card_in_index_fails(tmp_path: Path) -> None:
    card = VALID_CARD.replace("status: active", "status: draft")
    write_catalog(tmp_path, card=card)
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("draft" in p for p in problems)


def test_draft_card_needs_no_binding(tmp_path: Path) -> None:
    card = VALID_CARD.replace("status: active", "status: draft")
    index = VALID_INDEX.split("| demo |")[0]
    write_catalog(tmp_path, card=card, index=index, binding=None)
    assert check_catalog.check_catalog(tmp_path, as_of=None).problems == []


def test_missing_binding_fails(tmp_path: Path) -> None:
    write_catalog(tmp_path, binding=None)
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("binding" in p and "missing" in p for p in problems)


def test_binding_version_drift_fails(tmp_path: Path) -> None:
    binding = VALID_BINDING.replace("version_pinned: 1.2.3", "version_pinned: 1.2.2")
    write_catalog(tmp_path, binding=binding)
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("version_pinned" in p for p in problems)


def test_card_id_must_match_filename(tmp_path: Path) -> None:
    write_catalog(tmp_path, card_name="other.md")
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("filename" in p for p in problems)


def test_stale_card_reported_not_failing(tmp_path: Path) -> None:
    write_catalog(tmp_path)
    result = check_catalog.check_catalog(tmp_path, as_of=date(2027, 3, 1))
    assert result.problems == []
    assert result.stale == ["demo"]


def test_fresh_card_not_stale(tmp_path: Path) -> None:
    write_catalog(tmp_path)
    result = check_catalog.check_catalog(tmp_path, as_of=date(2026, 12, 1))
    assert result.stale == []


def test_missing_stacks_dir_fails(tmp_path: Path) -> None:
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("stacks directory" in p for p in problems)


@pytest.mark.parametrize(("break_it", "expected_code"), [(False, 0), (True, 1)])
def test_main_exit_code(tmp_path: Path, break_it: bool, expected_code: int) -> None:
    binding = None if break_it else VALID_BINDING
    write_catalog(tmp_path, binding=binding)
    assert check_catalog.main(["--root", str(tmp_path)]) == expected_code


# --- post-review hardening ---------------------------------------------------


def test_card_without_id_reports_problem_not_crash(tmp_path: Path) -> None:
    card = VALID_CARD.replace("id: demo\n", "")
    write_catalog(tmp_path, card=card)
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("frontmatter 'id' missing" in p for p in problems)


def test_non_utf8_card_reported_unreadable(tmp_path: Path) -> None:
    write_catalog(tmp_path)
    stacks = tmp_path / check_catalog.STACKS_DIR
    (stacks / "demo.md").write_bytes(VALID_CARD.encode("utf-8") + b"\xe9")
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("unreadable" in p for p in problems)


def test_non_utf8_binding_reported_unreadable(tmp_path: Path) -> None:
    write_catalog(tmp_path)
    bindings = tmp_path / check_catalog.BINDINGS_DIR
    (bindings / "demo.md").write_bytes(VALID_BINDING.encode("utf-8") + b"\xe9")
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("unreadable" in p for p in problems)


def test_non_utf8_index_reported_unreadable(tmp_path: Path) -> None:
    write_catalog(tmp_path)
    stacks = tmp_path / check_catalog.STACKS_DIR
    (stacks / check_catalog.INDEX_NAME).write_bytes(VALID_INDEX.encode("utf-8") + b"\xe9")
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("unreadable" in p for p in problems)


def test_utf8_bom_card_passes(tmp_path: Path) -> None:
    write_catalog(tmp_path)
    stacks = tmp_path / check_catalog.STACKS_DIR
    (stacks / "demo.md").write_bytes(b"\xef\xbb\xbf" + VALID_CARD.encode("utf-8"))
    assert check_catalog.check_catalog(tmp_path, as_of=None).problems == []


def test_hash_in_frontmatter_value_kept(tmp_path: Path) -> None:
    card = VALID_CARD.replace("name: Demo", "name: C# Agents")
    write_catalog(tmp_path, card=card)
    assert check_catalog.parse_frontmatter(card)["name"] == "C# Agents"
    assert check_catalog.check_catalog(tmp_path, as_of=None).problems == []


def test_frontmatter_trailing_comment_stripped() -> None:
    meta = check_catalog.parse_frontmatter("---\nstatus: active  # live\n---\n")
    assert meta == {"status": "active"}


def test_quoted_version_matches_binding(tmp_path: Path) -> None:
    card = VALID_CARD.replace("version_verified: 1.2.3", 'version_verified: "1.2.3"')
    write_catalog(tmp_path, card=card)
    assert check_catalog.check_catalog(tmp_path, as_of=None).problems == []


def test_heading_with_trailing_spaces_found(tmp_path: Path) -> None:
    card = VALID_CARD.replace("## 1. What it is\n", "## 1. What it is   \n")
    write_catalog(tmp_path, card=card)
    assert check_catalog.check_catalog(tmp_path, as_of=None).problems == []


def test_binding_last_heading_at_eof_without_newline_passes(tmp_path: Path) -> None:
    binding = VALID_BINDING.replace("demo-pkg==1.2.3\n", "").rstrip("\n")
    assert binding.endswith("## Pinned version and traps")
    write_catalog(tmp_path, binding=binding)
    assert check_catalog.check_catalog(tmp_path, as_of=None).problems == []


def test_duplicate_filter_attribute_fails(tmp_path: Path) -> None:
    card = VALID_CARD.replace(
        "| a2a | none | https://example.com/a2a |\n",
        "| a2a | none | https://example.com/a2a |\n| a2a | none | https://example.com/a2a |\n",
    )
    write_catalog(tmp_path, card=card)
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("duplicate" in p and "a2a" in p for p in problems)


def test_duplicate_seam_fails(tmp_path: Path) -> None:
    row = "| deploy | native | plain library in a container | https://example.com/deploy |\n"
    write_catalog(tmp_path, card=VALID_CARD.replace(row, row + row))
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("duplicate" in p and "deploy" in p for p in problems)


def test_duplicate_index_id_fails(tmp_path: Path) -> None:
    row = "| demo | framework | none | any | none | native | semver-stable | none | 2026-10-07 |\n"
    write_catalog(tmp_path, index=VALID_INDEX + row)
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("duplicate" in p and "demo" in p for p in problems)


def test_compact_date_fails(tmp_path: Path) -> None:
    card = VALID_CARD.replace("verified_on: 2026-10-07", "verified_on: 20261007")
    write_catalog(tmp_path, card=card)
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("verified_on" in p and "YYYY-MM-DD" in p for p in problems)


def test_sections_out_of_order_fails(tmp_path: Path) -> None:
    card = VALID_CARD.replace("## 1. What it is", "## 9. TMP").replace(
        "## 2. Filter attributes", "## 1. What it is"
    ).replace("## 9. TMP", "## 2. Filter attributes")
    write_catalog(tmp_path, card=card)
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("out of order" in p for p in problems)


def test_bad_level_enum_fails(tmp_path: Path) -> None:
    card = VALID_CARD.replace("level: framework", "level: lib")
    write_catalog(tmp_path, card=card)
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("level" in p and "lib" in p for p in problems)


def test_binding_wrong_card_fails(tmp_path: Path) -> None:
    binding = VALID_BINDING.replace("card: demo", "card: other")
    write_catalog(tmp_path, binding=binding)
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("card='other'" in p for p in problems)


def test_index_row_wrong_cell_count_fails(tmp_path: Path) -> None:
    index = VALID_INDEX + "| demo | framework |\n"
    write_catalog(tmp_path, index=index)
    problems = check_catalog.check_catalog(tmp_path, as_of=None).problems
    assert any("cells" in p for p in problems)


def test_empty_catalog_passes(tmp_path: Path) -> None:
    stacks = tmp_path / check_catalog.STACKS_DIR
    stacks.mkdir(parents=True)
    (stacks / check_catalog.INDEX_NAME).write_text(VALID_INDEX.split("| demo |")[0], encoding="utf-8")
    result = check_catalog.check_catalog(tmp_path, as_of=None)
    assert result.problems == []
    assert result.card_count == 0


@pytest.mark.parametrize(("break_it", "prefix"), [(False, "PASS:"), (True, "FAIL:")])
def test_main_prints_verdict_in_ascii(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], break_it: bool, prefix: str
) -> None:
    write_catalog(tmp_path, binding=None if break_it else VALID_BINDING)
    check_catalog.main(["--root", str(tmp_path)])
    out = capsys.readouterr().out
    out.encode("ascii")
    assert out.strip().splitlines()[-1].startswith(prefix)
