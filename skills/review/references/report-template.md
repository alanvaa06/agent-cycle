# review.md template

Written to `docs/agent/review.md` in the reviewed repo, or the user-directed
path for foreign targets. Read-only review: this file is the ONLY write.

---
agent_name: <name or target identifier>
version: 1
status: draft            # draft | approved — human gate only
date: <YYYY-MM-DD>
reviewed_commit: <git SHA when available, else "no-git">
pipeline_artifacts_present: <none | list>
---

# <Agent> — Review

## Executive summary

Three to six sentences: what this agent is (from evidence, not assumption),
its strongest aspect, the top findings by severity, and the one-line
bottom line. A non-technical client should understand this section alone.

## Dimension verdicts

| # | Dimension | Verdict | Findings | Fix route |
|---|---|---|---|---|
| 1 | Specification | ok / findings / n-a | <count or reason> | design |
| 2 | Contracts & tools | ... | ... | spec |
| 3 | Security | ... | ... | spec / build |
| 4 | Loop & harness | ... | ... | build |
| 5 | Evals | ... | ... | evals |
| 6 | Observability | ... | ... | build / ship |
| 7 | Economics | ... | ... | economics |
| 8 | Ops | ... | ... | ship |

## Findings

One block per finding, ordered by severity:

### <SEV-severity> <short title>
- **Evidence:** `<file:line>` — <what is there> · or **not found:** <what
  was looked for and where>
- **Why it matters:** <one or two sentences, concrete failure scenario>
- **Fix route:** agent-cycle:<phase> — <what that phase would produce>

## Remediation map (the proposal)

Findings grouped by phase, in pipeline order — this is the entry plan if the
owner adopts the cycle:

| Phase | Findings it resolves | What gets produced |
|---|---|---|
| design | ... | approved design.md with metric + NO-goals |
| spec | ... | tool contracts, tiers, security posture |
| evals | ... | runnable suite incl. adversarial cases |
| build | ... | caps, envelopes, telemetry, runner |
| economics | ... | cost model + spend alarm |
| ship | ... | release audit + runbook |

## Scope notes

- This review did not execute the agent or its tests; it is a static
  assessment with file:line evidence.
- It does not replace agent-cycle:ship (release audit with a live suite
  re-run) for pipeline-born agents.
- Reviewed at <reviewed_commit>; findings age as the code moves.
