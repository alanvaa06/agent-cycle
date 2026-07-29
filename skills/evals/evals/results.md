# Eval runs — agent-cycle:evals

One row per check, per run. Verdict: PASS / FAIL. Evidence: one line.

| Date | Case | Check # | Verdict | Evidence |
|---|---|---|---|---|
| 2026-07-28 | EVL-E01* | 1 | PASS (owner) | config notes resolve each spec §7 item per the deferred-corpus rule; one genuine interview question ("el finde" = Sat+Sun) confirmed at gate |
| 2026-07-28 | EVL-E01* | 2 | PASS | 21/21 coverage, map reconciles exactly with spec §6 table, coverage_gaps: [], bhv_ref @1 throughout |
| 2026-07-28 | EVL-E01* | 3 | PASS | 19 deterministic + 7 llm_judge + 8 adversarial; BHV-001 correctly split into deterministic (EVL-001) + judge (EVL-002) |
| 2026-07-28 | EVL-E01* | 4 | PASS | 3 untrusted surfaces x2 payloads (EN+ES: ADV-002/004/006 Spanish); ADV-002 = ES authority-claim + third-party exfiltration with containment in forbidden |
| 2026-07-28 | EVL-E01* | 5 | PASS | Modes declared per case; IN_ORDER on real dependency (ADV-002 list→send), ANY_ORDER default elsewhere |
| 2026-07-28 | EVL-E01* | 6 | PASS | Per-tier thresholds incl. honest "no destructive tool in v1" note; blockers lifted verbatim with BHV refs; OWN refinement: adversarial tier pass^3 |
| 2026-07-28 | EVL-E01* | 7 | PASS | 7 judge cases → 4 anchored rubrics; grounded-answer.md: 1-5 scale, >=4 threshold, judge-model requirement, judged-vs-asserted separation |
| 2026-07-28 | EVL-E01* | 8 | PASS | No non-automatable scenario existed (all 21 BHV observable or judge-able); none omitted — vacuous by construction, verified against BHV list |
| 2026-07-28 | EVL-E01* | 9 | PASS | Spec §6 Eval column filled for all 21 rows; BHV/Capability/Test columns byte-identical to pre-run version |
| 2026-07-28 | EVL-E01* | 10 | PASS | 34 JSON + 4 rubric MD + config.yaml; zero code files, zero framework imports; all 34 parse |
| 2026-07-28 | EVL-E01* | 11 | PASS | golden/ rubrics/ adversarial/ config.yaml structure; status approved via owner gate 2026-07-28 |

\* Real-agent run: `whatsapp-owner-assistant` suite in `C:\Proyectos\Whatsapp_agent\evals\` (34 cases over 21 BHV). Fixes from the coherence review all exercised in production: EVL-021 uses messages[] with offsets (debounce), EVL-025/026 use harness_condition force_step_cap, trusted-by-design WhatsApp surface got enforcement case (ADV-007) + trusted-principal abuse path (ADV-008), never content injections. Approved without manual rework — DoD met. EVL-E02×2/E03/E04 scratch runs pending for formal graduation tag.
