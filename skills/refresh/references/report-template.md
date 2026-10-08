# Refresh report template

The report is written to `docs/refresh/<YYYY-MM-DD>.md` with this shape (a second
run on the same date: `<YYYY-MM-DD>-2.md`, then `-3`; never overwrite).

```
---
date: <YYYY-MM-DD>
checker_before: <PASS/FAIL line>
checker_after: <PASS line>
harvested_projects: <paths or none>
cards_reverified: <ids>
---

# Stack catalog refresh — <date>

## Research notes appended
<paths of the research files that received a Refresh <date> section; or none>

## Commands run
<python scripts/check_catalog.py --root . --as-of <date>  -> output before>
<python scripts/check_catalog.py --root .  -> output after>

## Cards changed
| Card | Field / row | Old | New | Source |
|---|---|---|---|---|

## Version moves
| Card | version_verified old -> new | Breaking changes checked (URL) | Binding pins changed | Traps added / removed |
|---|---|---|---|---|

## Newer versions not adopted
| Card | Newer version | Reason not adopted | Changes found only there (not applied) |
|---|---|---|---|

## Observed facts to re-observe
| Card or binding | Fact | Spike | Observed on | Re-observed this run (yes / no) |
|---|---|---|---|---|

## Unverifiable (old value kept)
| Card | Item | Why |
|---|---|---|

## Harvested drift
| Project | Claim | Verdict (applied / rejected / already current) | Evidence |
|---|---|---|---|

## Binding defects reported
| Source (project build.md or chat) | Defect claimed | Verified against | Spike to re-run |
|---|---|---|---|

## Draft cards proposed
<id — why — source; or none>

## Cards proposed for retirement
<id — why — source; or none>

## Proposals outside scope (checker, templates, index mapping)
<what and why; or none>

## Dependency security advisories
<package — advisory — URL; or none>

## Suspicious content
<page URL or project file — short excerpt — what was NOT done; or none>

## Draft CHANGELOG entry
<patch entry text>
```
