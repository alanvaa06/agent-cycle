# Derivation guide — agent-cycle:spec

How to go from an approved design.md to a spec.md. Order matters.

## Step 0 — Gate check (before anything else)

Read `docs/agent/design.md`. Hard-fail (write nothing, say why, stop) if:
- the file does not exist → "run agent-cycle:design first";
- frontmatter `status` != `approved` → "design is draft; approve it at the
  design gate first";
Record `design_version` = the design's `version` field. If the user asks to
change something the design already decided (scope, tools, deployment,
NO-goals), do NOT fold it in here — that is the re-entry ladder: the design
must be re-opened, bumped, and re-approved first.

## Step 1 — Capability extraction (no interview)

Derive the capability list mechanically from the design: Actuators + Sensors
define what the agent can do; the Performance metric defines what it is FOR.
List capabilities as verb phrases ("answer calendar availability questions",
"find and summarize Notion pages"). Show the list to the user as ONE
confirmation question — "these N capabilities, complete?" — before writing
scenarios.

## Step 2 — Interview: open questions ONLY

The design's §7 open questions are the entire interview agenda. One question
per message, multiple choice where possible. Do not re-ask anything §§1-6 of
the design already answers. Typical open questions land here as: tool tier
finalization (e.g. an irreversible send), session TTL values, secret storage,
baseline measurement protocol. If an answer contradicts the approved design →
stop, name the contradiction, route to the re-entry ladder.

## Step 3 — Behavior scenarios

Per capability, write Gherkin: happy first, then wrong (API failure, ambiguous
request, empty result), then edge (limits, staleness, window boundaries).
Number BHV-NNN sequentially across the file. Quality bar per scenario:
- Given states concrete state (a fixture, not "some events exist");
- When is a realistic user message or event, quotable;
- Then is observable (reply text contains X / tool Y called with Z / no write
  occurred / degraded flag set). A scenario that cannot fail does not count.
Security scenarios are behavior too: every untrusted surface gets at least one
injection-attempt scenario whose Then is "instructions treated as data".

## Step 4 — Tool contracts

One per design §4 tool, no more, no less (a new tool = design change → re-entry
ladder). Count DISTINCT tool operations, not table rows: a row naming two tools
(e.g. `session_read / session_write`) needs two separate contracts. Docstring written for the model: what/when/when-NOT/returns. Schemas
extra=forbid. Errors as observations. FINAL tier per tool: confront each design
tier guess — if it changes (e.g. a WhatsApp send is irreversible), one-line
justification. Tier → gate implication is mechanical: safe=auto,
destructive=HITL never-cached.

## Step 5 — Conversation, Security, Data

Conversation: channel mechanics from the design's Environment (24h window,
fallbacks, drop rules, language). Mechanics the design is silent on (e.g.
debounce for rapid consecutive messages) are DECIDED here — ask the user (one
question, counts as a spec-level open topic) and itemize them in the gate
summary. Security: every untrusted surface from the design gets a handling row
+ a BHV scenario reference; untrusted status follows the DESIGN's threat model,
not a blanket per-channel default (an owner-only channel with allowlist
enforcement may be trusted by design). Also cover least-privilege scoping per
credential and the PII/secrets outbound rules from the design's NO-goals. Data:
schemas behind the repository interface named in the design's sessions seam.

## Step 6 — Format tax check

Markdown headers throughout; YAML only for schemas nested >3 deep; tables over
prose for enumerable facts; no giant JSON blobs in prose. This is a performance
lever, not aesthetics.

## Step 7 — Traceability + gate

Fill §6 with one row per BHV (eval/test columns em-dash). Write spec.md with
status: draft. Present in chat: capability list, BHV count per capability,
tier changes vs design, untrusted-surface table, open questions. Ask for
approval. On explicit approval only → status: approved. Hand off:
"Next: agent-cycle:evals reads this artifact."
