# Forge delegation — agent-cycle:build

/build does not reimplement loop engineering. Non-trivial builds delegate
execution to forge-master through its PUBLIC contract only: a PRD with ACs +
a test-runner command whose exit code defines green.

## When to delegate

Delegate when ANY holds: >3 tools, any non-safe tier, a queue/channel adapter,
or an eval suite with >15 cases. Direct TDD (no forge) only when ALL of:
few tools, all safe-tier, no channel infra, small suite — and record the
one-line justification in build.md.

## Mechanical PRD derivation

forge-master's real contract (verified against its installed skills): PRDs live
at `docs/forge/prd/NNN-name.md` (NNN = next number in the directory) with the
mandatory shape `## Goal / ## Non-Goals / ## User Stories (US-n, "As a
<role>...") / ## Constraints / ## Definition of Done`, ACs numbered `AC-n.m`
nested under their US-n, and stable IDs never renumbered. Derive mechanically:

1. `## Goal`: the design's Performance metric, one paragraph.
2. `## Non-Goals`: the design's NO-goals, copied.
3. `## User Stories`: one US-n per capability from the spec (C1..Cn map 1:1).
   Under each, one `AC-n.m` per BHV scenario of that capability. The AC text
   is the scenario's Given/When/Then verbatim, with the BHV id preserved as a
   leading annotation inside the text: `AC-1.2: [BHV-002] Given the calendar
   API returns 503...`. BHV ids ride inside the AC text — forge's AC-n.m
   numbering stays canonical for its machinery; the BHV annotation keeps the
   pipeline's traceability chain intact (BHV → eval → AC → phase → test).
4. `## Constraints`: runtime + target (spec/design), loop caps, the frozen-
   artifact rule (evals/ and docs/agent/ are read-only for the forge run).
5. `## Definition of Done`: the eval-runner command stated exactly (e.g.
   `python -m evals.runner`), "exit code 0 with every case at its threshold",
   plus the adapter smoke test.

Then follow forge-master's OWN two-gate process: `forge-master:prd-import` on
the derived PRD (Human Gate 1 — the human approves the PRD) →
`forge-master:plan-design` (Human Gate 2 — the human approves the plan) →
`forge-master:forge-run`. Never collapse or skip either gate. Forge's "green =
test runner exit code" composes with the runner's "0 = every case at
threshold" — no opinion anywhere in the chain.

## The anti-gaming hook

Installed at build Step 2, BEFORE source exists. Claude Code harness — write
`.claude/settings.json` in the TARGET repo (merge if it exists):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash|PowerShell",
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/guard_artifacts.py"
          }
        ]
      }
    ]
  }
}
```

And `.claude/hooks/guard_artifacts.py` (stdin receives the tool call JSON;
exit 2 blocks):

```python
import json, os, sys

BLOCKED_PREFIXES = ("evals/", "docs/agent/")
ALLOWED = ("docs/agent/build.md",)
WRITE_TOKENS = (">", ">>", "tee ", "cp ", "mv ", "rm ", "sed -i",
                "touch ", "git checkout", "git restore")

def rel_to_repo(raw):
    if not raw:
        return None
    p = str(raw).replace("\\", "/")
    try:
        rp = os.path.relpath(p, os.getcwd()).replace("\\", "/")
    except ValueError:
        return None      # different drive -> not this repo
    if rp.startswith(".."):
        return None      # outside the repo
    return rp

call = json.load(sys.stdin)
ti = call.get("tool_input", {})
hits = []

for raw in (ti.get("file_path"), ti.get("notebook_path")):
    rel = rel_to_repo(raw)
    if rel and rel.startswith(BLOCKED_PREFIXES) and rel not in ALLOWED:
        hits.append(rel)

command = str(ti.get("command", "")).replace("\\", "/")
if command and any(p in command for p in BLOCKED_PREFIXES):
    if any(t in command for t in WRITE_TOKENS) \
            and "docs/agent/build.md" not in command:
        hits.append("shell write touching a frozen path")

if hits:
    print("BLOCKED by agent-cycle anti-gaming rail: " + "; ".join(hits)
          + " — frozen pipeline artifacts. Changes go through the re-entry"
          " ladder (dispute -> re-open the owning phase), never through the"
          " builder.", file=sys.stderr)
    sys.exit(2)
sys.exit(0)
```

The spec §6 Test column exception: the column is filled at build Step 9 AFTER
the suite is green. Procedure, stated at the gate: (1) announce the sanctioned
edit to the human; (2) disable the hook by renaming
`.claude/hooks/guard_artifacts.py` to `guard_artifacts.py.off`; (3) make the
single column edit; (4) rename back; (5) VERIFY restoration — attempt a dummy
edit to `evals/config.yaml` and confirm it is blocked. A build.md DoD line
records that the verify-after-restore ran. Additionally, the hook is a first
layer, not the only one: /ship's git-diff audit over the build's commit range
(evals/ and docs/agent/ minus the allow-list must show zero diffs) is the
standing second layer on every build, hook or no hook.

## Disputes

The builder believing an eval or scenario is wrong is NOT a license to edit
it. Raise the dispute: name the case id, the two readings, the evidence from
the trace. The human routes it (fix-eval via /evals, fix-spec via /spec, or
overrule). The hook makes the wrong path mechanical to catch; the dispute
makes the right path cheap to take.
