# spec.md template

The skill fills this template and writes it to `docs/agent/spec.md` in the
TARGET AGENT'S repo. Default is ONE file; split into a `specs/` folder only if
the single file would exceed ~400 lines. Frontmatter is mandatory —
`design_version` pins which design this spec was derived from (staleness
detection: if design.md's version moves past it, this spec is stale).

---
agent_name: <same-as-design>
version: 1
status: draft            # draft | approved — approved ONLY via explicit human gate
date: <YYYY-MM-DD>
design_version: <version of the design.md consumed>
---

# <Agent Name> — Spec

## 1. Behavior (BHV)

One subsection per capability. Scenario ids are BHV-NNN, unique and sequential
across the whole file. Every capability: at least happy + wrong + edge. A
scenario that cannot fail is not a scenario.

### Capability: <name>

```gherkin
# BHV-001 (happy)
Scenario: <one-line intent>
  Given <precondition — concrete state, not vibes>
  When <the triggering message/event, verbatim-style>
  Then <observable outcome: reply content, tool call, state change>

# BHV-002 (wrong)
Scenario: <what goes wrong — bad input, API failure, ambiguity>
  Given ...
  When ...
  Then <graceful behavior: fallback reply, no partial writes, degraded flag>

# BHV-003 (edge)
Scenario: <boundary: empty result, limit hit, stale data, 24h window edge>
  ...
```

## 2. Tools

One block per tool. The docstring IS the interface — written for the model.
Schemas use extra=forbid semantics: unknown fields are rejected. Errors are
caught inside the tool and returned as observations, never raised.

### `<tool_name>` — tier: <safe | reversible | destructive> <(justification if tier differs from design's guess)>

**Docstring (verbatim, for the LLM):**
> <What it does, when to use it, when NOT to use it, what it returns.>

**Input schema** (YAML only if nested >3 deep, else inline table):

| Field | Type | Required | Constraint |
|---|---|---|---|
| <field> | <type> | yes/no | <bounds/enum/format> |

**Output:** <shape of the JSON returned, including the error-as-observation form>
**Gate implication:** <safe → auto | reversible → per design policy | destructive → HITL approval, never cached>

## 3. Conversation

Channel mechanics the agent must respect. For WhatsApp: 24h service window
behavior (what happens when it expires), fallback reply for unsupported input
types, non-owner / out-of-scope drop behavior (mirror the design's NO-goals),
debounce policy for rapid consecutive messages, language mirroring. For
channel-less agents: one line — "not applicable because <reason>".

## 4. Security

- **Untrusted surfaces** — one row per surface named in the design, no
  omissions:

| Surface | Why untrusted | Handling |
|---|---|---|
| <e.g. inbound WhatsApp text> | <attacker-writable> | <extraction boundary, never in system prompt, sanitized echo> |

- **Least privilege:** scopes per credential, read provisioned separately from
  write.
- **Injection posture:** what happens when embedded instructions are detected
  (per the design's NO-goals); which BHV scenarios cover it.
- **PII / secrets:** what never leaves the agent (mirror design NO-goals);
  outbound sanitization rules.

## 5. Data

Schemas for session/state/dedupe behind a repository interface (the design's
sessions seam). Tables/collections with fields, key strategy, TTLs. YAML for
anything nested >3 deep.

## 6. Traceability

Every BHV row exists here from day one; /evals fills the eval column, /build
fills the test column.

| BHV | Capability | Eval (filled by /evals) | Test (filled by /build) |
|---|---|---|---|
| BHV-001 | <capability> | — | — |

## 7. Open questions → /evals & /build

<Unresolved items for the next phases. Non-empty — if truly nothing is open,
state the single riskiest assumption instead.>
