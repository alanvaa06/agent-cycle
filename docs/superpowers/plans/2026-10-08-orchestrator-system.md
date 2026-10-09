# agent-cycle v0.13 — Orchestrator Agents Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a workspace agent act as an orchestrator that delegates to other workspace agents over the network, with a justification test, a delegates table, recorded delegate responses, published inbound contracts and ship-time contract checks.

**Architecture:** No new skill and no hook change. Existing skills gain an orchestrator branch: design §9 Delegation (justification + inventory), spec §8 Delegates, evals recorded delegate responses, interop "Inbound contracts" with a side-effect-free probe, ship checks on both sides (orchestrator: gate + contract + live probe; delegate: contract-bump block), runbook weekly live probe. Eval cases are written first (EDD).

**Tech Stack:** Claude Code plugin (Markdown/JSON). No Python changes.

**Spec:** `docs/superpowers/specs/2026-10-08-orchestrator-system-design.md`

---

## Conventions used by every task

**Branch.** `feat/v0.13-system` (already created from `main` at `v0.12.0`). Never commit to `main`; never switch branches.

**Commit trailer.** End every commit message with the `Co-Authored-By:` line your own harness attribution reminder specifies.

**Checks** (run from the repo root before every commit):

```bash
python -m pytest tests -q
python scripts/check_catalog.py --root .
python -c "import json,glob; [json.load(open(p,encoding='utf-8')) for p in glob.glob('skills/*/evals/cases.json')]; print('[ok] all cases.json parse')"
```

Expected: `305 passed`; `PASS: 9 card(s); cards, index and bindings consistent`; `[ok] all cases.json parse`.

**Plugin paths.** Skills run in the TARGET repo; refer to plugin files as "the agent-cycle plugin's `<path>`".

**Console output** of any Python stays ASCII-only.

**Line endings.** The index stores LF; the working tree may be CRLF. Check each file before editing and preserve its endings. Never `sed -i` a CRLF file. When writing through Python, `"\n"` inside a string literal is a real newline: verify bytes after writing.

**Insertion anchors.** Each step quotes the existing line to insert after or the text to replace. If an anchor is not found exactly once, STOP and report; do not guess.

**Vocabulary (use exactly):** orchestrator, delegate, design §9 Delegation, spec §8 Delegates, Inbound contracts, probe request, contract version (`<agent>-contract@<n>`), recorded delegate responses.

---

### Task 1: EDD eval cases — before any skill text changes

**Files:**
- Modify: `skills/design/evals/cases.json` (append DES-E09, DES-E10)
- Modify: `skills/spec/evals/cases.json` (append SPC-E06)
- Modify: `skills/evals/evals/cases.json` (append EVL-E05)
- Modify: `skills/interop/evals/cases.json` (append ITP-E05)
- Modify: `skills/ship/evals/cases.json` (append SHP-E06, SHP-E07)
- Modify: the `evals/README.md` of design, spec, evals, interop, ship (fixture notes)

- [ ] **Step 1: Append to `skills/design/evals/cases.json` `cases` array**

```json
{
  "id": "DES-E09",
  "type": "edge-orchestrator-not-justified",
  "input": "Design an agent 'recepcion' that sends sales questions to ventas and support questions to soporte. (Fixture: workspace with agents [ventas, soporte], both approved; the user says the split is only by keyword in the first message and both agents already have their own WhatsApp numbers the customer can use directly.)",
  "expected": {
    "fires": true,
    "checks": [
      "Runs the mechanical-routing check first, before the four reasons and before inventorying delegates, and records it in design.md §9 Delegation",
      "Concludes 'router without an LLM' because routing is by keyword, even though the reuse reason holds (ventas and soporte have their own channels); states that reuse justifies separate agents, not an LLM in front of them",
      "No delegate inventory is written and no orchestrator design is produced; it states that the router lives outside agent-cycle and stops",
      "Does not modify anything under agents/ventas/ or agents/soporte/"
    ]
  }
},
{
  "id": "DES-E10",
  "type": "edge-orchestrator-justified",
  "input": "Design an agent 'recepcion' that talks to customers on the web chat, decides whether they need ventas or soporte, and hands the conversation to that agent; it also uses an internal 'resumidor' helper that only it uses. (Fixture: workspace with agents [ventas, soporte]; ventas is built and its interop.md has no Inbound contracts section; soporte has an approved design only.)",
  "expected": {
    "fires": true,
    "checks": [
      "design.md §9 Delegation records the justification test with at least one of the four reasons tied to a fact (e.g. reuse: ventas and soporte have their own channels and releases)",
      "§9 lists ventas and soporte as delegates (both names from agent-cycle.yaml), each with what it is used for and the reason it serves",
      "'resumidor' is NOT a delegate: it stays as an internal subagent/subgraph of recepcion (§3 / §8), not a workspace agent",
      "Warns that ventas is already built without an inbound interface for recepcion, so adding it is a build re-entry of ventas (interop rule 7); advises designing the orchestrator before building delegates without requiring it",
      "Reads agents/ventas and agents/soporte design.md / interop.md only; writes only agents/recepcion/docs/agent/design.md and appends 'recepcion' to agent-cycle.yaml"
    ]
  }
}
```

