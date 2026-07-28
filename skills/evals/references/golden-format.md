# Suite formats — agent-cycle:evals

The suite is DATA. No runner code, no framework imports — `/build`'s adapter
binds the runner (first documented target: ADK `AgentEvaluator` with
EXACT / IN_ORDER / ANY_ORDER trajectory modes; other frameworks map the same
fields). Everything below lands in the TARGET AGENT'S repo under `evals/`.

## Directory layout

```
evals/
  config.yaml          suite manifest + thresholds + release blockers
  golden/EVL-NNN.json  one file per case (deterministic + llm_judge)
  adversarial/ADV-NNN.json  injection/abuse cases (same schema, method fixed)
  rubrics/<name>.md    anchored rubrics for llm_judge / human_review
```

## Golden case schema (golden/EVL-NNN.json, adversarial/ADV-NNN.json)

```json
{
  "id": "EVL-001",
  "bhv_ref": "BHV-001@1",
  "method": "deterministic | llm_judge | adversarial",
  "tier": "safe | reversible | destructive",
  "input": {
    "message": "<verbatim user message, in the user's real language>",
    "messages": [ { "text": "<...>", "offset_s": 0 } ],
    "fixture": { "<world state the scenario's Given requires>": "..." }
  },
  "expected": {
    "trajectory": {
      "mode": "EXACT | IN_ORDER | ANY_ORDER",
      "tools": [ { "name": "<tool>", "args_subset": { } } ]
    },
    "asserts": [
      "<observable claim from the scenario's Then, one per line>"
    ],
    "outcome": "<value from the spec's outcome enum, if it defines one>",
    "rubric": "rubrics/<name>.md   (llm_judge only)",
    "forbidden": [
      "<strings/behaviors that must NOT appear: credentials, extra recipients, write calls>"
    ]
  },
  "human_review": false
}
```

Field rules:
- `bhv_ref` pins scenario AND spec version — a spec bump makes stale refs
  machine-detectable.
- `trajectory.mode`: ANY_ORDER is the default for independent reads; IN_ORDER
  when a dependency exists (search → get); EXACT only when order itself is the
  contract. Over-constraining trajectory is the #1 source of false FAILs.
- `args_subset` matches a subset of the real call's arguments — never require
  full argument equality (timestamps vary).
- `message` XOR `messages`: use `messages` (with second-resolution offsets) only
  for scenarios about multi-message mechanics (debounce, ordering); otherwise
  `message`.
- `fixture` may include `harness_condition` (e.g. `force_step_cap: true`,
  `tool_always_errors: "calendar_freebusy"`): a declarative condition the
  /build runner binds to its framework's mechanism. The suite stays data-only;
  expressing the condition is the eval's job, inducing it is the runner's.
- Case `tier` = the HIGHEST tier among the tools in its expected trajectory
  (a read-then-write case is reversible, not safe).
- `human_review: true` only when no rubric can reliably anchor the judgment
  (taste, brand voice); the default for judgment calls is `llm_judge` with an
  anchored rubric.
- `forbidden` is first-class: security cases usually assert absence.
- Adversarial cases: `method` fixed to `adversarial`, input carries the
  injection payload inside the fixture (event title, page body...) and the
  message is an innocent user request that surfaces it.

## config.yaml schema

```yaml
agent_name: <same-as-spec>
spec_version: <the spec version this suite covers>
status: draft            # draft | approved — human gate only
date: <YYYY-MM-DD>
dimensions:              # active for this agent, from the plugin's fixed set
  - functional_correctness
  - trajectory_quality
  - safety
  - intent_satisfaction   # llm_judge
  - cost_efficiency       # observed via telemetry, not a pass/fail case
  - self_repair           # probed by wrong-path cases (tool-failure recovery);
                          # active whenever the spec defines recovery behavior
thresholds:
  safe:        { runs: 1, passes_required: 1 }
  reversible:  { runs: 1, passes_required: 1 }
  destructive: { runs: 4, passes_required: 4 }   # pass^k, k>=4
release_blockers:
  - all adversarial cases pass          # always
  - <hard constraints lifted verbatim from the spec, e.g. zero unauthorized writes>
notes:
  red_by_design: "With no agent built, running this suite MUST produce failures."
```

## Coverage rules

Every BHV in the spec appears in exactly one of: a golden case's `bhv_ref`, an
adversarial case's `bhv_ref`, or a written gap justification in config.yaml
under `coverage_gaps:` (id + one-line reason). The spec §6 Eval column gets the
case id(s) — and ONLY that column is ever touched in spec.md.
