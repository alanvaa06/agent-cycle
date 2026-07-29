---
name: blueprint
description: "Transversal skill of the agent-cycle pipeline: render a pipelined agent as one self-contained, client-shareable HTML page (docs/agent/blueprint.html) — PEAS/harness, architecture diagram, tools with tiers, security surfaces, eval coverage, economics embedded, pipeline progress — progressively from whatever artifacts exist. Use when the user wants the agent's blueprint/one-pager/visual — 'generate the blueprint', 'render the agent', 'página del agente para el cliente'. Requires an approved design.md. Do NOT use for generic diagrams outside the pipeline, nor to recompute economics or re-run evals (it renders their artifacts verbatim)."
---

# agent-cycle:blueprint — The Agent, On One Page

A dated snapshot for two readers: the owner reviewing at a glance, the
client seeing what they are buying. The artifacts are the truth; this page
is a photo.

## Hard rules

1. GATE: design.md approved. Everything else renders progressively; absent
   phases appear as honest pending states — never faked, never omitted.
2. EXTRACT, NEVER INVENT: every rendered fact comes from a pipeline
   artifact. No imagined architecture, no recomputed numbers — economics is
   embedded verbatim; suite status is build.md's record labeled with its
   date (the blueprint re-runs nothing).
3. STRICTLY SELF-CONTAINED: one .html file, zero external references (no
   CDN, fonts, images, fetch); opens fully offline. Verified by grep before
   presenting.
4. NO JAVASCRIPT REQUIRED: diagrams are inline SVG or pure HTML/CSS;
   collapsibles are native details/summary; print-friendly CSS included.
5. SANITIZED BY DEFAULT: env var names allowed, values never; no tokens,
   internal IDs, or payloads. Client-shareable is the bar.
6. DATED SNAPSHOT, NOT A CONTRACT: source versions + generation date
   visible on the page; no draft/approved status of its own; regenerate
   after any phase completes.
7. The ONLY write: docs/agent/blueprint.html.

## Workflow

1. Read `references/render-guide.md`; run steps 0→6 in order.
2. Structure and styling come from `references/blueprint-template.html` —
   inline everything, fill every section that has an artifact, mark the
   rest pending.
3. Verify self-containment (grep) and sanitization before presenting.
4. Present: what it covers, what is pending, when to regenerate.

## Failure modes to avoid

- Rendering an architecture the artifacts don't state (rule 2).
- A CDN font or external icon "just for polish" (rule 3).
- A script tag for a collapsible details already handles (rule 4).
- An env VALUE or internal ID in a client-facing page (rule 5).
- Treating the blueprint as an approval artifact (rule 6).
- Recomputing economics "to freshen the numbers" (rule 2 — that is the
  economics skill's calibration job).
