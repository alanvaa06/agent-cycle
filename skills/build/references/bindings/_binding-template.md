# Build binding template

One file per active stack card, named `<card-id>.md`. Frontmatter
`version_pinned` must equal the card's `version_verified`
(`scripts/check_catalog.py` enforces it). Facts carry source URLs like cards.

```
---
card: <card-id>
version_pinned: <exact version>
---

# <Name> — build binding

## Sessions and state
<Postgres (incl. Supabase) / DynamoDB / Firestore: official store or the
adapter to write; per-session serialization (the queue guarantees one turn
per session); durability settings.>

## HITL gate
<How gated/destructive tiers pause for approval and resume; idempotency
rules for work done before the pause.>

## Caps
<Step cap and tool-call cap — native or own counter; the two are always
counted separately.>

## Model provider
<How the LiteLLM-style config string maps; non-native providers' caveats.>

## Telemetry
<OTel GenAI setup, token counters, and how to switch OFF any vendor egress.>

## Eval runner mapping
<Model double, trajectory capture, EXACT/IN_ORDER/ANY_ORDER mapping, caps
and harness_condition injection; pass^k is always computed by the pipeline
runner.>

## A2A and MCP
<A2A path (native / licensed / own a2a-sdk server) and MCP client.>

## Pinned version and traps
<Exact pins (and hash pinning where a card trap says so) plus the card's
traps restated as build obligations.>
```
