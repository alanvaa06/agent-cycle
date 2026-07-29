# agent-cycle `/blueprint` Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship transversal 2 of 2 — `agent-cycle:blueprint` — the self-contained HTML rendering of a pipelined agent: architecture, tools with tiers, flows, security surfaces, BHV coverage, the real runtime graph post-build, and the economics table embedded. Progressive by available artifacts; a dated snapshot, not an app. Then release v0.9.0.

**Architecture:** Same shape (EDD cases → two references → SKILL.md). Core stances from plugin design §5.2 + hard rules learned this cycle: minimum gate is an approved design.md, everything else renders progressively with absent phases marked honestly (a pipeline progress bar is part of the blueprint); STRICT self-containment (zero external URLs — no CDN, no fonts, no fetch; one .html file that opens offline); no JS required (native `<details>` for collapsibles; SVG/CSS for diagrams — the graph is drawn, not scripted); the blueprint is a DATED SNAPSHOT carrying its source-artifact versions visibly, regenerable at will, so it has no draft/approved status of its own; client-shareable means SANITIZED (zero secrets, tokens, internal IDs); economics is embedded as stated by its artifact, never recomputed. The only write: `docs/agent/blueprint.html`.

**Tech Stack:** Claude Code plugin format, Markdown/JSON only (the skill GENERATES HTML).

**Spec:** `docs/superpowers/specs/2026-07-28-agent-cycle-plugin-design.md` § 5.2.

---

### Task 1: EDD eval cases — before the skill exists

**Files:**
- Create: `skills/blueprint/evals/cases.json`
- Create: `skills/blueprint/evals/README.md`
- Create: `skills/blueprint/evals/results.md`

- [ ] **Step 1: Write the eval cases**

Write `skills/blueprint/evals/cases.json`:

```json
{
  "skill": "agent-cycle:blueprint",
  "spec_ref": "docs/superpowers/specs/2026-07-28-agent-cycle-plugin-design.md#52-agent-cycleblueprint",
  "cases": [
    {
      "id": "BLP-E01",
      "type": "positive-progressive",
      "input": "Generate the agent blueprint. (Run in a repo with approved design+spec+evals+economics but NO build yet, e.g. the real whatsapp-owner-assistant pre-build.)",
      "expected": {
        "fires": true,
        "checks": [
          "Gate: design.md approved is the only hard requirement; every other artifact renders when present and absent phases appear as honest 'pending' states in a visible pipeline progress indicator",
          "STRICT self-containment verified: zero external URLs anywhere in the HTML (no CDN, no web fonts, no fetch/XHR, no external images) — checkable by grep for http:// and https:// (only harmless inert mentions inside visible text may remain, no src/href/url() references); one single .html file that opens offline",
          "Sections present per available artifact: PEAS + environment + harness (design); tools with color-coded tiers, conversation mechanics, untrusted-surface table (spec); BHV→eval coverage from spec §6 + evals config (evals); the economics table embedded with bands and the alarm threshold, taken verbatim from the economics artifact — never recomputed",
          "Architecture/graph rendered as inline SVG or pure HTML/CSS (no JavaScript required for any content; native details/summary for collapsibles); pre-build the diagram shows the spec's intended flow, marked as intended",
          "Source versions visible in the rendered page: design vN, spec vN, evals config date, economics version, plus the generation date — the blueprint is a dated snapshot, regenerable, carrying no draft/approved status of its own",
          "Sanitized for client sharing: zero secrets, tokens, credential values, internal IDs, or env values anywhere in the HTML — env var NAMES are acceptable, values never",
          "The only write is docs/agent/blueprint.html; the skill presents the result and offers regeneration guidance (re-run after any phase completes)"
        ]
      }
    },
    {
      "id": "BLP-E02",
      "type": "gate-negative",
      "input": "Generate the agent blueprint. (Run twice: once with no docs/agent/design.md, once where design.md has status: draft.)",
      "expected": {
        "fires": true,
        "checks": [
          "Refuses in both branches: names the gate (no design / design draft → run agent-cycle:design first) and stops",
          "Writes NO files in either branch — verified on the filesystem afterward"
        ]
      }
    },
    {
      "id": "BLP-E03",
      "type": "edge-post-build",
      "input": "Generate the agent blueprint. (Run against a fixture repo where build.md exists approved with runner results, and a ship-report.md exists.)",
      "expected": {
        "fires": true,
        "checks": [
          "The runtime graph section renders the REAL built topology (loop, tools, adapter bindings from build.md's recorded runtime/target) instead of the intended-flow placeholder, and is labeled as built",
          "Traceability shows the Test column populated and the suite status from build.md's recorded DoD (labeled as of that build's date — the blueprint does not re-run anything)",
          "The ship verdict (SHIP/NO-SHIP + date) appears when ship-report.md exists"
        ]
      }
    },
    {
      "id": "BLP-E04",
      "type": "trigger-negative",
      "input": "Make me an architecture diagram for my REST API — boxes for the services and the database.",
      "expected": {
        "fires": false,
        "checks": [
          "agent-cycle:blueprint does NOT fire — generic diagramming outside the pipeline",
          "No files are created or modified — verified on the filesystem afterward"
        ]
      }
    }
  ]
}
```