- [ ] **Step 2: Append to `skills/spec/evals/cases.json` `cases` array**

```json
{
  "id": "SPC-E06",
  "type": "edge-orchestrator-delegates",
  "input": "Write the spec for recepcion. (Fixture: workspace; agents/recepcion/docs/agent/design.md approved with §9 Delegation listing ventas and soporte; agents/ventas/docs/agent/interop.md approved with Inbound contracts publishing ventas-contract@1; soporte has no interop.md yet.)",
  "expected": {
    "fires": true,
    "checks": [
      "spec.md §8 Delegates has one row per delegate with every column: Delegate, Used by (BHV ids), Input, Output, Contract, On failure",
      "ventas's row pins Contract ventas-contract@1 (read from ventas's interop.md); soporte's row reads Contract: pending and the spec states ship is blocked until it is pinned",
      "Each On failure entry names what recepcion does when the delegate is down, times out, or returns invalid output",
      "Delegates are treated as untrusted: §4 lists each delegate's replies as an untrusted surface with handling, and the credential each delegate requires is a row in §4's least-privilege table",
      "Writes only agents/recepcion/docs/agent/spec.md"
    ]
  }
}
```

- [ ] **Step 3: Append to `skills/evals/evals/cases.json` `cases` array**

```json
{
  "id": "EVL-E05",
  "type": "edge-orchestrator-recorded-responses",
  "input": "Write the eval suite for recepcion. (Fixture: approved spec with §8 Delegates: ventas pinned ventas-contract@1 with On failure 'down -> tell the user and offer a human; timeout -> retry once then tell the user; invalid -> tell the user'; soporte pinned soporte-contract@2.)",
  "expected": {
    "fires": true,
    "checks": [
      "Every delegate is replaced by recorded delegate responses in the case fixtures (fixture.delegates), none calls a real delegate",
      "Per delegate: at least one golden case with a valid recorded response, and one case per On failure mode in its spec row (ventas: down, timeout, invalid)",
      "Per delegate: at least one adversarial case whose recorded reply carries injected instructions or asks for a gated action; expected: treated as data and the gated action still requires HITL",
      "Each recording carries the contract version it was taken from (ventas-contract@1, soporte-contract@2)",
      "Writes only agents/recepcion/evals/ plus the Eval column of agents/recepcion/docs/agent/spec.md §6"
    ]
  }
}
```

- [ ] **Step 4: Append to `skills/interop/evals/cases.json` `cases` array**

```json
{
  "id": "ITP-E05",
  "type": "edge-orchestrator-inbound-contract",
  "input": "Run interop for ventas. (Fixture: workspace; ventas built and approved through build; agents/recepcion/docs/agent/design.md §9 Delegation names ventas as a delegate that receives one question and returns one answer.)",
  "expected": {
    "fires": true,
    "checks": [
      "The relationship inventory includes 'recepcion calls ventas', found by reading recepcion's design §9 (read-only)",
      "The entry test gives that relationship a verdict with a reason (single request -> single result here, so a simple call, not A2A)",
      "interop.md has an Inbound contracts section with caller, input schema, output schema, contract version ventas-contract@1, and one side-effect-free probe request with its expected response shape",
      "If ventas has no handler for that interface, it is routed to a build re-entry of ventas, not improvised",
      "Writes only agents/ventas/docs/agent/interop.md (plus agent-card.json / executor config only if the verdict is A2A)"
    ]
  }
}
```

