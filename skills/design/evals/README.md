# Eval procedure for agent-cycle:design

The skill is a human-in-the-loop process, so evals run agentically, not via pytest.

Per case in `cases.json`:

1. Start a FRESH Claude Code session in a scratch project (never this repo).
2. Paste the case's `input` verbatim as the user message.
3. Observe whether the skill fires (`fires` check) and follow the interview to
   completion for positive/edge cases (answer as a plausible dental-clinic owner).
4. Score every item in `expected.checks` as PASS / FAIL with one line of evidence.
   Presence checks require judgment on substance — a vacuous Goodhart note or a
   factually wrong architectural implication does NOT pass. For negative cases,
   also check the scratch project's filesystem afterward (e.g. no docs/agent/design.md).
5. Record the run in `results.md` (date, case id, per-check verdict, notes).

Gate: all checks PASS on all 3 cases before the skill graduates. A FAIL means
fix the SKILL.md (or the case, if the case itself is wrong — via dispute, not
silent edit) and re-run that case fresh.
