# Costing guide — agent-cycle:economics

## Step 0 — Gate check

Read `docs/agent/design.md`. Hard-fail (write nothing) if missing ("run
agent-cycle:design first") or not approved. Read `docs/agent/spec.md` when
present and approved — it sharpens turns/tools/telemetry assumptions; record
spec_version. Never re-ask what design/spec answer (model, target, tools,
telemetry fields). Determine mode: no prior economics artifact → basis:
estimate; existing artifact + real usage numbers offered → calibration mode
(step 7).

## Step 1 — Volume scenarios

Three scenarios (low/medium/high). Sources in priority order: the spec's own
fixtures/expectations, the user's stated expectations (one question if truly
absent), comparables. Every number gets a Basis cell; a guess is written
"guess" — hiding uncertainty is the cardinal sin here.

## Step 2 — Unit prices, dated

Priority order: (1) compiled sources already in the workspace — a knowledge
vault, pricing docs the user maintains — cite article + date; (2) provider
pricing pages via web, cite URL + retrieval date; (3) nothing found → the row
enters as UNKNOWN with a note, and totals become conditional. NEVER quote a
price from model memory without a dated source. Tokens first: model input/
output per Mtok for the design's chosen model AND one cheaper + one stronger
alternative (feeds §4). Then infra for the design's target only, channel fees,
third-party tools the spec names.

## Step 3 — Cost model

Tokens/mo per scenario from the §1 formulas; model cost; then infra, channel,
third-party. Totals as BANDS (round to honest figures — $80–150, never
$83.47). Base case = the design's deployment target. Other targets only if the
design names alternatives or the user asks — this is an agent costing, not a
cloud comparison shootout.

## Step 4 — Sensitivity

Mandatory: model-tier swap (recompute §3's dominant line with the two
alternatives priced in step 2) and volume swing (±50% on Medium). Add prompt
caching / history truncation effect when the provider supports it — cite the
mechanism, don't invent discount factors.

## Step 5 — Break-even

Client-facing agent: margin table vs the client's monthly price (ask for the
price if unknown — one question) and the floor price. Internal agent: monetize
the design's own Performance metric (e.g. hours of owner lookup time saved x
the owner's hourly value — ask for the hourly value if needed, one question)
→ cost per unit of value; state the utilization at which the agent pays for
itself.

## Step 6 — Controls + alarm

Levers that actually move THIS agent's bill (routing, caching, truncation,
caps — tied to its model and loop limits, not generic advice). Then the alarm:
token-spend threshold = Medium-scenario estimate x 1.5, stated as an explicit
number with its formula. Flag it as /ship's calibration input.

## Step 7 — Calibration mode (basis: calibrated)

Requires an existing economics artifact + real numbers (telemetry export or
user-pasted actuals). Build the delta table (assumption → estimated → actual →
delta). Confirmed assumptions marked; assumptions off by >25% recomputed and
§3 re-derived. Recompute the alarm from actuals; flag if the original would
have misfired. Bump version, set basis: calibrated, preserve the estimate
columns — never silently overwrite.

## Step 8 — Gate

Present: scenario table, total bands, dominant cost line, break-even headline,
alarm threshold. Explicit approval → status: approved. Hand off: "/ship reads
the alarm threshold; /blueprint embeds this artifact."