- [ ] **Step 5: Append to `skills/ship/evals/cases.json` `cases` array**

```json
{
  "id": "SHP-E06",
  "type": "edge-orchestrator-delegates-gate",
  "input": "Ship recepcion. (Fixture: workspace; recepcion fully through interop with spec §8 Delegates pinning ventas-contract@1 and soporte-contract@1; ventas has approved interop.md (ventas-contract@1) and approved ship-report.md; soporte has approved interop.md but no ship-report.md. Second run: soporte shipped too, both delegates deployed.)",
  "expected": {
    "fires": true,
    "checks": [
      "First run: refuses, naming soporte and the missing phase (its ship), and writes nothing",
      "Second run: Section 3 Delegates compares each pinned contract version with the delegate's interop.md (cites the command and output)",
      "Second run: one live call per delegate using the delegate's published probe request (never a writing or gated request); the response validates against the pinned output schema; command and output cited",
      "Second run: recepcion's delegate credentials are included in the least-privilege diff",
      "Second run: writes only agents/recepcion/docs/agent/ship-report.md (the first run writes nothing)"
    ]
  }
},
{
  "id": "SHP-E07",
  "type": "edge-delegate-contract-bump",
  "input": "Ship ventas. (Fixture: workspace; ventas's interop.md now publishes ventas-contract@2 and its Inbound contracts no longer serve @1; agents/recepcion/docs/agent/spec.md §8 pins ventas-contract@1.)",
  "expected": {
    "fires": true,
    "checks": [
      "Reads every other agent's spec §8 (read-only) and finds recepcion pinning ventas-contract@1",
      "Reports a blocker: shipping @2 while @1 is pinned and not served would break recepcion; routes to recepcion (spec re-entry and re-recording) or to ventas (keep serving @1)",
      "Verdict is NO-SHIP while the blocker stands; with the fixture changed so ventas still serves @1, the check passes",
      "Writes only agents/ventas/docs/agent/ship-report.md"
    ]
  }
}
```

- [ ] **Step 6: README fixture notes**

Append an `## Orchestrator cases (v0.13)` section to each named README, built in a scratch git repo (never this repo), hand-written minimal artifacts (do NOT use the pipeline skills to author fixtures):
- `skills/design/evals/README.md`: DES-E09 (workspace `agents: [ventas, soporte]`, both with an approved trivial design.md; score with `git status --porcelain` that nothing outside `agents/recepcion/` and the yaml line changed — for "router without an LLM", nothing at all), DES-E10 (ventas also has `docs/agent/build.md` approved and an `interop.md` without Inbound contracts).
- `skills/spec/evals/README.md`: SPC-E06 (recepcion design with §9; ventas interop.md with an Inbound contracts block `ventas-contract@1`).
- `skills/evals/evals/README.md`: EVL-E05 (approved recepcion spec with the §8 table from the case input).
- `skills/interop/evals/README.md`: ITP-E05 (ventas design/spec/build.md approved; recepcion design.md with §9).
- `skills/ship/evals/README.md`: SHP-E06 (two runs; for the live probe, a stub HTTP server per delegate answering the probe request is enough), SHP-E07 (ventas interop.md with `ventas-contract@2`, recepcion spec §8 pinning `@1`).

- [ ] **Step 7: Run the checks, then commit**

```bash
git add skills/*/evals/cases.json skills/*/evals/README.md
git commit -m "test(evals): v0.13 orchestrator eval cases (EDD first)"
```

---

### Task 2: `references/agent-root.md` — cross-agent read exceptions

**Files:**
- Modify: `references/agent-root.md` (first bullet of `## Rules`)

- [ ] **Step 1: Replace the end of the first `## Rules` bullet**

Old text (exact):

```
  of a sanctioned workspace move, and reads the history of `.claude/hooks/`.
```

New text:

