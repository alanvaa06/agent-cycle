# agent-cycle — Plugin Design

**Date:** 2026-07-28
**Status:** draft — pending Alan's review
**Author:** Alan Vazquez + Claude (brainstorming session)

## 1. What this is

A Claude Code plugin that runs the **complete construction cycle of an AI agent** — from idea to shipped, evaluated, observable production agent — as a gated, disk-backed pipeline of skills. Built skill-by-skill with maximum depth per skill, each one dogfooded on a real project before the next begins.

**First real agent (dogfood):** a WhatsApp Business agent deployed on AWS for a client.

## 2. Foundational decisions (settled during brainstorming)

| Decision | Choice | Rationale |
|---|---|---|
| Framework scope | **Framework-agnostic, ADK 2.0 as first build target** | Clients may demand AWS or a VPS; design/spec/evals are framework-neutral by nature. ADK pinned at 2.0 (1.x session schema is incompatible). |
| Relationship to forge-master | **Separate, composable plugin** | forge-master owns *how to execute software* (PRD → plan → run, proven on MAES). agent-cycle owns *what a correct agent is*. `/build` delegates execution to forge-master; the agent spec feeds the forge PRD. |
| Build method | **Skill-by-skill, full pipeline as the goal** | Each skill gets research → EDD → SKILL.md → dogfood → iterate before the next starts. |
| Dogfood cadence | **Per-skill, not at the end** | Each finished skill immediately produces its real artifact for the WhatsApp agent. DoD per skill = "produced the real artifact and Alan approved it without manual rework". |
| Design model | **PEAS + environment classification; BDI as an optional lens only** | PEAS is external specification (applies to every agent). BDI is internal deliberative architecture that modern LLM harnesses replace; its essence ("partially observable → belief state/memory") is already operationalized in the environment classification. BDI stays citable from the agent-design knowledge skill. |
| Knowledge vs process | **The plugin references the existing `agent-design` skill, never copies it** | One source of truth. The diverged copy in `scaffold/templates/` is the anti-pattern this rule prevents. |

## 3. Plugin architecture

```
agent-cycle/
  .claude-plugin/plugin.json      # manifest = contract (viability pattern)
  skills/
    design/     SKILL.md + references/     # phase 1
    spec/       SKILL.md + references/     # phase 2
    evals/      SKILL.md + references/     # phase 3
    build/      SKILL.md + adapters/       # phase 4 (adapters: aws first, then gcp, vps)
    skills/     SKILL.md + references/     # phase 5 (target agent's skills) — conditional
    interop/    SKILL.md + references/     # phase 6 (A2A) — conditional
    ship/       SKILL.md + checklist       # phase 7
    economics/  SKILL.md + references/     # transversal — invokable any time
    blueprint/  SKILL.md + template.html   # transversal — invokable any time
  docs/superpowers/specs/                  # this design doc + future specs
```

**Contract between phases — disk-backed (forge-master pattern):**

```
/design    → docs/agent/design.md                 PEAS + environment + harness + seams
/spec      → docs/agent/spec.md                   BDD scenarios (BHV-NNN) + tool contracts + security
/evals     → evals/                               golden/ rubrics/ adversarial/ config.yaml
/build     → src/                                 core + adapter, via forge-master when sizable
/skills    → target agent's skills/               conditional
/interop   → Agent Card + A2A executor            conditional
/ship      → DoD report                           mechanical audit + sign-off
/economics → docs/agent/<name>-economics.md       transversal analysis
/blueprint → docs/agent/blueprint.html            transversal view (renders whatever exists)
```

Every artifact carries frontmatter: `agent_name, version, status: draft|approved, date`. Each phase **fails hard** if its upstream artifact is missing, `draft`, or version-stale. Human gate between every phase.

**Security is transversal, not a phase**: each SKILL.md carries its phase's security gates; `/ship` verifies the aggregate.

## 4. Phase skills

### 4.1 `/agent-cycle:design`

**Purpose:** idea → approvable `design.md`. The layer where errors are cheapest.

