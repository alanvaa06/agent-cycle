# Eval runs — agent-cycle:economics

One row per check, per run. Verdict: PASS / FAIL. Evidence: one line.

| Date | Case | Check # | Verdict | Evidence |
|---|---|---|---|---|
| 2026-07-28 | ECO-E01* | 1 | PASS (owner) | No re-ask of model/target/tools; frontmatter carries spec_version AND design_version; interview = the 2 legitimate questions only (turns/day, hourly value) |
| 2026-07-28 | ECO-E01* | 2 | PASS | Unit = TURN with stated reason; owner-stated scenario ladder flagged guess until calibration; per-component token build-up (354-tok tool-use overhead sourced); worked example recomputable |
| 2026-07-28 | ECO-E01* | 3 | PASS | 11 price rows all URL+dated; web-first (v0.4.1); Hetzner honestly "NOT RETRIEVED"; free-tier conditions stated and bound (WhatsApp $0 inside service window, Supabase pause risk analyzed) |
| 2026-07-28 | ECO-E01* | 4 | PASS | Scenario x component table, band totals; model band spans intro→standard pricing with expiry reasoning (2026-08-31) |
| 2026-07-28 | ECO-E01* | 5 | PASS | Base case = VPS per design §5; no multi-cloud shootout |
| 2026-07-28 | ECO-E01* | 6 | PASS | 3-tier swap incl. tokenizer nuance (+30% only 4.7+, Haiku cheaper than headline); ±50% volume; caching with sourced multipliers, hit-rate marked guess/upper-bound; "Haiku is an eval question, not a cost question — run the suite" |
| 2026-07-28 | ECO-E01* | 7 | PASS | Internal break-even at owner-stated $80/h → 12 min/mo; conditional on unlogged baseline; honest read: "cost is not the risk — do not let a favorable model substitute for the log" |
| 2026-07-28 | ECO-E01* | 8 | PASS | 5 agent-specific levers ordered by effect with trade-offs; alarm $20/mo with formula, computed on standard pricing to avoid a September misfire |
| 2026-07-28 | ECO-E01* | 9 | PASS | Calibration table maps every assumption to a telemetry field; CAUGHT A REAL SPEC GAP: token counters missing from spec §5 telemetry — /build must emit them |
| 2026-07-28 | ECO-E01* | 10 | PASS | docs/agent/whatsapp-owner-assistant-economics.md; frontmatter incl. basis: estimate, prices_as_of, design_version; approved at owner gate |

\* Real-agent run post-v0.4.1 fix: `whatsapp-owner-assistant` in `C:\Proyectos\Whatsapp_agent`. Totals $7–41/mo across scenarios; tokens dominate only above ~10 turns/day (single-user nuance from the coherence fix, exercised). Which-line-dominates stated per rule 3. Finding for /build: spec §5 lists per-turn attributes but no token counters — carried as an open question into the build phase (owner to decide if it warrants a spec version bump via re-entry). Approved without manual rework — DoD met. ECO-E02×2/E03/E04 scratch runs pending for graduation tag.