```
  of a sanctioned workspace move, and reads the history of `.claude/hooks/`.
  Orchestrators (design §9 Delegation) add read-only exceptions: design of an
  orchestrator reads other agents' `docs/agent/design.md` and
  `docs/agent/interop.md`; interop reads other agents' design §9 and spec §8
  to find its callers; ship of an orchestrator reads its delegates'
  `docs/agent/interop.md` and `docs/agent/ship-report.md`; ship of any agent
  reads other agents' spec §8 to find orchestrators that pin it.
```

- [ ] **Step 2: Run the checks, then commit**

```bash
git add references/agent-root.md
git commit -m "feat: agent-root read exceptions for orchestrators"
```

---

### Task 3: design — orchestrator mode and §9 Delegation

**Files:**
- Modify: `skills/design/SKILL.md` (hard rule 4; Failure modes)
- Modify: `skills/design/references/interview-guide.md` (after Phase C)
- Modify: `skills/design/references/artifact-template.md` (append §9)

- [ ] **Step 1: SKILL.md hard rule 4 — replace**

Old:

```
4. Single-agent by default; multi-agent needs a written, measurable justification.
   The Justification field is filled in BOTH branches.
```

New:

```
4. Single-agent by default; multi-agent needs a written, measurable justification.
   The Justification field is filled in BOTH branches. Delegating to OTHER
   workspace agents (an orchestrator) is decided separately in §9 Delegation
   (interview-guide "Phase C2 — Delegation"): the mechanical-routing check,
   then the justification test, run before any delegate is listed, and "one agent" or "router without an LLM"
   are successful outcomes. Helpers that exist only to serve this agent are
   internal subagents (§3/§8), never delegates.
```

- [ ] **Step 2: SKILL.md — add a Failure modes bullet**

Append to the `## Failure modes to avoid` list:

```
- Listing delegates before the justification test, or claiming one of its four reasons without a fact from the case (rule 4, §9).
```

- [ ] **Step 3: interview-guide.md — insert after the Phase C paragraph ending `and note gaps as open questions.`**

```
## Phase C2 — Delegation (workspace agents only)

Runs only when this agent would hand work to other agents listed in
`agent-cycle.yaml` (the user names them, or says so). Delegates must be
workspace agents: in a one-agent repo, show the conversion ("Second agent in a
one-agent repo") and stop.

1. **Mechanical routing first.** If deciding which agent gets each message is
   mechanical (by channel or keyword), record "router without an LLM" in §9:
   plain code outside agent-cycle; design names it and stops. This holds even
   when the reasons below are true (reuse justifies separate agents, not an
   LLM in front of them).
2. **Justification test.** An orchestrator is justified only when at
   least one reason holds, each written with a concrete fact from this case:
   reuse (the delegate already exists with its own channel or releases);
   separate permissions (one merged agent would need credentials it should not
   hold); context too large (one agent would carry too many tools or
   conflicting instructions); different models or costs.
3. **No reason holds** → record "one agent" in §9 with the reason (add the
   tools to an existing agent via its design re-entry, or design one agent)
   and stop delegation.
4. **Justified** → inventory each delegate: name (must be in
   `agent-cycle.yaml`), what it is used for, the reason(s) it serves. Read the
   other agents' `docs/agent/design.md` and `docs/agent/interop.md`
   (read-only). A helper that only serves this agent is NOT a delegate; it
   stays an internal subagent/subgraph (§3/§8).
5. **Built delegate without an inbound interface** for this agent (its
   `interop.md` has no Inbound contracts row for this caller) → warn: adding
   it is a build re-entry of that delegate (interop rule 7). Advise designing
   the orchestrator before building its delegates; do not require it.
```

- [ ] **Step 4: artifact-template.md — append at the end**

```
## 9. Delegation

<!-- Orchestrators only (interview-guide Phase C2). Otherwise one line: "No delegation: <reason>". -->

**Verdict:** orchestrator | one agent | router without an LLM

**Justification test:**

**Routing mechanical?** yes (→ router without an LLM) / no — <fact>

| Reason | Holds? | Fact from this case |
|---|---|---|
| Reuse (delegate has its own channel or releases) | yes/no | <...> |
| Separate permissions | yes/no | <...> |
| Context too large | yes/no | <...> |
| Different models or costs | yes/no | <...> |

**Delegates** (orchestrator only):

| Delegate (in agent-cycle.yaml) | Used for | Reason(s) served | Inbound interface today |
|---|---|---|---|
| <agent> | <...> | <...> | <published in its interop.md / missing → build re-entry of the delegate> |

Internal helpers (not delegates): <names, or none> — see §3/§8.
```