**Boundary:** loads the personal `agent-design` skill as knowledge base and cites it — process here, knowledge there, zero duplication.

**Workflow:**
1. PEAS interview, one question at a time. Performance = a metric of the *environment*, not agent activity; Goodhart stress-test.
2. Environment classification → automatic architectural implications (partially observable → memory/belief state; stochastic → contingency plans; sequential → plan ahead; dynamic → time-bound decisions; multi-agent → model others).
3. Minimal harness — single-agent default; roles only with measurable justification. Completeness checklist: the 5 agent parts (model / tools / memory / orchestration / deployment).
4. **Deployment intent** — declares target (AWS/GCP/VPS) and the 3 portability seams (framework-native sessions, LiteLLM model access, OTel telemetry) from day one, citing the vault's Multi-Cloud Agent Deployment Patterns. Seams are decided early or paid for late.
5. Human gate → `status: approved`.

**Artifact `docs/agent/design.md`:** PEAS table (+ Goodhart notes) · environment classification (5 dims → implications) · harness decision · preliminary tool inventory (name + purpose, no schemas) · deployment intent + seams · NO-goals · open questions (input to `/spec`).

**EDD cases:** positive ("WhatsApp appointment agent for a dentist" → full PEAS, env classified, single-agent, seams declared) · trigger-negative ("review this orchestration code" → does NOT fire; that is the knowledge skill alone) · edge (user brings partial PEAS → completes without re-asking what was given).

**DoD:** produced the real WhatsApp agent's design.md, approved without manual rework.

### 4.2 `/agent-cycle:spec`

**Purpose:** approved design → executable specification. "If the brain gets a vibe instead of a blueprint, it guesses."

**forge-master boundary:** the agent spec is the *input* to the forge PRD. `BHV-NNN` scenarios are already Given/When/Then — they become forge ACs mechanically. One source of truth, no rival specs.

