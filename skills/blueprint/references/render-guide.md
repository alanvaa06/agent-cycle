# Render guide — agent-cycle:blueprint

A dated snapshot of the pipeline's artifacts, drawn for two readers: the
owner reviewing architecture at a glance, and a client seeing what they are
buying. One HTML file, offline-complete, no scripts required.

## Step 0 — Gate + inventory

design.md approved or refuse (write nothing, name the phase). Then inventory
what exists: spec.md (approved?), evals/config.yaml, build.md, skills.md,
interop.md, ship-report.md, <agent_name>-economics.md. Each present artifact
becomes a rendered section; each absent one becomes a 'pending' chip in the
progress bar. Record every artifact's version/date for the source stamp.

## Step 1 — Extract, never invent

All rendered data comes from the artifacts. The skill never invents
architecture, numbers, or status. Per artifact:
- design: PEAS table, environment classification, harness decision,
  deployment intent + seams, NO-goals.
- spec: capability list with BHV counts, tool inventory with tiers,
  conversation mechanics table, untrusted-surface table.
- evals: case counts by method, coverage N/N, thresholds, release blockers.
- build (when present): runtime + target, the REAL topology, runner command,
  recorded DoD status + date. The blueprint does NOT re-run the suite — it
  reports build.md's record, labeled with its date.
- skills/interop: their decisions (none/skip render as one-line states).
- economics: the scenario table, total bands, dominant-line statement, alarm
  threshold — verbatim numbers, never recomputed.
- ship-report: verdict + date.

## Step 2 — The diagram

Inline SVG (preferred) or pure HTML/CSS boxes. Pre-build: the spec's flow
(ingress → dedupe/allowlist → extract/route → loop+tools → reply) labeled
"intended (spec vN)". Post-build: the built topology — build.md's recorded runtime/target bound
onto the pipeline's invariant 5-binding shape (ingress → queue → worker →
state → egress, per the build skill's adapter-bindings) plus the spec's
tools — labeled "built (build vN)". Keep it under ~15 nodes; tiers color the tool nodes
(safe green / reversible amber / destructive red). No JavaScript — ever.
Collapsible detail uses native <details><summary>.

## Step 3 — Sanitize

Before writing: scan every rendered string. Env var NAMES are fine
(WA_OWNER_WA_ID); values never. No tokens, no credential fragments, no
internal record IDs, no API payloads. The blueprint is client-shareable by
default — sanitization is not optional.

## Step 4 — Assemble

Fill `references/blueprint-template.html` (copy its structure; inline
everything). Source stamp visible near the title: every artifact version +
generation date. Pipeline progress bar: seven phases + transversals, each
done/pending. Print-friendly: the CSS includes @media print; a client PDF
is one Ctrl+P away.

## Step 5 — Verify self-containment

Grep the produced file: no http://, https://, src= pointing outward, url(),
fetch(, XMLHttpRequest, <script src. Open from disk offline — full render.
Any external reference is a defect, not a nice-to-have violation.

## Step 6 — Present

Write docs/agent/blueprint.html (the only write). Tell the owner what it
covers, what is pending, and to regenerate after any phase completes — the
blueprint is disposable by design; the artifacts are the truth.