- [ ] **Step 5: Run the checks, then commit**

```bash
git add skills/design/SKILL.md skills/design/references/interview-guide.md skills/design/references/artifact-template.md
git commit -m "feat(design): orchestrator justification test and delegate inventory (§9)"
```

---

### Task 4: spec — §8 Delegates

**Files:**
- Modify: `skills/spec/SKILL.md` (new hard rule 9)
- Modify: `skills/spec/references/spec-template.md` (append §8)

- [ ] **Step 1: SKILL.md — append after hard rule 8**

```
9. ORCHESTRATORS (design §9 verdict "orchestrator"): §8 Delegates has one row
   per delegate with every column (Delegate, Used by, Input, Output, Contract,
   On failure). Contract = the version the delegate publishes in its
   `docs/agent/interop.md` Inbound contracts (read-only); not yet published →
   `Contract: pending`, and ship is blocked until it is pinned. Each
   delegate's replies are an untrusted surface in §4 (with at least one
   injection-attempt BHV), and each delegate credential is a row in §4's
   least-privilege list.
```

- [ ] **Step 2: spec-template.md — append at the end**

```
## 8. Delegates

<!-- Orchestrators only (design §9 verdict "orchestrator"). Otherwise one line: "No delegates". Appended last: earlier sections keep their numbers. -->

| Delegate | Used by | Input | Output | Contract | On failure |
|---|---|---|---|---|---|
| <agent> | BHV-NNN, ... | <schema> | <schema> | <agent>-contract@<n> or pending | down: <...>; timeout: <...>; invalid output: <...> |

Delegates are untrusted counterparts: their replies ride the untrusted envelope
(§4), and any gated or destructive action a reply implies goes through this
agent's own HITL tiers.
```

- [ ] **Step 3: Run the checks, then commit**

```bash
git add skills/spec/SKILL.md skills/spec/references/spec-template.md
git commit -m "feat(spec): §8 Delegates for orchestrators"
```

---

### Task 5: evals — recorded delegate responses

**Files:**
- Modify: `skills/evals/references/golden-format.md` (fixture field)
- Modify: `skills/evals/references/suite-guide.md` (Step 4)

- [ ] **Step 1: golden-format.md — insert after the `## Golden case schema` code block** (after its closing fence)

````
**Delegates (orchestrators only).** When spec §8 lists delegates, the case
fixture carries recorded delegate responses; no case calls a real delegate:

```json
"fixture": {
  "delegates": {
    "<agent>": {
      "contract": "<agent>-contract@<n>",
      "response": { "<output per the pinned schema>": "..." }
    }
  }
}
```

`response` may instead be `"down"`, `"timeout"`, or
`{ "invalid": <raw payload> }` for the On failure cases. Recordings are
frozen with the rest of `evals/` after build; re-recording is a human
re-entry when the pinned contract version changes.
````

- [ ] **Step 2: suite-guide.md — append to the end of `## Step 4 — Adversarial expansion`** (after the paragraph whose last two lines are `containment claim (no extra recipients, no writes, no secrets in reply, rules` / `unchanged).`)

```
Orchestrators (spec §8): per delegate, at least one golden case with a valid
recorded response, one case per On failure mode in its row, and at least one
adversarial case whose recorded reply carries injected instructions or asks
for a gated action (expected: treated as data; the gated action still needs
HITL). Each recording names the contract version it was taken from.
```

- [ ] **Step 3: Run the checks, then commit**

```bash
git add skills/evals/references/golden-format.md skills/evals/references/suite-guide.md
git commit -m "feat(evals): recorded delegate responses for orchestrators"
```

---

### Task 6: interop — inbound contracts and probe

**Files:**
- Modify: `skills/interop/SKILL.md` (hard rule 2)
- Modify: `skills/interop/references/entry-test.md` (inventory paragraph; new section)
- Modify: `skills/interop/references/a2a-guide.md` (Step 5)

