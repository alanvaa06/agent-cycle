# Changelog

All notable changes to the agent-cycle plugin. Semver: minor = new pipeline
skill, patch = fixes.

## [0.4.0] — 2026-07-28

### Added
- **`economics` skill** (transversal 1 of 2): monthly cost analysis for a
  designed agent. Dated unit prices (workspace sources first, never from model
  memory), tokens-first scenario model with auditable formulas and band totals,
  mandatory sensitivity (tier swap + volume) and break-even (client price or
  monetized internal metric), token-spend alarm threshold as the /ship
  contract, calibration mode with delta tables (estimates never silently
  overwritten). Artifact: docs/agent/<agent_name>-economics.md.
- EDD eval suite (`skills/economics/evals/`): ECO-E01 positive (10-check
  contract), ECO-E02 gate-negative (two branches), ECO-E03 calibration edge,
  ECO-E04 trigger-negative (generic API pricing must not fire).

### Pending graduation
- `economics` skill runs against the real agent — tag `economics-v0.1` when
  the dogfood passes.

## [0.3.0] — 2026-07-28

### Added
- **`evals` skill** (phase 3 of 7): approved spec.md → framework-agnostic eval
  suite BEFORE any code. Golden cases pin BHV-NNN@spec_version; method mix
  (deterministic / llm_judge with anchored rubrics / adversarial per untrusted
  surface, >=2 realistic payloads incl. end-user language); per-tier thresholds
  (pass^k destructive); release blockers lifted from the spec's hard
  constraints; red-by-design rule; suite is pure data — the runner belongs to
  /build. Sanctioned external write: exactly the spec §6 Eval column.
- EDD eval suite (`skills/evals/evals/`): EVL-E01 positive (11-check contract),
  EVL-E02 gate-negative (two branches), EVL-E03 non-automatable edge,
  EVL-E04 trigger-negative.

### Pending graduation
- `evals` skill runs against the real agent — tag `evals-v0.1` when the dogfood
  passes.

## [0.2.0] — 2026-07-28

### Added
- **`spec` skill** (phase 2 of 7): approved design.md → executable spec.md.
  Gherkin scenarios with BHV-NNN ids (happy/wrong/edge per capability), final
  tool contracts (docstring-as-interface, extra=forbid schemas, distinct-
  operation counting, action tiers with justified changes), conversation rules
  incl. spec-level decisions (debounce), design-anchored security model with
  mandatory injection scenarios per untrusted surface, least-privilege + PII
  rules, data schemas, traceability table. Hard gate on design approval; design
  is settled law (re-entry ladder for changes).
- EDD eval suite (`skills/spec/evals/`): SPC-E01 positive (13-check contract),
  SPC-E02 gate-negative (two hard-fail branches), SPC-E03 trivial-agent edge,
  SPC-E04 trigger-negative (generic Gherkin help must not fire).

### Pending graduation
- `spec` skill eval runs against the real agent — tag `spec-v0.1` when the
  dogfood passes.

## [0.1.0] — 2026-07-28

### Added
- Plugin scaffold: `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json`
  (installable as a GitHub marketplace: `alanvaa06/agent-cycle`).
- **`design` skill** (phase 1 of 7): PEAS interview → approvable
  `docs/agent/design.md` with environment classification, harness decision,
  deployment intent + 3 portability seams, NO-goals, open questions. Human gate;
  never self-approves.
- EDD eval suite for the skill itself (`skills/design/evals/`): 3 cases
  (DES-E01 positive / DES-E02 trigger-negative / DES-E03 partial-PEAS edge),
  11-check contract on the positive case, per-check results log.
- Design doc for the full pipeline (`docs/superpowers/specs/`): 7 gated phases +
  2 transversals (economics, blueprint), re-entry ladder, anti-gaming rules,
  forge-master delegation.

### Pending graduation
- `design` skill eval runs (DES-E01..E03) against a real agent — tag
  `design-v0.1` lands when the dogfood passes.