- [ ] **Step 2: Write the run procedure**

Write `skills/blueprint/evals/README.md`:

```markdown
# Eval procedure for agent-cycle:blueprint

Same agentic procedure as `skills/design/evals/README.md` (fresh session,
per-check PASS/FAIL rows in `results.md`, fix-and-rerun, dispute — never
silently edit — if a case is wrong).

Case-specific setup:

- **BLP-E01** is the real dogfood run (pre-build state of the real repo
  qualifies today). Score self-containment by actually grepping the produced
  HTML for `http://`, `https://`, `src=`, `href=`, `url(`, `fetch(`,
  `XMLHttpRequest` — any external reference is a FAIL. Open the file from
  disk with networking off (or devtools network tab empty) — it must render
  fully.
- **BLP-E02**: scratch repos; filesystem check afterward.
- **BLP-E03** fixture: copy the real repo and hand-write a minimal approved
  build.md (with runtime, target, runner command, a recorded green DoD) and a
  minimal ship-report.md. ~20 min; do NOT run the build skill for it.
- **BLP-E04**: filesystem check afterward.

Scoring anchors: the sanitization check is scored by grepping the HTML for
every value in the repo's .env.example patterns and any token-like string —
NAMES may appear, values never. The economics check is scored by diffing the
embedded numbers against the economics artifact — identical or FAIL (no
recomputation drift).
```

- [ ] **Step 3: Create the results log**

Write `skills/blueprint/evals/results.md`:

```markdown
# Eval runs — agent-cycle:blueprint

One row per check, per run. Verdict: PASS / FAIL. Evidence: one line.

