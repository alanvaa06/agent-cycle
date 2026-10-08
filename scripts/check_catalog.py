"""Validate the agent-cycle stack catalog: cards, _index.md and build bindings agree.

Usage:
    python scripts/check_catalog.py [--root PATH] [--as-of YYYY-MM-DD]

Prints one line per problem and a final PASS/FAIL verdict; exits 1 on FAIL.
--as-of lists cards verified more than STALE_AFTER_DAYS before that date.
Staleness is informational (refresh's work queue), never a FAIL.
Console output is ASCII-only (Windows cp1252 consoles).
"""
from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

STACKS_DIR = Path("skills/design/references/stacks")
BINDINGS_DIR = Path("skills/build/references/bindings")
INDEX_NAME = "_index.md"
INDEX_HEADING = "## Filter table"
STALE_AFTER_DAYS = 90

REQUIRED_FRONTMATTER = (
    "id", "name", "level", "nests_on", "package", "version_verified",
    "license", "ts_sdk", "verified_on", "status",
)
FRONTMATTER_ALLOWED = {
    "level": {"framework", "runtime", "harness", "none"},
    "ts_sdk": {"none", "partial", "full"},
    "status": {"active", "draft"},
}
CARD_SECTIONS = (
    "## 1. What it is",
    "## 2. Filter attributes",
    "## 3. Seam mapping",
    "## 4. Known traps",
    "## 5. Pick when / avoid when",
    "## 6. Build binding",
)
FILTER_ATTRIBUTES = (
    "model_portability", "a2a", "mcp_client",
    "deploy_constraints", "default_egress", "stability",
)
FILTER_ALLOWED = {
    "a2a": {"client+server", "server-only", "licensed-server", "none"},
    "mcp_client": {"native", "beta", "none"},
    "stability": {"semver-stable", "fast-moving", "pre-1.0", "alpha", "own-code"},
}
PORTABILITY_RE = re.compile(r"^(any|vendor-only \([^)]+\))$")
SEAMS = (
    "sessions", "hitl_gate", "step_cap", "tool_call_cap",
    "model_provider", "telemetry", "eval_runner", "deploy",
)
SEAM_SUPPORT = {"native", "adapter", "custom"}
TRAP_RE = re.compile(r"^- \[(security|data|ops|churn)\] .*https://")
INDEX_COLUMNS = (
    "id", "level", "nests_on", "model_portability", "a2a",
    "mcp_client", "stability", "default_egress", "verified_on",
)
BINDING_SECTIONS = (
    "## Sessions and state",
    "## HITL gate",
    "## Caps",
    "## Model provider",
    "## Telemetry",
    "## Eval runner mapping",
    "## A2A and MCP",
    "## Pinned version and traps",
)


@dataclass(frozen=True)
class Card:
    meta: dict[str, str]
    filters: dict[str, str]

    @property
    def card_id(self) -> str:
        return self.meta["id"]

    def value(self, column: str) -> str | None:
        return self.meta.get(column, self.filters.get(column))


@dataclass
class CheckResult:
    problems: list[str] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)
    card_count: int = 0


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Return the key: value pairs between the leading '---' fences, or None."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    meta: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return meta
        key, sep, value = line.partition(":")
        if sep:
            value = re.split(r"\s+#", value, maxsplit=1)[0]
            meta[key.strip()] = value.strip().strip("'\"")
    return None


DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _parse_date(value: str) -> date | None:
    """Strict YYYY-MM-DD; None when malformed (compact forms are rejected)."""
    if not DATE_RE.fullmatch(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _read(path: Path) -> tuple[str | None, str | None]:
    """Return (text, None) or (None, error); a BOM is tolerated, never silent."""
    try:
        return path.read_text(encoding="utf-8-sig"), None
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"{path.name}: unreadable ({exc})"


def find_heading(lines: Sequence[str], heading: str) -> int | None:
    """Index of the first line equal to `heading` (trailing whitespace ignored)."""
    for i, line in enumerate(lines):
        if line.rstrip() == heading:
            return i
    return None


def section_lines(text: str, heading: str) -> list[str] | None:
    """Lines between `heading` and the next '## ' heading; None if absent."""
    lines = text.splitlines()
    start = find_heading(lines, heading)
    if start is None:
        return None
    body: list[str] = []
    for following in lines[start + 1:]:
        if following.startswith("## "):
            break
        body.append(following)
    return body


def table_rows(lines: Sequence[str]) -> list[list[str]]:
    """Cells of every Markdown table row in `lines`, header and separator included."""
    return [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in lines
        if line.strip().startswith("|")
    ]


def check_card(path: Path) -> tuple[Card | None, list[str]]:
    name = path.name
    text, error = _read(path)
    if text is None:
        return None, [error or f"{name}: unreadable"]
    meta = parse_frontmatter(text)
    if meta is None:
        return None, [f"{name}: no frontmatter"]
    problems: list[str] = []
    for key in REQUIRED_FRONTMATTER:
        if not meta.get(key):
            problems.append(f"{name}: frontmatter '{key}' missing or empty")
    if not meta.get("id"):
        return None, problems
    for key, allowed in FRONTMATTER_ALLOWED.items():
        if key in meta and meta[key] not in allowed:
            problems.append(f"{name}: frontmatter {key}='{meta[key]}' not in {sorted(allowed)}")
    if meta.get("id") and meta["id"] != path.stem:
        problems.append(f"{name}: id '{meta['id']}' does not match the filename")
    if _parse_date(meta.get("verified_on", "")) is None:
        problems.append(f"{name}: verified_on '{meta.get('verified_on', '')}' is not YYYY-MM-DD")

    text_lines = text.splitlines()
    positions = [find_heading(text_lines, heading) for heading in CARD_SECTIONS]
    for heading, pos in zip(CARD_SECTIONS, positions):
        if pos is None:
            problems.append(f"{name}: section '{heading}' missing")
    found = [p for p in positions if p is not None]
    if found != sorted(found):
        problems.append(f"{name}: sections out of order")

    filters: dict[str, str] = {}
    for row in table_rows(section_lines(text, CARD_SECTIONS[1]) or [])[2:]:
        if len(row) != 3:
            problems.append(f"{name}: filter row {row} must have 3 cells")
            continue
        attribute, value, source = row
        if attribute in filters:
            problems.append(f"{name}: duplicate filter '{attribute}'")
        filters[attribute] = value
        if "https://" not in source:
            problems.append(f"{name}: filter '{attribute}' has no source URL")
    for attribute in FILTER_ATTRIBUTES:
        if not filters.get(attribute):
            problems.append(f"{name}: filter '{attribute}' missing")
    for attribute, allowed in FILTER_ALLOWED.items():
        value = filters.get(attribute)
        if value and value not in allowed:
            problems.append(f"{name}: filter {attribute}='{value}' not in {sorted(allowed)}")
    portability = filters.get("model_portability")
    if portability and not PORTABILITY_RE.match(portability):
        problems.append(
            f"{name}: filter model_portability='{portability}' must be 'any' or 'vendor-only (<vendor>)'"
        )

    seen_seams: set[str] = set()
    for row in table_rows(section_lines(text, CARD_SECTIONS[2]) or [])[2:]:
        if len(row) != 4:
            problems.append(f"{name}: seam row {row} must have 4 cells")
            continue
        seam, support, _how, source = row
        if seam in seen_seams:
            problems.append(f"{name}: duplicate seam '{seam}'")
        seen_seams.add(seam)
        if support not in SEAM_SUPPORT:
            problems.append(f"{name}: seam '{seam}' support '{support}' not in {sorted(SEAM_SUPPORT)}")
        if "https://" not in source:
            problems.append(f"{name}: seam '{seam}' has no source URL")
    for seam in SEAMS:
        if seam not in seen_seams:
            problems.append(f"{name}: seam '{seam}' missing")

    trap_lines = [
        line for line in section_lines(text, CARD_SECTIONS[3]) or [] if line.startswith("- ")
    ]
    if not trap_lines:
        problems.append(f"{name}: no known trap listed")
    for line in trap_lines:
        if not TRAP_RE.match(line):
            problems.append(f"{name}: trap not tagged [security|data|ops|churn] with a URL: {line[:60]}")

    binding_ref = f"bindings/{meta.get('id', '')}.md"
    if binding_ref not in "\n".join(section_lines(text, CARD_SECTIONS[5]) or []):
        problems.append(f"{name}: section 6 must point to {binding_ref}")

    return Card(meta=meta, filters=filters), problems


def check_index(index_path: Path, cards: Sequence[Card]) -> list[str]:
    if not index_path.is_file():
        return [f"{INDEX_NAME} missing"]
    text, error = _read(index_path)
    if text is None:
        return [error or f"{INDEX_NAME}: unreadable"]
    rows = table_rows(section_lines(text, INDEX_HEADING) or [])
    if not rows or tuple(rows[0]) != INDEX_COLUMNS:
        return [f"{INDEX_NAME}: '{INDEX_HEADING}' header must be {list(INDEX_COLUMNS)}"]
    by_id = {card.card_id: card for card in cards}
    problems: list[str] = []
    indexed: set[str] = set()
    for row in rows[2:]:
        if len(row) != len(INDEX_COLUMNS):
            problems.append(f"{INDEX_NAME}: row {row} has {len(row)} cells")
            continue
        values = dict(zip(INDEX_COLUMNS, row))
        card_id = values["id"]
        if card_id in indexed:
            problems.append(f"{INDEX_NAME}: duplicate id '{card_id}'")
            continue
        indexed.add(card_id)
        card = by_id.get(card_id)
        if card is None:
            problems.append(f"{INDEX_NAME}: row '{card_id}' has no card")
            continue
        if card.meta.get("status") == "draft":
            problems.append(f"{INDEX_NAME}: draft card '{card_id}' must not be indexed")
            continue
        for column in INDEX_COLUMNS:
            if values[column] != card.value(column):
                problems.append(
                    f"{INDEX_NAME}: '{card_id}' {column}='{values[column]}' in index"
                    f" but '{card.value(column)}' on the card"
                )
    for card in cards:
        if card.meta.get("status") == "active" and card.card_id not in indexed:
            problems.append(f"active card '{card.card_id}' missing from {INDEX_NAME}")
    return problems


def check_binding(card: Card, bindings_dir: Path) -> list[str]:
    path = bindings_dir / f"{card.card_id}.md"
    if not path.is_file():
        return [f"binding for '{card.card_id}' missing: {path.as_posix()}"]
    text, error = _read(path)
    if text is None:
        return [error or f"{path.name}: unreadable"]
    meta = parse_frontmatter(text) or {}
    problems: list[str] = []
    if meta.get("card") != card.card_id:
        problems.append(f"{path.name}: frontmatter card='{meta.get('card')}' must be '{card.card_id}'")
    if meta.get("version_pinned") != card.meta.get("version_verified"):
        problems.append(
            f"{path.name}: version_pinned='{meta.get('version_pinned')}' must equal the card's"
            f" version_verified='{card.meta.get('version_verified')}'"
        )
    text_lines = text.splitlines()
    for heading in BINDING_SECTIONS:
        if find_heading(text_lines, heading) is None:
            problems.append(f"{path.name}: section '{heading}' missing")
    return problems


def check_catalog(root: Path, as_of: date | None) -> CheckResult:
    result = CheckResult()
    stacks = root / STACKS_DIR
    if not stacks.is_dir():
        result.problems.append(f"stacks directory missing: {stacks.as_posix()}")
        return result
    cards: list[Card] = []
    for path in sorted(stacks.glob("*.md")):
        if path.name.startswith("_"):
            continue
        card, problems = check_card(path)
        result.problems.extend(problems)
        if card is not None:
            cards.append(card)
    result.card_count = len(cards)
    result.problems.extend(check_index(stacks / INDEX_NAME, cards))
    for card in cards:
        if card.meta.get("status") == "active":
            result.problems.extend(check_binding(card, root / BINDINGS_DIR))
    if as_of is not None:
        for card in cards:
            verified = _parse_date(card.meta.get("verified_on", ""))
            if verified is None:
                continue
            if (as_of - verified).days > STALE_AFTER_DAYS:
                result.stale.append(card.card_id)
    return result


def _say(message: str) -> None:
    print(message.encode("ascii", "replace").decode("ascii"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the agent-cycle stack catalog.")
    parser.add_argument("--root", type=Path, default=Path("."),
                        help="plugin repo root (default: current directory)")
    parser.add_argument("--as-of", type=date.fromisoformat, default=None,
                        help="list cards verified more than 90 days before this date (YYYY-MM-DD)")
    args = parser.parse_args(argv)
    result = check_catalog(args.root, args.as_of)
    for problem in result.problems:
        _say(f"[x] {problem}")
    for card_id in result.stale:
        _say(f"[stale] {card_id}: verified more than {STALE_AFTER_DAYS} days before {args.as_of}")
    if result.problems:
        _say(f"FAIL: {len(result.problems)} problem(s) in {result.card_count} card(s)")
        return 1
    _say(f"PASS: {result.card_count} card(s); cards, index and bindings consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
