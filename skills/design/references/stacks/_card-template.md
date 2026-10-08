# Stack card template

Every card follows this format exactly; `scripts/check_catalog.py` enforces it.
Rules: every row and trap carries a full https:// source URL; unconfirmed facts
keep the word `unverified`; own reasoning keeps the word `inference`; a fact
seen in a scratch run rather than on a cited page keeps the word `observed`
(the card says which run: version and setup; a bare `observed` means observed
at the card's `version_verified` as of `verified_on`; `observed on <version>;
re-observe` means not yet re-observed at the current version); no `|` inside cell text; at most ~150 lines; English.

```
---
id: <kebab-case, equals the filename>
name: <display name>
level: <framework | runtime | harness | none>
nests_on: <card id this one is built on, or none>
package: <PyPI package, or none>
version_verified: <exact version verified, or n/a>
license: <SPDX id>
ts_sdk: <none | partial | full>   # one line only; TS is never evaluated
verified_on: <YYYY-MM-DD>
status: <active | draft>          # draft cards never enter _index.md
---

# <Name>

## 1. What it is
<2-3 lines.>

## 2. Filter attributes
| Attribute | Value | Source |
|---|---|---|
| model_portability | <any / vendor-only (<vendor>)> | <url> |
| a2a | <client+server / server-only / licensed-server / none> | <url> |
| mcp_client | <native / beta / none> | <url> |
| deploy_constraints | <free text, or none> | <url> |
| default_egress | <free text, or none> | <url> |
| stability | <semver-stable / fast-moving / pre-1.0 / alpha / own-code> | <url> |

## 3. Seam mapping
| Seam | Support | How | Source |
|---|---|---|---|
| sessions | <native / adapter / custom> | <how> | <url> |
| hitl_gate | ... | ... | ... |
| step_cap | ... | ... | ... |
| tool_call_cap | ... | ... | ... |
| model_provider | ... | ... | ... |
| telemetry | ... | ... | ... |
| eval_runner | ... | ... | ... |
| deploy | ... | ... | ... |

## 4. Known traps
- [security|data|ops|churn] <trap>. Source: <url>

## 5. Pick when / avoid when
<Pick when ... Avoid when ... — each claim with its source URL.>

## 6. Build binding
`skills/build/references/bindings/<id>.md`
```

Value meanings:
- `stability`: `semver-stable` = breaking changes only in majors (published
  policy); `fast-moving` = >=1.0 but breaking changes observed in minors or
  patches; `pre-1.0` = 0.x; `alpha` = marked alpha; `own-code` = no framework.
- `[security]`/`[data]` tags are for risks of the deployed agent at runtime or
  install time; maintainer-facing risks use `[ops]`.
- `support`: `native` = built in; `adapter` = official or small documented
  adapter; `custom` = the build writes it.
