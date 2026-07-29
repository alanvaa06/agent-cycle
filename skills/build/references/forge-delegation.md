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

The spec's BHV scenarios are ALREADY Given/When/Then — they are the forge
PRD's acceptance criteria verbatim:

1. PRD header: agent name, goal (design's Performance metric), runtime +
   target (spec/design), constraints (loop caps, NO-goals).
2. ACs: every BHV-NNN copied verbatim, ID preserved. No paraphrase — the IDs
   are the traceability chain (BHV → eval → forge phase → test).
3. Test runner: the eval-runner command from build Step 8, stated exactly
   (e.g. `python -m evals.runner` or `pytest tests/eval_runner.py`). Forge's
   "green = exit code" rule composes with the runner's "0 = every case at
   threshold" — no opinion anywhere in the chain.
4. Build order as suggested phasing: state → tools → loop → adapter → green.

Then: forge-master:plan-design over that PRD → HUMAN approves the plan →
forge-master:forge-run executes. Never skip the human plan gate.

## The anti-gaming hook

Installed at build Step 2, BEFORE source exists. Claude Code harness — write
`.claude/settings.json` in the TARGET repo (merge if it exists):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit|NotebookEdit",
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
import json, sys, pathlib

BLOCKED = ("evals/", "docs/agent/")
ALLOWED = ("docs/agent/build.md",)

call = json.load(sys.stdin)
path = call.get("tool_input", {}).get("file_path", "")
p = pathlib.PurePosixPath(str(path).replace("\\", "/"))
rel = str(p)
for i, part in enumerate(p.parts):
    if part in ("evals", "docs"):
        rel = "/".join(p.parts[i:])
        break

if rel.startswith(BLOCKED) and rel not in ALLOWED:
    print(f"BLOCKED by agent-cycle anti-gaming rail: {rel} is a frozen "
          f"pipeline artifact. Changes go through the re-entry ladder "
          f"(dispute -> re-open the owning phase), never through the builder.",
          file=sys.stderr)
    sys.exit(2)
sys.exit(0)
```

The spec §6 Test column exception: the column is filled at build Step 9 AFTER
the suite is green — remove or bypass the hook for that single sanctioned edit
with the human's knowledge (state it at the gate), then restore it.

Fallback when no hook mechanism exists: declare in build.md that the git-diff
audit is the rail — /ship verifies `evals/` and `docs/agent/` (minus
allow-list) have zero diffs across the build's commit range.

## Disputes

The builder believing an eval or scenario is wrong is NOT a license to edit
it. Raise the dispute: name the case id, the two readings, the evidence from
the trace. The human routes it (fix-eval via /evals, fix-spec via /spec, or
overrule). The hook makes the wrong path mechanical to catch; the dispute
makes the right path cheap to take.