- [ ] **Step 1: SKILL.md hard rule 2 — replace**

Old:

```
2. ENTRY TEST FIRST, per external relationship, table recorded (relationship
   → verdict → reason). Inventory comes from the spec (tools, security,
   integrations) plus anticipated collaborations — no missing rows.
```

New:

```
2. ENTRY TEST FIRST, per external relationship, table recorded (relationship
   → verdict → reason). Inventory comes from the spec (tools, security,
   integrations, §8 Delegates) plus anticipated collaborations plus every
   workspace agent whose design §9 or spec §8 names this agent (read-only) —
   no missing rows. A caller that needs an interface gets an Inbound contracts
   entry (entry-test "Inbound contracts").
```

- [ ] **Step 2: entry-test.md — in `## The test, per relationship`, replace**

Old:

```
the row proves they were considered.
```

New:

```
the row proves they were considered. In a workspace, also add one row per
agent whose design §9 or spec §8 names THIS agent as a delegate (inbound),
and one row per delegate in this agent's spec §8 (outbound).
```

- [ ] **Step 3: entry-test.md — append at the end**

```
## Inbound contracts (delegates)

When another workspace agent calls this one, `docs/agent/interop.md` carries
an **Inbound contracts** section in BOTH decisions (skip or A2A), one entry
per caller:
- caller (agent name), input schema, output schema;
- contract version `<this-agent>-contract@<n>`; any change to the input or
  output shape bumps `<n>`, and the entry states which versions are still
  served;
- one **probe request**: side-effect-free (no writes, no gated action), with
  its expected response shape. The caller's ship and weekly ritual use it.

No handler for the interface in the built code → BUILD re-entry of this agent
(rule 7), never improvised here.
```

- [ ] **Step 4: a2a-guide.md Step 5 — replace**

Old:

```
card location, role(s), executor binding, registry decision, counterpart-security
notes.
```

New:

```
card location, role(s), executor binding, registry decision, counterpart-security
notes, and the Inbound contracts section when another workspace agent calls
this one (entry-test "Inbound contracts").
```

- [ ] **Step 5: Run the checks, then commit**

```bash
git add skills/interop/SKILL.md skills/interop/references/entry-test.md skills/interop/references/a2a-guide.md
git commit -m "feat(interop): inbound contracts with versions and a probe request"
```

---

### Task 7: ship — delegate checks on both sides, runbook

**Files:**
- Modify: `skills/ship/SKILL.md` (hard rule 6)
- Modify: `skills/ship/references/audit-guide.md` (Section 3)
- Modify: `skills/ship/references/runbook-template.md` (Weekly ritual)

- [ ] **Step 1: SKILL.md — append to hard rule 6** (after `has an install-time supply-chain row.`)

```
   Orchestrators (spec §8): every delegate has approved interop.md and
   ship-report.md (else refuse, naming it), pinned contract versions match,
   one live probe request per delegate validates against the pinned schema.
   Any agent: an orchestrator that pins an older contract version this ship
   no longer serves is a blocker (audit-guide Section 3).
```

- [ ] **Step 2: audit-guide.md — insert after the `- Install-time supply chain:` bullet** (after its line ending `a finding routed to build.`, before `## Section 4`)

