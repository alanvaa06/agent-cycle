# Entry test — agent-cycle:skills

Skills are on-demand procedural memory: know-how loaded only when a matching
task appears. They are NOT the place for global context, tool reach, or
always-on rules. Badly built skills subtract capability — the burden of proof
is on adding one, never on skipping it.

## The test, per capability

For EVERY capability in the spec, answer in order; first "yes" that holds
decides:

1. **Static suffices?** Can this live in the agent's always-on instructions
   within budget (rule of thumb: the static block stays under ~2k tokens total
   and under ~10 always-on rules)? → tool + static instruction. No skill.
2. **Tool suffices?** Is it an action against a system with fixed semantics?
   → it is a tool contract (spec §Tools), not know-how. No skill.
3. **On-demand procedural?** Is it a multi-step procedure that (a) applies
   only when a specific task type appears, (b) varies by case/client/process,
   and (c) would bloat static instructions if always loaded? → SKILL
   candidate.
4. **Multi-agent instead?** Does it need different permissions, systems, or
   true parallelism? → that is an architecture change (re-entry to design),
   not a skill.

Record the table: capability → verdict → one-line reason. The table IS the
deliverable of the test — a bare conclusion fails the phase's own eval.

## Decision: none

A clean "none" is a SUCCESS. Record in docs/agent/skills.md:
- the per-capability table;
- why nothing qualifies (typical for v1 single-purpose agents: semantics live
  in tools, behavior in a small static block);
- **re-visit triggers** — the concrete changes that reopen this phase:
  a new client with different policies, process variants exceeding ~5,
  the static instruction block crossing its token budget, or a capability
  addition that is procedural by nature (via spec re-entry first).

## Decision: author

Only the capabilities the test flagged. Proceed to
`references/authoring-guide.md`. Never author "while we're at it" skills for
capabilities the test cleared.