**Artifact — default a single `docs/agent/spec.md`** (split into a folder only when the agent warrants it):
1. **Behavior** — Gherkin scenarios per capability, each with ID `BHV-NNN`; happy + wrong + edge.
2. **Tools** — per-tool contract: docstring-for-LLM (the docstring IS the interface), Pydantic I/O schema `extra="forbid"`, errors-as-observations, and **action tier** (safe / reversible / destructive) mapping directly to HITL gates.
3. **Conversation (WhatsApp)** — templates vs 24h window, fallbacks, human handoff, message debounce. Forces these decisions before build.
4. **Security** — inbound WhatsApp messages are **always untrusted**: injection surface, least privilege per tool, action gating, PII.
5. **Data** — session/dedupe/profile schemas behind a repository interface (the design's seams landed).

**Format tax rule (Google Day 5):** clean Markdown headers; YAML only for schemas nested >3 deep.

**Workflow:** read design (fail if not approved) → Gherkin per capability, interviewing only on the design's open questions → tool contracts → security → human gate.

**Traceability:** every `BHV-NNN` will be cited by `/evals` golden cases and mapped to tests by `/build`. Coverage table scenario→eval→test, machine-checkable.

**EDD:** positive (approved design → full spec with tiers) · negative (draft design → refuses, demands the gate) · edge (single-tool agent → one-file spec, no ceremony).

**DoD:** real WhatsApp agent spec approved.

### 4.3 `/agent-cycle:evals`

**Purpose:** approved spec → executable eval suite **before any agent code exists**. Hard gate: `/build` refuses to run without an approved suite. All evals fail at first — red before green, TDD at agent level.

**Why before build:** evals written after validate what was built (confirmation bias); written before, they are the executable functional spec and surface spec ambiguities while cheap (EDD). Separates doer from judge.

**Artifact `evals/`:** `golden/` (JSON cases: input → expected_tools trajectory + expected_output, each citing `BHV-NNN@version`) · `rubrics/` (LLM-judge rubrics) · `adversarial/` (injection/jailbreak/PII, derived from the spec's security section) · `config.yaml` (dimensions, thresholds, pass^k per tier).

**Dimensions** (selected for conversational agents): intent satisfaction · functional correctness · trajectory quality (right answer via wrong tools = fragile; critical for action-allowed) · cost/efficiency (tokens, turns) · self-repair · safety (transversal).

**Method mix (never one alone):** deterministic asserts for correctness/trajectory · LLM-judge with rubric for intent/quality (judge stronger than judged; periodically validated vs human) · adversarial suite for safety.

**Thresholds by tier:** safe tools → pass^1; destructive tools → **pass^k** (k≥4, all green). Basis: 61% pass^1 → <25% pass^8 on tau-bench.

**Runner:** suite is framework-agnostic JSON (a seam); the runner is per-framework and lives in the `/build` adapter — for ADK: pytest + native `AgentEvaluator` with trajectory modes (EXACT / IN_ORDER / ANY_ORDER mapped to tier). **The eval runner's exit code becomes forge-master's definition of "green"** — the whole pipeline is machine-closed.

**Living suite post-launch:** real user corrections mined as labeled failures → new golden cases; the weekly ritual (pull → score → patch ONE thing → A/B → promote) operates on this suite.

**EDD:** positive (approved spec → suite with full BHV coverage + pass^k on destructive) · negative (draft spec → refuses) · edge (non-automatable scenario, e.g. tone → LLM-judge rubric + explicit human-review flag, never silent omission).

**DoD:** WhatsApp agent suite running red before `/build` exists.

### 4.4 `/agent-cycle:build`

**Purpose:** the only phase that produces code. Spec + evals approved and version-consistent, or hard fail.

**Generated structure — invariant core + adapter per target** (the 5 bindings from Multi-Cloud Agent Deployment Patterns):

```
src/
  agent/        ADK 2.0 loop (pinned + constraints), tools from spec contracts,
                repository interfaces (state), LiteLLM (model = config), native OTel
  adapters/
    aws/        Lambda ingress (HMAC + dedupe), SQS FIFO binding, DynamoDB repo,
                Secrets Manager, SAM/CDK recipe            ← v0.1 (dogfood)
    gcp/ vps/   ← later, same adapter interface
tests/          unit + eval-runner integration
```

Agent, evals, and instrumentation **never fork per cloud** — only the adapter does.

**forge-master delegation:**
1. `/build` generates scaffold + a forge PRD derived mechanically: `BHV-NNN` = ACs verbatim; forge's test runner = the eval suite runner.
2. Alan approves the forge plan → `forge-run` executes with proven machinery (junior/senior escalation, TDD Iron Law on heavy phases, disk-backed resume).
3. **Anti-gaming enforced during the run**: PreToolUse hook blocks writes to `evals/` and `docs/agent/`.
4. **When not to delegate:** small builds (few tools, all safe) → `/build` runs directly with TDD. The WhatsApp dogfood is mid-size — full delegation is tested there.

**Build DoD:** eval suite green locally (pass^k per tier) + adapter smoke test (container boots, `/ping` answers, simulated webhook roundtrip via SAM local / docker).

**Transversal security here:** the build itself runs sandboxed · secrets never in code (SOPS / Secrets Manager per adapter) · slopsquatting defense: pinned deps + vetted registries.

**EDD:** positive (approved spec+evals → scaffold passing smoke) · negative (draft evals → refuses) · edge (trivial all-safe agent → direct build, no forge ceremony).

**DoD:** WhatsApp agent running on AWS dev, suite green.

### 4.5 `/agent-cycle:skills` (conditional)

Skills for the **target agent** (not the plugin's).

- **Entry test:** is the capability on-demand procedural know-how (per-client policies, process variants), or does tool + static instruction suffice? Skills only for narrow action workflows; global context in static instructions. If not warranted (likely for WhatsApp v1) → emits justified "no skills needed" and passes. Zero ceremony skills — 19% of badly built skills subtract capability.
- When warranted, per skill: EDD first (trigger positive/negative + execution cases) → SKILL.md with description-as-routing (when-to-use + when-NOT) → trigger eval ≥90% + **regression co-loaded** (suite runs with all skills loaded, never isolated).
- **Authority ladder:** every new skill enters draft; action-allowed requires pass^k + Alan's approval. Same rail as tool tiers.

### 4.6 `/agent-cycle:interop` (strongly conditional)

- **Entry test (A2A vs tool):** does the other system need to *take responsibility* (unbounded domain, multi-turn, can pause and consult) or just *return a result*? Only the former is A2A; wrapping a collaborator as a tool injects the GOTO problem. Result → MCP tool, phase does not apply.
- When it applies: Agent Card (capabilities, security, schemas) + executor (ADK `LlmAgent` + `Runner` is the A2A executor's reasoning core) + registry if enterprise/marketplace.
- WhatsApp dogfood: **skip**, one-line justification. The phase exists for the enterprise client who asks.

### 4.7 `/agent-cycle:ship`

Mechanical audit, not a creative phase:
1. **End-to-end traceability:** `BHV → eval → test → green` table, complete or gaps justified in writing.
2. **Security gates re-verified:** adversarial suite green · least-privilege diff (real permissions vs spec) · tiers with HITL configured · secret scan · egress/sandbox per adapter.
3. **Anti-gaming audit:** git diff of `evals/` and `docs/agent/` during build — zero unapproved changes, machine-verified.
4. **Observability live:** OTel traces reaching the adapter's backend (CloudWatch for dogfood); alarms on queue age, DLQ depth, token spend.
5. **Operations runbook:** DLQ drain, rollback, kill switch, weekly ritual scheduled on the living suite.
6. **DoD report** to disk + Alan's sign-off = shipped. Operationalizes the agent-design `references/checklist.md`.

## 5. Transversal skills

### 5.1 `/agent-cycle:economics`

Financial estimate of running the agent monthly — tokens, cloud infra, WhatsApp fees, third-party tools. CFA-grade; no other plugin in the ecosystem has this.

- **Inputs by moment:** post-spec → band estimate from design (harness, deployment intent) + spec (turns/conversation, tools/turn) + vault unit prices (tokens dominate 70–90%; AWS/GCP infra $5–75/mo; VPS €10–12 flat; Haiku vs Sonnet 5–10×). Post-build → **recalibration with real runner data** (the eval runner already traces tokens/turn).
- **Output:** monthly cost table per volume scenario (low/medium/high) × cloud target (multi-cloud matrix) · breakdown tokens/infra/WhatsApp/third-party · model sensitivity · **break-even vs client price**.
- **Artifact:** `docs/agent/<agent_name>-economics.md`.
- **Hooks into the pipeline:** post-spec invocation acts as a viability gate (worth building?); `/ship` calibrates the token-spend alarm against the estimate — real >> estimate = drift detected.

### 5.2 `/agent-cycle:blueprint`

Self-contained HTML rendering of the agent — architecture, state, tools, nodes/edges — plus agent detail and its economics.

- **Progressive rendering by available artifacts:** design only → PEAS + harness · +spec → tools with tiers and flows · +build → **real graph extracted mechanically from ADK 2.0 `Workflow`** (graph-based: nodes and edges declared in code) · +economics → embeds the financial table (consumes `<agent_name>-economics.md` — clean contract between the two transversals).
- **Form:** single self-contained HTML (inline SVG/mermaid, no external deps) — a capture, not an app. Fixed template + injected data = low maintenance. Publishable as a Claude Artifact for client sharing.
- **Artifact:** `docs/agent/blueprint.html`.
- Dual value: client-facing sales deliverable (agency) + at-a-glance architecture review. The HTML-as-agent-output thesis operationalized.

## 6. Re-entry ladder (what happens when evals fail)

**Moment 1 — red during `/build`: not a failure, that is the phase working.** Red→green iteration with forge escalation (K consecutive reds / stuck → tier up).

**Moment 2 — persistent red where diagnosis says the code is not the problem: return to the lowest phase whose artifact is wrong.**

| Diagnosis | Return to | Example |
|---|---|---|
| Code doesn't meet scenario | `/build` (stay) | Tool returns badly formatted date |
| The eval itself is wrong | `/evals` | expected_tools demanded EXACT where ANY_ORDER was correct |
| BHV scenario is ambiguous | `/spec` | Two valid readings of the Gherkin |
| Design error | `/design` | Goodhart-gameable PEAS metric; misclassified environment; capability impossible with declared tools |

- **Minimum-return rule:** lowest defective artifact, never restart.
- **Surgical staleness cascade:** corrected artifact → version bump → only downstream artifacts citing the touched part go `stale` (evals cite `BHV-NNN@version` — machine-detectable) → only those re-derive.
- **Anti-gaming (the most important rule):** the builder can NEVER edit `evals/` or `spec.md`. Believes an eval is wrong → raises a dispute → Alan decides → correction enters via `/evals` or `/spec` with its gate. Enforced mechanically: PreToolUse hook during build + `/ship` git-diff audit.
- **Who classifies:** the runner reports with a *suggested* classification (fix-code / fix-eval / fix-spec / fix-design) from trace evidence; reclassifying an approved artifact always goes through the human. Evidence suggests, human rules.

## 7. Vault source map

| Plugin area | Vault articles |
|---|---|
| design | PEAS Framework · agent-design skill (knowledge base) · The New SDLC with Vibe Coding (Google) — 5 agent parts |
| spec | Spec-Driven Production-Grade Development (Google) — SDD, BDD, format tax · WhatsApp Business Cloud API |
| evals | Agent Skills (Google Whitepaper) — EDD, pass^k · Vibe Coding Agent Security and Evaluation (Google) — 7 dimensions, method mix · AI Agent Evaluation Tools (2026) |
| build | Google ADK (adk-python) · Multi-Cloud Agent Deployment Patterns — 5-binding adapter surface · Deploying AI Agents on AWS (2026) · Forge Master |
| skills | Agent Skills (Google Whitepaper) — trigger gate, authority ladder |
| interop | Agent Tools and Interoperability (Google) — A2A vs tools, GOTO problem · Building Agents on Gemini Agent Platform |
| ship | agent-design references/checklist.md · Vibe Coding Agent Security and Evaluation (Google) |
| economics | Deploying AI Agents on AWS/GCP (2026) · Self-Hosting AI Agents on a VPS (2026) — unit prices |
| blueprint | HTML for Agent Outputs (Thariq) · Claude Code Artifacts · Google ADK — Workflow graph |
| deployment (adapters) | Multi-Cloud Agent Deployment Patterns · per-cloud articles |

## 8. Build roadmap (skill-by-skill order)

1. `/design` → dogfood: WhatsApp agent design.md
2. `/spec` → dogfood: WhatsApp agent spec.md
3. `/economics` → dogfood: quote the WhatsApp agent to the client (small skill, data ready, immediate value)
4. `/evals` → dogfood: suite running red
5. `/build` (aws adapter) → dogfood: agent green on AWS dev
6. `/blueprint` → dogfood: client-facing HTML of the real agent
7. `/skills` → dogfood: likely "no skills needed" — validates the entry test
8. `/interop` → dogfood: skip with justification — validates the entry test
9. `/ship` → dogfood: WhatsApp agent shipped
10. Later: gcp/ and vps/ adapters; plugin marketplace packaging.

Each skill: research from vault → EDD (3+ eval cases for the skill itself) → SKILL.md → dogfood → iterate → next.

## 9. Risks

| Risk | Mitigation |
|---|---|
| Per-skill perfectionism without usage signal | Dogfood DoD per skill: "produced the real artifact, approved without rework" |
| Divergence from the personal agent-design skill | Plugin references, never copies; single source of truth |
| forge-master contract drift | Delegation uses only forge's public contract (PRD format + test runner exit code) |
| ADK churn (2 renames in 18 months, 2.0 breaking) | Version pinning + constraints files; adapter isolates framework surface |
| Builder gaming evals | PreToolUse hook + `/ship` git-diff audit — mechanical, not honor-system |
| Scope creep toward CrewAI/LlamaIndex adapters | Adapter architecture accepts new targets later; none built without a real client demand |