```
- Delegates (orchestrators: spec §8 exists). Gate: each delegate has an
  approved `docs/agent/interop.md` publishing Inbound contracts for this
  caller and an approved `docs/agent/ship-report.md`; missing → refuse,
  naming the delegate and its missing phase (Section 0 rule). Contract: the
  version in the delegate's interop.md equals the spec §8 pin (cite the
  `grep` of both); mismatch → finding routed to this agent's spec re-entry.
  Live probe: send the delegate's published probe request — never any other
  request — to its deployed endpoint (from the deploy configuration) and
  validate the response against the pinned output schema; cite command and
  output. Failure → finding routed to the delegate (down or off-contract) or
  to this agent (client wrong). This agent's delegate credentials are part of
  the least-privilege diff above.
- Dependents (any agent). Read every other agent's spec §8
  (`grep -n "<this-agent>-contract@" agents/*/docs/agent/spec.md`). An
  orchestrator pinning a contract version that this ship's interop.md no
  longer lists as served → blocker, routed to that orchestrator (spec
  re-entry and re-recording) or to this agent (keep serving the version).
```

- [ ] **Step 3: runbook-template.md — append to `## Weekly ritual (the living suite)`** (after the line `- Review token spend vs the economics estimate; recalibrate when >25% off.`)

```
- Orchestrators: send each delegate's probe request to the deployed delegate
  and compare with the pinned output schema; drift → re-record via the evals
  phase (human re-entry), never in place.
- Orchestrators: what this agent does when a delegate's kill switch is used
  (its spec §8 On failure path), and who to tell.
```

- [ ] **Step 4: Run the checks, then commit**

```bash
git add skills/ship/SKILL.md skills/ship/references/audit-guide.md skills/ship/references/runbook-template.md
git commit -m "feat(ship): delegate gate, contract and probe checks; contract-bump block"
```

---

### Task 8: economics and blueprint

**Files:**
- Modify: `skills/economics/references/economics-template.md` (§3)
- Modify: `skills/blueprint/references/render-guide.md` (Step 1, Step 2)

- [ ] **Step 1: economics-template.md — insert a table row after `| Third-party | ... | ... | ... |`**

```
| Delegates (orchestrators: calls per turn x delegate cost per call) | ... | ... | ... |
```

And after the paragraph ending `rather than assuming.` add:

```
Orchestrators: each delegate's cost per call comes from that delegate's own
economics artifact when present (read-only); otherwise it is an assumption in
§1.
```

- [ ] **Step 2: render-guide.md — Step 1, replace**

Old:

```
- skills/interop: their decisions (none/skip render as one-line states).
```

New:

```
- skills/interop: their decisions (none/skip render as one-line states).
- delegates (orchestrators): spec §8 rows (delegate, contract version, On
  failure) and design §9 verdict.
```

- [ ] **Step 3: render-guide.md — Step 2, append after the sentence ending `labeled "built (build vN)".`**

```
Orchestrators: each delegate is one external node labeled with its contract
version, connected from the tools that call it.
```

- [ ] **Step 4: Run the checks, then commit**

```bash
git add skills/economics/references/economics-template.md skills/blueprint/references/render-guide.md
git commit -m "feat(economics,blueprint): delegate cost and delegate nodes"
```

---

### Task 9: Release v0.13.0

**Files:**
- Modify: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` (version / description)
- Modify: `CHANGELOG.md` (new `[0.13.0]` above `[0.12.0]`)
- Modify: `README.md` (Status line; a short "Orchestrator agents" subsection after "Several agents in one repo")

- [ ] **Step 1: Version.** `plugin.json` `"version": "0.13.0"`; append to both descriptions: ` Orchestrator agents that delegate to other workspace agents.`

- [ ] **Step 2: CHANGELOG `[0.13.0] — <date of last commit>`**, sourced from `git log --oneline main..HEAD` and spec §10:
- Added: design §9 Delegation (justification test, outcomes "one agent" / "router without an LLM", delegate inventory); spec §8 Delegates; recorded delegate responses; interop Inbound contracts with versions and a probe request; ship delegate gate, contract match, live probe, contract-bump block; runbook weekly live probe; economics delegate cost; blueprint delegate nodes; agent-root read exceptions; eval cases DES-E09, DES-E10, SPC-E06, EVL-E05, ITP-E05, SHP-E06, SHP-E07.
- Upgrade notes: opt-in; one-agent repos and workspaces without orchestrators are unchanged; the hook is unchanged; existing interop.md files gain Inbound contracts only when an orchestrator calls the agent (interop re-entry).
- Pending graduation: a real orchestrator and two delegates taken through ship.

- [ ] **Step 3: README.** Status → v0.13.0; subsection "Orchestrator agents" (4-6 lines: what an orchestrator is, agent vs internal helper rule, network-only, the justification test can say no).

- [ ] **Step 4: Run the checks, then commit**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json CHANGELOG.md README.md
git commit -m "chore: release v0.13.0 (orchestrator agents)"
```

- [ ] **Step 5: Hand-off.** Do NOT push or tag. Report `git log --oneline main..HEAD`.