| Date | Case | Check # | Verdict | Evidence |
|---|---|---|---|---|
```

- [ ] **Step 4: Verify JSON**

Run: `python -c "import json; d=json.load(open(r'skills/blueprint/evals/cases.json')); print(len(d['cases']), 'cases,', len(d['cases'][0]['expected']['checks']), 'checks in E01')"`
Expected: `4 cases, 7 checks in E01`

- [ ] **Step 5: Commit**

```bash
git add skills/blueprint/evals/
git commit -m "feat(blueprint): EDD eval cases before SKILL.md (BLP-E01..E04)"
```

---

### Task 2: Render guide

**Files:**
- Create: `skills/blueprint/references/render-guide.md`

- [ ] **Step 1: Write the guide**

Write `skills/blueprint/references/render-guide.md`:

```markdown
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
"intended (spec vN)". Post-build: the built topology from build.md labeled
"built (build vN)". Keep it under ~15 nodes; tiers color the tool nodes
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
```

- [ ] **Step 2: Commit**

```bash
git add skills/blueprint/references/render-guide.md
git commit -m "feat(blueprint): render guide (extract never invent, sanitize, self-containment verify)"
```

---

### Task 3: HTML template

**Files:**
- Create: `skills/blueprint/references/blueprint-template.html`

- [ ] **Step 1: Write the template**

Write `skills/blueprint/references/blueprint-template.html`:

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{AGENT_NAME}} — Agent Blueprint</title>
<style>
  :root{
    --bg:#ffffff; --ink:#1a1d21; --muted:#5b6470; --line:#e3e6ea;
    --safe:#1a7f4b; --rev:#b07d0f; --destr:#b3261e;
    --chip:#eef1f4; --accent:#274b8f; --pending:#9aa3ad;
  }
  @media (prefers-color-scheme: dark){
    :root{ --bg:#14161a; --ink:#e8eaed; --muted:#9aa3ad; --line:#2a2e34;
           --chip:#22262c; --accent:#7ea2e6; }
  }
  *{box-sizing:border-box}
  body{margin:0;padding:2rem;background:var(--bg);color:var(--ink);
       font:15px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
       max-width:960px;margin-inline:auto}
  h1{font-size:1.6rem;margin:0 0 .25rem}
  h2{font-size:1.15rem;border-bottom:1px solid var(--line);
     padding-bottom:.35rem;margin-top:2.2rem}
  .stamp{color:var(--muted);font-size:.8rem;margin-bottom:1.5rem}
  .stamp code{background:var(--chip);padding:.1rem .4rem;border-radius:4px}
  .progress{display:flex;flex-wrap:wrap;gap:.4rem;margin:1rem 0}
  .phase{padding:.25rem .65rem;border-radius:999px;font-size:.78rem;
         background:var(--chip);color:var(--pending)}
  .phase.done{background:var(--accent);color:#fff}
  table{border-collapse:collapse;width:100%;font-size:.88rem;margin:.6rem 0}
  th,td{border:1px solid var(--line);padding:.45rem .6rem;text-align:left;
        vertical-align:top}
  th{background:var(--chip)}
  .tier-safe{color:var(--safe);font-weight:600}
  .tier-reversible{color:var(--rev);font-weight:600}
  .tier-destructive{color:var(--destr);font-weight:600}
  .band{font-variant-numeric:tabular-nums;font-weight:600}
  details{border:1px solid var(--line);border-radius:8px;padding:.6rem .9rem;
          margin:.5rem 0}
  summary{cursor:pointer;font-weight:600}
  figure{margin:1rem 0;overflow-x:auto}
  .pending-note{color:var(--pending);font-style:italic}
  .verdict{display:inline-block;padding:.3rem .8rem;border-radius:6px;
           font-weight:700}
  .verdict.ship{background:var(--safe);color:#fff}
  .verdict.noship{background:var(--destr);color:#fff}
  @media print{
    body{padding:0;max-width:none} details{page-break-inside:avoid}
    .phase{border:1px solid var(--line)}
  }
</style>
</head>
<body>

<h1>{{AGENT_NAME}} — Agent Blueprint</h1>
<div class="stamp">
  Snapshot generated {{GEN_DATE}} from:
  design <code>v{{DESIGN_V}}</code> · spec <code>v{{SPEC_V}}</code> ·
  evals <code>{{EVALS_DATE}}</code> · build <code>{{BUILD_STATE}}</code> ·
  economics <code>{{ECO_STATE}}</code>. Regenerate after any phase completes —
  the artifacts are the truth, this page is a photo.
</div>

<div class="progress">
  <!-- one .phase per pipeline step; add class="done" when its artifact is approved -->
  <span class="phase">design</span><span class="phase">spec</span>
  <span class="phase">evals</span><span class="phase">build</span>
  <span class="phase">skills</span><span class="phase">interop</span>
  <span class="phase">ship</span><span class="phase">economics</span>
</div>

<h2>1 · What this agent is (design)</h2>
<!-- PEAS table, environment classification, harness decision, NO-goals list.
     Data verbatim from design.md. -->

<h2>2 · Architecture</h2>
<figure>
  <!-- Inline SVG here. Pre-build: spec's intended flow, caption
       "intended (spec vN)". Post-build: built topology, caption
       "built ({{BUILD_STATE}})". Tool nodes colored by tier via the
       tier- classes. <15 nodes. NO external images, NO scripts. -->
</figure>

<h2>3 · Tools &amp; tiers (spec)</h2>
<!-- table: tool | purpose | tier (class tier-safe / tier-reversible /
     tier-destructive) | untrusted output? -->

<h2>4 · Conversation &amp; security (spec)</h2>
<!-- conversation mechanics table + untrusted-surface table inside
     <details> blocks -->

<h2>5 · Evals &amp; coverage</h2>
<!-- counts by method, coverage N/N, thresholds incl. pass^k, release
     blockers. Post-build: suite status from build.md labeled with its date. -->

<h2>6 · Economics</h2>
<!-- scenario table + total bands (class band) + dominant-line sentence +
     alarm threshold — VERBATIM from the economics artifact. If absent:
     <p class="pending-note">Economics pending — run agent-cycle:economics.</p> -->

<h2>7 · Status</h2>
<!-- skills decision · interop decision · ship verdict when present:
     <span class="verdict ship">SHIP</span> / <span class="verdict noship">NO-SHIP</span>
     with date. Pending phases named honestly. -->

</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add skills/blueprint/references/blueprint-template.html
git commit -m "feat(blueprint): self-contained HTML template (progress bar, tier colors, print-ready, zero JS)"
```

