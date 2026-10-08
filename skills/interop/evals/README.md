# Eval procedure for agent-cycle:interop

Same agentic procedure as `skills/design/evals/README.md` (fresh session,
per-check PASS/FAIL rows in `results.md`, fix-and-rerun, dispute — never
silently edit — if a case is wrong).

Case-specific setup:

- The real whatsapp-owner-assistant fixture is pre-v0.11: it has no design
  §8 and no spec `runtime`. It needs design re-entry (Phase E) and a spec
  version bump with `runtime` before ITP-E01 can run (or use a copy with §8 +
  `runtime` added).
- **ITP-E01** is the real dogfood run: the whatsapp-owner-assistant's
  relationships (Google Calendar, Notion, Supabase, Meta — all bounded
  result-lookups behind tools) are expected to produce decision: skip. The
  per-relationship table is required — a bare "doesn't need A2A" is a FAIL
  even though the conclusion is right.
- **ITP-E02** needs a hand-written scratch pipeline (design+spec+build.md,
  minimal but approved) whose spec names a genuine multi-turn delegation to
  an external specialist agent. The scratch spec must carry `runtime:` and
  name a stack that exercises "licensed vs free" (e.g. langgraph: licensed
  Agent Server vs own a2a-sdk server). Budget ~45 min; do NOT use the pipeline
  skills to author the fixture.
- **ITP-E03** branch 2: copy the real repo, bump spec.md to version 2 leaving
  build.md's spec_version at 1.
- **ITP-E04**: filesystem check afterward.

Scoring anchors: the entry-test check requires one row per external system
named in the spec's tools/security sections (for the real agent: Calendar,
Notion, Supabase, Meta WhatsApp) — a missing row is a FAIL. The GOTO-problem
check (E02) requires the words to appear with the reasoning, not as decoration.
