---
name: ship
description: "Phase 7 of the agent-cycle pipeline — the closing mechanical audit: full-chain gate, live suite re-run (never trusted from build.md), end-to-end traceability, security re-verification, anti-gaming word-diff audit, observability + alarm checks, runbook verification, and an explicit SHIP / NO-SHIP verdict with re-entry routes. Use when the user wants the ship audit / release check for a pipelined agent — 'run the ship audit', 'is the agent ready to ship', 'siguiente fase del pipeline' after build+conditionals. Do NOT use without the full approved chain (design+spec+evals+build+skills/interop decisions), nor for generic app deployment (Vercel/hosting setup), nor for the architecture assessment of an arbitrary agent (that is agent-cycle:review), nor to FIX anything — findings route to the re-entry ladder."
---

# agent-cycle:ship — The Audit That Closes the Pipeline

Ship audits; it never fixes. Every check is a command plus its output.
NO-SHIP is the pipeline working.

## Hard rules

1. FULL-CHAIN GATE: design, spec, evals, build approved and version-
   consistent; skills.md and interop.md present with recorded decisions
   (none/skip valid; absence is not); economics read when present. Any gap →
   refuse, name the phase, write nothing.
2. THE AUDITOR ONLY WRITES docs/agent/ship-report.md. Nothing else — not a
   fix, not a runbook, not a config touch-up. Findings route to the re-entry
   ladder with the owning phase named.
3. EVIDENCE PER COMMAND: every check cites the literal command it ran and a
   summary of its output. No command, no check. Claims in build.md are
   history, not evidence.
4. GREEN = THIS AUDIT'S RUN: the suite is re-run live via the build's runner;
   exit code, pass^k, and release blockers come from that run.
5. A red does not abort the audit — all sections complete; the verdict floor
   becomes NO-SHIP.
6. Security re-verify is mandatory: adversarial status, least-privilege diff
   (real scopes vs spec), secret scan incl. git history, ingress spot-checks
   with file:line.
7. Anti-gaming audit is mandatory: word-diff over the build's commit range on
   evals/ and docs/agent/ minus the sanctioned allow-list; hook-restore
   verification confirmed when bypassed.
8. Observability: spans with token counters evidenced; token-spend alarm
   matches the economics threshold when economics exists. Runbook verified
   against the template minimums — missing runbook is a finding referencing
   the template, never auditor-authored.
9. Verdict explicit (SHIP / NO-SHIP), findings carry severity + re-entry
   route, NO-SHIP written as the pipeline catching what it was built to
   catch. Human sign-off at the gate → approved = SHIPPED. Never
   self-approve.

## Workflow

1. Read `references/audit-guide.md`; run sections 0→7 in order, completing
   all sections regardless of reds.
2. Write docs/agent/ship-report.md (frontmatter: agent_name, version,
   status: draft, date, design_version, spec_version, evals_config_date,
   build_version) with every section's commands and evidence.
3. Present: verdict, blockers (if any) with re-entry routes, the suggested
   release tag.
4. Explicit sign-off → status: approved = SHIPPED. Findings → the owner
   routes re-entry; re-audit after.

## Failure modes to avoid

- Quoting build.md's green instead of re-running (rules 3-4).
- Stopping at the first red (rule 5).
- Fixing anything — even a one-line runbook gap (rule 2).
- An assertion without its command (rule 3).
- Accepting a missing skills.md/interop.md as "obviously none/skip" (rule 1).
- Soft-pedaling NO-SHIP (rule 9).