---

### Task 4: SKILL.md

**Files:**
- Create: `skills/blueprint/SKILL.md`

- [ ] **Step 1: Write the skill**

Write `skills/blueprint/SKILL.md`:

```markdown
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
```

- [ ] **Step 2: Verify frontmatter**

Run: `head -4 skills/blueprint/SKILL.md`
Expected: `---`, `name: blueprint`, description present.

- [ ] **Step 3: Commit**

```bash
git add skills/blueprint/SKILL.md
git commit -m "feat(blueprint): SKILL.md — extract never invent, self-contained, sanitized snapshot"
```

---

### Task 5: Release v0.9.0

- [ ] **Step 1:** plugin.json version → `0.9.0`.
- [ ] **Step 2:** README status line → `**Status:** v0.9.0 — all 7 phases + both transversals (\`economics\`, \`blueprint\`).\nThe original 9-skill pipeline is complete. Built skill-by-skill, each dogfooded\non a real agent.`
- [ ] **Step 3:** CHANGELOG entry before `## [0.8.1]`:

```markdown
## [0.9.0] — 2026-07-29

### Added
- **`blueprint` skill** (transversal 2 of 2 — completes the original 9-skill
  pipeline): one self-contained, client-shareable HTML snapshot of the agent
  rendered progressively from whatever artifacts exist (design gate only) —
  PEAS/harness, tier-colored tools, security surfaces, eval coverage,
  economics embedded verbatim (never recomputed), pipeline progress bar,
  ship verdict when present. Zero external references, zero required
  JavaScript, print-ready, sanitized by default (env names yes, values
  never). Dated snapshot carrying its source versions — regenerable, no
  approval status of its own. Only write: docs/agent/blueprint.html.
- EDD eval suite (`skills/blueprint/evals/`): BLP-E01 positive-progressive
  (7-check contract incl. grep-verified self-containment), BLP-E02
  gate-negative, BLP-E03 post-build edge (real topology, ship verdict),
  BLP-E04 trigger-negative (generic diagramming must not fire).

### Pending graduation
- `blueprint` run against the real agent — tag `blueprint-v0.1` when the
  dogfood passes (runnable TODAY: pre-build progressive render qualifies).
```

- [ ] **Step 4:** Verify version prints `0.9.0`; commit `chore: release v0.9.0 (blueprint skill)`.

---

### Task 6 (Alan, interactive): eval runs + dogfood

- [ ] BLP-E02 ×2, BLP-E04 in scratch; BLP-E03 with the hand-written build/ship fixture → rows in results.md.
- [ ] BLP-E01 dogfood in `C:\Proyectos\Whatsapp_agent` — runnable NOW (pre-build progressive render is the case) → tag `blueprint-v0.1`. Re-run after BLD-E01 for the built-topology upgrade.
- [ ] Marketplace update + reinstall for v0.9.0.

---

## Self-review (done at planning time)

- **§5.2 coverage:** progressive rendering by artifact ✓ (E01 check 1, guide step 0); graph extracted mechanically post-build / intended-flow pre-build ✓ (E03 check 1, guide step 2 — §5.2's "ADK Workflow" example generalized to build.md's recorded topology per the runtime-is-law rule); economics embedded ✓ (verbatim rule — stronger than §5.2's "consumes the artifact"); self-contained HTML per the Artifact/HTML-output thesis ✓ (strict grep-verified rule); template fixed + injected data = low maintenance ✓ (blueprint-template.html shipped).
- **Lessons applied:** no workspace assumptions (template self-contained, no mermaid/CDN dependency — mermaid needs a JS runtime, so diagrams are SVG/CSS); sanitization as a first-class check (client deliverable); snapshot-no-status avoids a fake approval gate on a regenerable view.
- **Check counts:** E01=7, E02=2, E03=3, E04=2 — match cases.json.
```
