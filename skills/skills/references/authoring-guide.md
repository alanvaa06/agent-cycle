# Authoring guide — agent-cycle:skills

Only reached when the entry test flagged capabilities. Per skill, in order:

## Step 1 — EDD first

Before the skill's SKILL.md exists, write its eval cases: at least one
trigger-positive (a realistic task phrase that MUST route here), one
trigger-negative (an adjacent phrase that must NOT), one execution case
(input → expected procedure outcome). Store them next to the skill
(`<skill>/evals/cases.json`, same schema family as this plugin's own).

## Step 2 — Description as routing

The description is the routing algorithm — the only thing the router sees:
- WHAT it does (one clause), WHEN to use (concrete trigger phrases, the
  task-type vocabulary users actually say), when NOT to use (the adjacent
  cases that belong elsewhere).
- One skill = one job. If the description needs "and", split it.
- Ban "helpful skill for...", vendor prefixes, and vague nouns (utils/helper).

## Step 3 — Body and disclosure

Body carries the procedure only — steps, decision points, failure handling.
Depth goes to references the skill loads only when needed (progressive
disclosure). Smells: a body over ~500 lines; an ever-growing edge-case
section; content two teams could own; anything the STATIC instructions
already say (duplication drifts).

## Step 4 — Runtime binding

Declare in docs/agent/skills.md HOW this agent loads skills:
- **Harness-native** (Claude Code-class): folder discovery, description-based
  routing by the harness itself.
- **Custom loader** (built agents, e.g. a Pydantic AI service): the build's
  router/classifier selects by task type and injects the skill body into
  context for that turn only. If the build has no such mechanism, adding one
  is a BUILD change (re-entry to build), not something this phase improvises.

## Step 5 — Trigger accuracy

Target >=90%. Measure: at least 5 paraphrase variants per skill (include the
user's real language(s)), routed with ALL skills co-loaded; record hits and
misses per skill. Under 90% → sharpen the description (front-load trigger
vocabulary, tighten when-NOT), re-run fresh.

## Step 6 — Co-loaded regression

Never evaluate in isolation. Production loads every skill's metadata every
turn: run the full trigger suite and the agent's OWN eval suite (via /build's
runner) with all skills present. A skill that degrades unrelated turns
(token budget, routing collisions) fails regression even if it works alone.

## Step 7 — Authority ladder

Every skill enters at **draft** (advisory: procedure available, no new
privileges). Promotion to **action-allowed** (the skill's procedure includes
gated/destructive actions) requires: pass^k on its execution cases at the
tier the actions demand + explicit human approval, recorded per skill in
docs/agent/skills.md. Skills never expand the TOOL surface — tools are the
spec's; a skill teaches procedure over existing tools.

## Step 8 — Record and gate

docs/agent/skills.md: frontmatter (agent_name, version, status: draft, date,
spec_version, build_version), the entry-test table, per-skill: description,
eval results (trigger %, execution, regression), ladder status. Human gate →
status: approved. Hand off: "/ship audits this record; the agent's eval suite
now runs with skills co-loaded."
