# Derivation guide — agent-cycle:spec

How to go from an approved design.md to a spec.md. Order matters.

## Step 0 — Gate check (before anything else)

Read `docs/agent/design.md`. Hard-fail (write nothing, say why, stop) if:
- the file does not exist → "run agent-cycle:design first";
- frontmatter `status` != `approved` → "design is draft; approve it at the
  design gate first";
- §8 Stack decision is missing, or has no "Chosen" stack (an approved design
  written before v0.11, or a §8 that never recorded a pick) → "design has no
  stack decision; re-open design per agent-cycle:design's re-entry rule";
Record `design_version` = the design's `version` field. Record `runtime` =
the value inside the backticks of design §8 "Chosen", nothing else
(`<card-id>@<version>`, `no-framework@n/a`, or `off-catalog:<name>@<version>`)
— never re-pick or re-version it here. If the user asks to
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
Every mandatory stack security row (the §8 list plus any rows added in Step 5)
gets at least one BHV scenario with an observable Then. For a trap that only
applies when a feature is used, the handling may read "feature not used:
<guard>", with a BHV asserting the feature is absent (e.g. the guarded tool
or option is never registered). Install-time rows are the one exception, see
Step 5.

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
credential and the PII/secrets outbound rules from the design's NO-goals.
Stack traps: copy design §8 "Mandatory spec security rows" into §4 — one row
each (handling = the obligation, e.g. "default trace exporter disabled"),
each traced to at least one BHV scenario (Step 3). Open the chosen card
(the agent-cycle plugin's `skills/design/references/stacks/<card-id>.md`) to
look up wording and URL for each listed trap, and check it for completeness:
every `[security]`/`[data]` trap of the card that is missing from §8's list is
ADDED as a row marked "not in design §8", and listed in the gate summary and
in §7 open questions. This is additive; it does not force a design re-entry.
Exception: an install-time supply-chain row (e.g. hash-pinning a package)
traces to "build rule 9 hash pins + ship lockfile check" instead of a BHV
scenario; no other row may use it. `off-catalog:` stacks: the rows are the §8
cons that are security or data risks plus the egress switch-off row when Q4
set an egress constraint (if §8's mandatory rows list is filled, copy it).
Data: define the app-owned tables (dedupe, pending record, turns) behind the
repository interface named in the design's sessions seam; for a
framework-owned store, name it (from §8 "Concrete per-seam binding") and do
not redefine its schema. The interface itself stays stack-neutral.

## Step 6 — Format tax check

Markdown headers throughout; YAML only for schemas nested >3 deep; tables over
prose for enumerable facts; no giant JSON blobs in prose. This is a performance
lever, not aesthetics.

## Step 7 — Traceability + gate

Fill §6 with one row per BHV (eval/test columns em-dash). Write spec.md with
status: draft. Present in chat: capability list, BHV count per capability,
tier changes vs design, the pinned `runtime`, the stack security rows table
(flagging rows added as "not in design §8"), untrusted-surface table, open
questions. Ask for
approval. On explicit approval only → status: approved. Hand off:
"Next: agent-cycle:evals reads this artifact."
