# <agent_name>-economics.md template

Written to `docs/agent/<agent_name>-economics.md` in the TARGET AGENT'S repo.
Bands over precision: totals are ranges, unit prices may be exact list values.

---
agent_name: <same-as-design>
version: 1
status: draft            # draft | approved — human gate only
date: <YYYY-MM-DD>
basis: estimate          # estimate | calibrated
prices_as_of: <YYYY-MM-DD>
spec_version: <version, when a spec exists>
design_version: <version of the design.md consumed>
---

# <Agent Name> — Economics

## 1. Assumptions

| Scenario | Conversations/mo | Turns/conv | Tool calls/turn | Tokens in/turn | Tokens out/turn | Basis |
|---|---|---|---|---|---|---|
| Low | ... | ... | ... | ... | ... | <where each number comes from: spec scenario, comparable, guess-flagged> |
| Medium | ... | | | | | |
| High | ... | | | | | |

- Model: <from design/spec — e.g. Sonnet-class via LiteLLM>; alternatives priced in §4.
- Formulas (auditable):
  `tokens_in/mo = convs x turns x tokens_in/turn` · `model_cost = tokens_in/mo x price_in + tokens_out/mo x price_out` · state every derived number's formula once.

## 2. Unit prices (every row dated + sourced)

| Item | Price | Source | As of |
|---|---|---|---|
| <model> input / output per Mtok | ... | <vault article / provider page> | <date> |
| <infra: VPS node / serverless unit> | ... | ... | <date> |
| <channel fees, e.g. WhatsApp conversation> | ... | ... | <date> |
| <third-party tools> | ... | ... | <date> |

Prices are dated inputs, not truths — stale rows invalidate totals, not the method.

## 3. Monthly cost model (base case: <design's deployment target>)

| Component | Low | Medium | High |
|---|---|---|---|
| Model tokens (dominant) | $A–B | ... | ... |
| Infra (<target>) | ... | ... | ... |
| Channel fees | ... | ... | ... |
| Third-party | ... | ... | ... |
| **Total (band)** | **$X–Y** | ... | ... |

Tokens are modeled FIRST — they usually dominate (70–90% in multi-user
agents). At very low volume, flat infra can rival or exceed them: the model
STATES which line dominates and why, rather than assuming.

## 4. Sensitivity

- Model tier swap: <e.g. Haiku-class vs Sonnet-class — factor and new bands>.
- Volume swing: ±50% on Medium.
- Prompt caching / history truncation effect where the provider supports it.

## 5. Break-even

- Client-facing: monthly price to client → margin per scenario, floor price.
- Internal: cost vs the design's own Performance metric monetized
  (e.g. owner hours saved x hourly value) → cost per hour saved.

## 6. Cost controls

Actionable levers (model routing, caching, history truncation, max-token caps)
plus: **token-spend alarm threshold = <Medium estimate x 1.5, stated
explicitly>** — this number is the input `/ship` calibrates the billing alarm
against.

## 7. Calibration plan (post-build)

| Assumption | Telemetry field that measures it (from the spec) | Recalibrate when |
|---|---|---|
| tokens/turn | <e.g. token counters per span> | after N real turns |
| turns/conv | <e.g. session turn count> | ... |
| tool calls/turn | tool_call_count | ... |

On calibration: bump version, set basis: calibrated, and fill the delta table —
estimates are preserved, never silently overwritten:

| Assumption | Estimated | Actual | Delta | Verdict (confirmed / recomputed) |
|---|---|---|---|---|
| tokens/turn | ... | ... | ... | ... |
