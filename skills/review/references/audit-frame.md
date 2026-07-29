# Audit frame — agent-cycle:review

Eight dimensions. Each one: what to look for, the concrete probes, and the
pipeline phase that fixes its findings. Assess ALL eight; n/a needs a reason.
Evidence discipline: file:line for what exists, explicit "not found" for what
does not. Never infer architecture from genre conventions.

## 1. Specification → fixes route: agent-cycle:design

- Is there a stated purpose and a SUCCESS METRIC? Is the metric a property of
  the ENVIRONMENT (booked appointments, resolved requests) or of agent
  ACTIVITY (messages sent, tool calls)? Activity metrics are a finding.
- Goodhart probe on any metric found: if the agent optimized ONLY this, what
  is the worst way to hit the number? No counterweight → finding.
- Scope boundaries / NO-goals stated anywhere? Unbounded scope ("handle my
  inbox") is a license to be hijacked — finding, route design.

## 2. Contracts & tools → fixes route: agent-cycle:spec

- Tool interfaces: typed schemas with unknown-field rejection, or loose
  dicts? Docstrings written for the model (what/when/when-NOT), or
  implementation notes?
- Action tiers: are destructive/irreversible actions distinguishable from
  reads in the tool layer at all? Any write path without a tier concept →
  finding.
- Overlap: two tools a human cannot tell apart → routing errors — finding.
- Errors: raised into the loop (crash/retry chaos) or returned as
  observations?

## 3. Security → fixes route: agent-cycle:spec (posture) / agent-cycle:build (enforcement)

- Enumerate the REAL untrusted inputs: channels, retrieved documents/pages,
  third-party text, other agents. For each: does it reach the system prompt
  (finding: critical), or is it enveloped/quarantined?
- Least privilege: credential scopes vs what the code actually needs; one
  god-token → finding.
- Secrets: in code, in prompts, in logs? Approval gates: do dangerous actions
  ship with HITL, and are approvals per-action (cached approval = finding)?
- Extraction pattern: does untrusted content meet tool-bearing context
  directly, or is there a no-tools extraction boundary?

## 4. Loop & harness → fixes route: agent-cycle:build

- Caps: max steps, max tool calls, wall clock — in CODE or absent? Absent →
  finding (runaway loops are a cost and safety issue).
- Exits: explicit termination (answer / cap / unrecoverable error), or
  implicit "hope the model stops"?
- Topology: single agent unless a measurable reason exists; unexplained
  multi-agent → finding routed to design.
- State: durable sessions behind an interface, or in-memory only / coupled
  to one vendor store with no export path?

## 5. Evals → fixes route: agent-cycle:evals

- Do evals exist AT ALL beyond demo transcripts? None → finding (critical
  for anything with write actions): "an agent without evals is a hope."
- Coverage: behavior scenarios? adversarial/injection cases for each
  untrusted surface? Reliability: single-run or repeated (pass^k) for
  dangerous paths?
- Are they runnable (a runner, an exit code) or prose?

## 6. Observability → fixes route: agent-cycle:build (emit) / agent-cycle:ship (verify)

- Traces: any per-turn record of tool calls, outcomes, errors? Token
  counters emitted (cost calibration impossible without them)?
- Outcome taxonomy: can success/failure/refusal be told apart in telemetry,
  or does everything look like HTTP 200?

## 7. Economics → fixes route: agent-cycle:economics

- Is the monthly cost KNOWN (any model of tokens/infra/channel), or
  discovered on the invoice? No spend alarm → finding.
- Model tier chosen deliberately (cost/quality trade stated) or by default?

## 8. Ops → fixes route: agent-cycle:ship

- Kill switch: can the owner stop the agent NOW, documented? Rollback path?
- Queue/backlog handling documented? Any alarm wired to a human?
- Post-launch loop: does anything feed real failures back into tests/evals?

## Verdict discipline

Per dimension: ok / findings / n-a (+reason). Per finding: severity
(critical = exploitable or unbounded harm; important = will bite at scale or
on drift; minor = friction) + the pipeline route. The remediation map at the
end groups findings BY PHASE in pipeline order — that map is the proposal.
