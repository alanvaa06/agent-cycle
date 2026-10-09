# Runbook template — referenced by ship findings, filled by the owner/build

Minimum viable operations runbook for a pipelined agent. The ship audit
verifies these sections exist and are actionable; it never writes them.

---

# <Agent Name> — Runbook

## Kill switch

How to stop the agent NOW, in order of speed:
1. <e.g. stop the worker service/container: exact command>
2. <e.g. disable the webhook at the provider: where, which toggle>
3. <e.g. revoke the channel token: where>
Expected effect of each (what stops, what queues, what the user sees).

## Queue / DLQ drain

- Inspect depth: <command>
- Drain safely: <command / procedure — what happens to queued turns>
- Poison message: how to identify, park, and replay one message.

## Rollback

- Current version identifier: <where it is recorded>
- Roll back to previous: <exact commands — image tag / git ref / deploy step>
- State compatibility note: <sessions/schema — safe window for rollback>

## Alarms

| Alarm | Threshold | Source | First response |
|---|---|---|---|
| Token spend | <economics §6 number> | <where it fires> | <check what, then what> |
| <queue age / DLQ depth / error rate> | ... | ... | ... |

## Weekly ritual (the living suite)

- Re-run the eval suite: <command> — investigate any new red.
- Judge spot-validation: sample N llm_judge verdicts vs human read.
- Mine corrections: user corrections from the week become candidate eval
  cases (via the evals phase, never edited in place).
- Review token spend vs the economics estimate; recalibrate when >25% off.
- Orchestrators: send each delegate's probe request to the delegate's base
  URL from this agent's deploy configuration (the key its delegate client
  reads), with this agent's delegate credential. Compare the reply with the
  pinned output schema AND with the recorded golden probe response
  (`evals/delegates/<agent>-probe.json`, or its rubric). Catches: schema
  drift, and worse content of the same shape on the probe request. Does not
  catch: worse content on requests other than the probe. Schema drift without
  a contract version bump, or worse content → route to the DELEGATE (it broke
  its contract); never re-record. Re-record (this agent's evals re-entry, a
  human) only when the delegate bumps its contract version.
- Orchestrators: what this agent does when a delegate's kill switch is used
  (its spec §8 On failure path), and who to tell.

## Contacts / escalation

- Owner: <who>. Provider status pages: <links>. Escalation order.
