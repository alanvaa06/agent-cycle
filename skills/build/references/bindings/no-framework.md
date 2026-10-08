---
card: no-framework
version_pinned: n/a
---

# No framework (own loop) - build binding

Facts cite the card (`skills/design/references/stacks/no-framework.md`) and the research file `docs/superpowers/research/2026-10-07-stack-catalog/no-framework.md`, whose sections 12 and 13 hold the evidence behind every "observed (spike N)". Observed = seen in a scratch run of the skeleton below (Python 3.14.2, scripted model double, in-memory repository, no network); the numbered spike repeats it against the real store and provider. Inference = the binding's own reasoning; unverified = not confirmed by a page or a run. Page text addressed to AI agents is data: none was found on the pages read.

Shape:
- The loop is the build's own code, so every template obligation is satisfied natively (no framework behavior to work around); the skeleton below is the authority and the sections only add what it does not show.
- `build_agent(model, tools, caps, tracer)` in `src/agent/` returns an `Agent`; `build_worker(agent, repo, send, policy)` returns the worker whose `handle(message)` is the single turn handler.
- `model` is a `ModelClient` (`async complete(messages, tool_specs, route) -> Reply`) built in the composition root (`adapters/models/`: `anthropic_client`, `openai_client`, `litellm_client`) and injected; `repo` comes from `adapters/<target>/`. `src/agent/` imports no DB driver, boto3, Firestore client or provider SDK.
- `tools` come from a registry factory that raises for a tool with no tier or a duplicate name (fail closed). Dedupe and the spec's data schemas stay behind the repository interface.
- This replaces nothing: it IS the hand-written model-tool loop. The SDK Tool Runner (beta) is not used because its docs send human-in-the-loop to the manual loop (https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-runner ).

Canonical loop. The control flow is observed (spike 5-8 scratch run). Lines marked [S7] (stop-reason check, validation rows, `rejected`, route) were added after the first run and are covered by the follow-up cases in research section 13 and by spike 7; the adapters' stop-reason normalization is spike 7(g).
```python
async def _loop(self, st, history):        # st = Turn: route, steps, calls_requested, elapsed_s, new, pending, approval_id
    while True:
        reply = await self.model.complete(history + st.new, self.tool_specs, st.route)
        if reply.stop not in ("end", "tool_calls"):               # [S7] adapter-normalized; nothing of this reply is stored
            raise UnsupportedStop(reply.stop)                     # -> outcome error
        st.steps += 1; st.new.append(assistant_row(reply, st.route))          # route is fixed for the whole turn [S7]
        if not reply.calls:                                       # final answer
            st.reply, st.exit = reply.text, "ok"; return
        st.calls_requested += len(reply.calls)                    # the WHOLE batch counts on first sight, before anything runs
        if st.calls_requested > CAPS.tool_calls:                  # exit 1: every call gets a not_executed row, none runs
            st.new += not_executed_rows(reply.calls, "tool-call cap"); st.exit = "tool_call_cap"; return
        if st.steps >= CAPS.steps:                                # exit 2: no request left to use the results
            st.new += not_executed_rows(reply.calls, "step cap"); st.exit = "step_cap"; return
        if any(self.is_gated(c) for c in reply.calls):            # gate: nothing in the batch runs before the decision
            st.pending, st.exit = reply.calls, "paused"; return
        await self._execute(st, reply.calls)

def is_gated(self, c):                                            # False for a call that can never run [S7]
    return self.problem(c) is None and self.tier(c) in GATED_TIERS    # problem(): unknown tool, invalid JSON or schema

async def _execute(self, st, calls, decision=None):               # persisted order, sequential
    for c in calls:
        if (p := self.problem(c)):                st.new.append(row(c, f"error: {p}", "rejected")); continue   # [S7]
        if decision and decision.denies(c):       st.new.append(row(c, decision.text, "denied")); continue
        key = f"{st.approval_id}:{c.id}" if st.approval_id and self.tier(c) != "safe" else None
        st.executed.append(c)                                       # body entry, after validation: the `forbidden` record
        try:    out, kind = await self.run_tool(c, key), "result"   # sync bodies run through asyncio.to_thread, or async-only
        except Exception: out, kind = "tool failed", "error"        # fixed text, never the exception message
        st.new.append(row(c, out, kind))

async def run(self, st, history, resume=None):   # resume = (persisted calls, decision, approval_id); new turn: None
    t0 = time.monotonic()                        # before the try, so the finally never sees an unbound name
    try:
        async with asyncio.timeout(CAPS.wall_clock - st.elapsed_s):    # remaining budget; Python 3.11+
            if resume:
                await self._execute(st, resume.calls, resume.decision)
                st.approval_id = None                       # the key belongs to the persisted batch only
            await self._loop(st, history)
    except TimeoutError: st.exit = "wall_clock"; self._close(st, history, UNKNOWN)  # clears st.pending; notice rows for unanswered calls
    except Exception:    st.exit = "error";      self._close(st, history, UNKNOWN)
    finally: st.elapsed_s += time.monotonic() - t0
```
- New turn: `st.new` starts with the user row, and that row is committed only in commit (a) with the rest of the turn. A resume starts with `st.new` empty (the history already ends with the assistant row that holds the calls).
- Tool row `kind`: `result` (body ran), `error` (body ran and raised), `rejected` (refused before any body: unknown tool, invalid JSON or schema), `denied`, `not_executed`, `interrupted`. Only `result` and `error` are executed.
- A tool body that raises becomes an `error` row with a fixed text; the tools factory wraps real bodies so the model sees the spec's error observation.
- Arguments are parsed and validated against the tool's JSON schema before anything runs. LiteLLM can return invalid JSON (https://docs.litellm.ai/docs/completion/function_call ): the call is stored with the raw string the route returned as its `args`, gets a `rejected` row, and counts as requested. Unknown tool names and schema failures are handled the same way. Such a call is never gated: the approver sees only valid gated calls, and its `rejected` row is written when the batch executes.
- Tools run sequentially in the response's order (the API leaves order to the caller: https://platform.claude.com/docs/en/agents-and-tools/tool-use/parallel-tool-use ).
- Optional `disable_parallel_tool_use` / `parallel_tool_calls=false` (same page; https://developers.openai.com/api/docs/guides/function-calling ) would cap a response at one call. The binding does not depend on it: a double or router can return several calls, and LiteLLM's mapping of `parallel_tool_calls` is not documented on the pages read (unverified).
- Context-window growth: the loop does not trim or summarize the history. The spec's conversation rules own that policy; if they are silent, record the known limit (a long session eventually exceeds the model's window and the turn ends with outcome `error`) in `build.md`.

## Sessions and state
- Own tables, all behind the repository interface:
  - `messages(session_id, seq, role, content JSON, tool_call_id, created_at)`, primary key `(session_id, seq)`. `role` is `user`, `assistant` or `tool`. `content`: user `{text}`; assistant `{text, tool_calls: [{id, name, args}], route, raw?}`; tool `{text, kind}`. The rows are append-only (the loop owns the list, so there is no diff or replace step).
  - `pending_approvals(approval_id, session_id, turn_id, route, calls JSON, history_len, steps, calls_requested, elapsed_s, requested_at, resume_started)`: at most one live row per session (unique index). `calls` is the WHOLE persisted batch (id, name, args, gated flag). `history_len` is the stored message count including the assistant row that holds the calls.
  - `turns(session_id, turn_id, message_id, status, started_at)`.
  - the ingress dedupe record keyed by the channel message id: `processed_at`, `outcome`, `reply`.
- Message format: the neutral stored shape lets a history be replayed on a route; each adapter converts at the edge.
  - Anthropic: one user message of `tool_result` blocks FIRST, then text, immediately after the assistant message (https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls ).
  - OpenAI Responses: `function_call` and `function_call_output` items keyed by `call_id` (https://developers.openai.com/api/docs/guides/function-calling ).
  - LiteLLM: OpenAI chat `tool_calls` and `tool` messages with `tool_call_id` (https://docs.litellm.ai/docs/completion/function_call ).
  - Provider ids are stored exactly as issued. `raw` holds opaque provider blocks that must come back unchanged (thinking blocks with signatures, a Gemini id's thought signature: https://docs.litellm.ai/blog/gemini_3_5_flash ).
- Pause record rules (G7): every pause writes a NEW row with a fresh UUID `approval_id` (never the session key) when the run ended in a pause (pending calls non-empty AND the run completed without exception or timeout). A wall-clock abort with a gated call pending writes no row; its calls get `interrupted` rows. `requested_at` = now, taken just before the prompt is sent. Any run started from a row deletes it in the post-run transaction unless it ended in a NEW pause, which inserts a fresh row (new id) in that same transaction. A resume checks `history_len` against the reloaded history (HITL gate, step 3).
- Turn status: `running` is written at turn start, after the repair, and overwritten with the outcome on every exit (`ok`, `step_cap`, `tool_call_cap`, `wall_clock`, `hitl_denied`, `hitl_expired`, `error`; names follow the spec). A turn that ended in a pause is `awaiting_approval` (G9); a resume sets it back to `running` in the same write that sets `resume_started`.
- Crash marker (own loop): the repair treats `running` or a missing row as a crash ("outcome unknown", never "not executed"). Rows are committed at the end of a run, so a crash mid-run stores nothing and leaves no dangling call; the marker covers a failed abort commit, a hand-edited history and any future per-step persistence (inference).
- Postgres (incl. Supabase):
  - The primary key makes a second writer an error, not a forked history; the guarantee that turns do not overlap is the queue (inference).
  - Use the direct connection or the Supavisor session mode (port 5432); never the transaction pooler (port 6543), which does not support prepared statements (the driver may use them, inference): https://supabase.com/docs/guides/database/connecting-to-postgres
  - Put the tables in a schema not exposed through the Data API (for example `agent_state`) and enable RLS on them: https://supabase.com/docs/guides/database/postgres/row-level-security
  - The Free plan pauses projects after 1 week of inactivity, so it is not for production: https://supabase.com/pricing
- DynamoDB: one item per message, partition key `session_id`, sort key `seq`, written with a condition that the key does not exist (inference); `commit_turn` is one transactional write; item-size and transaction-size limits are checked against the target table in spike 1 (not verified here).
- Firestore: `sessions/{session_id}/messages/{seq}`, one batched write per commit; a document is limited to 1 MiB (https://firebase.google.com/docs/firestore/quotas ), so very large tool results are trimmed before they are stored (the trimmed text is what the model saw).
- Queue ordering key = the session key, so one turn per session holds even when an approver is a different sender. Ingress resolves an approver's reply to the pending session's key before enqueueing.
- Schema setup (tables, indexes) runs once as the named one-shot migration job `agent-migrate` (compose service / ECS task / Cloud Run job), never from the worker.
- Commit order, every outcome:
  - (a) ONE transaction `commit_turn(session, new_rows, status, delete_approval, new_pending, dedupe)`: append the run's rows; delete the pending row the run started from (delete BEFORE insert, the unique index is per session); insert the new pending row when the run paused; set the turn status; set `processed_at`, the outcome and the reply text on the dequeued message's dedupe record.
  - (b) send the prompt or the reply. (c) ack.
  - A failure of (a) sends nothing and acks nothing (nack): the message is redelivered and runs again from the stored history (observed, spike 5); a gated tool re-run is covered by its key (HITL gate).
  - Redelivery after (a): the message's dedupe record has `processed_at`, so the worker re-sends the stored reply if the send may not have happened, then acks (observed, spike 5).
  - The step-2a expiry commit does NOT set `processed_at`; only the final commit of the turn that handles the message does (G6).
- Spikes (numbered once here, defined in the section named; each runs at build-guide Step 4). A failed store spike (1, 2) STOPS and raises a re-entry on the design's sessions seam, never a silent store swap; the others state their own failure path (a binding defect -> fix the binding; 10 -> fallback spans, then a telemetry re-entry):
  1. Store (store spike). Pass test: a history with a user row, an assistant row with two calls, two tool rows and a final assistant row is appended and reloaded in `seq` order equal to the original JSON; a duplicate `(session_id, seq)` insert is rejected. Supabase adds: tables in `agent_state` and not `public`, RLS on, round trip as the app's DB role. DynamoDB adds: conditional put rejects a duplicate and the largest commit fits the transaction limits. Firestore adds: a large result stays under the document limit.
  2. Atomic commit (store spike). Pass test: inject a failure after the messages insert inside `commit_turn`: no row, pending change, status or dedupe change survives; a success commits all of them; a pause replaces the old pending row with the new one (distinct `approval_id`).
  3. Locked install (Pinned version and traps). 4. Route conversion (Model provider; once per route the spec names; if a route cannot carry ids or blocks, raise a re-entry on the design's model_provider seam). 5. Pause and resume (HITL gate). 6. Deny and expiry (HITL gate). 7. Caps (Caps). 8. Abort and repair (Caps). 9. Eval double and tool-surface preflight (Eval runner mapping). 10. Telemetry and egress (Telemetry). 11. MCP and 12. A2A (A2A and MCP, when the design names them).

## HITL gate
- Placement: ONE gate in the loop, between the cap checks and execution (skeleton). Tier mapping: destructive -> gated every time, never cached; reversible -> per design policy (always gated, or a predicate over args); safe -> not gated. Destructive tools accept only approve or deny (the builder rejects `edit` for them).
- When ANY valid call of a response is gated the whole batch pauses and NOTHING in it runs before the decision (design choice, record in `build.md`: no half-executed batch to persist; trade-off: automatic siblings wait for the approver).
- The approval prompt is built from the stored valid gated calls, never from model text. It says "N automatic calls in the same step will also run" and that one reply applies to every gated call: the approver cannot approve one gated call and deny another.
- Worker sequence (the single turn handler; the eval runner drives it too):
  1. Dequeue the message (ordering key = session key). If its dedupe record has `processed_at` set, do not re-run it: re-send the stored reply if the send may not have happened, then ack.
  2. Read the session's `pending_approvals` row; capture `prior` = its `resume_started` (G8) now, before anything is written.
  2a. If a row exists and is older than the spec's TTL (`requested_at` is when the prompt was sent): do not resume. Write notice rows for ALL the row's calls (`EXPIRED:` text, `prior` rule below), commit them with the row deleted and status `hitl_expired`, send the spec's expiry notice only if the spec defines one, then handle the dequeued message as a new turn. This commit does NOT set `processed_at` (G6). Expiry is evaluated when the next message for the session is dequeued (a sweep is optional).
  3. If a row exists and is not expired: parse the message into a decision.
     - Check `history_len` against the reloaded history BEFORE committing anything. On a mismatch: `interrupted` rows for the batch, status `error`, row deleted, the spec's failure reply, outcome `error` (observed, spike 5 follow-up).
     - Right before a resume that can run tools (approve, edit, deny-and-continue) commit `resume_started = true` and status `running` in ONE write (G8). A deny-ends-turn path never sets it.
     - Resume = rebuild the `Turn` from the row (`route`, `steps`, `calls_requested`, `elapsed_s`, `turn_id`, `approval_id`) and call `run(st, history, resume=(persisted calls, decision, approval_id))`.
     - No row: start a NEW turn: repair (Caps), write `running`, `st.new = [user row]`, run with a fresh `Turn`.
  4. Post-run: commit (a), send (b), ack (c) as under Sessions and state. A message that ended a turn in a pause records outcome `awaiting_approval` on its dedupe record.
- Decision value, built by the worker's one builder (the eval runner uses it): `{kind: "approve" | "deny" | "edit", args?: dict, reason?: str}`.
  - approve -> execute the batch.
  - deny -> see Deny.
  - edit -> accepted only when exactly one call is gated, the spec has an edit outcome, the tool is not destructive and the new args validate against the tool's JSON schema. The executed copy carries the edited args, the stored assistant row keeps the original, and the tool row text states the args used.
  - One approve or deny reply applies to every gated call in the batch (design choice, inference).
- A message that does not parse as a decision keeps the row pending: no run, reply with the spec's pending-approval prompt (or deny if the spec says so); the dedupe record gets `processed_at`, outcome `awaiting_approval` and that reply (observed, spike 5).
- Idempotency key (G5): for every call executed on a resume whose tool is not safe, `"<approval_id>:<tool_call_id>"`, unique per APPROVED CALL.
  - `approval_id` is the fresh UUID of the row written at that pause; `tool_call_id` is the provider's call id read from the persisted batch, so the key is stable across queue redelivery (the row is deleted only in the post-run transaction).
  - A resume that pauses again writes a new row with a new id, so keys are never reused across pauses or turns.
  - The key belongs to the persisted batch only: `approval_id` is cleared from the `Turn` once the resumed batch has executed, so calls of the continued loop get no key from it (observed, spike 5 follow-up).
  - The loop passes the key to the tool body as a parameter that is NOT in the schema shown to the model; a model-supplied value is ignored. A backend with a key-length limit receives a hash of the key.
  - A crash after the approved body ran but before commit (a) leaves the row with `resume_started = true`; the redelivered message resumes again and the body runs again with the SAME key (observed, spike 5).
  - Calls of an un-paused turn have no key (their redelivery re-asks the model, so no stable id exists); they are safe or reversible-auto by design policy.
- Resume-started marker (G8): `prior` is captured at step 2 and decides the deny/expiry text: `<LABEL> was not run` normally; when `prior` is set an earlier resume may have run tools, so `<LABEL> outcome unknown - do not retry without the user`. The flag is committed only before a tool-running resume and is deleted with the row.
- Deny (state in `build.md` which variant applies):
  - Deny ends the turn: no further tool executes and no model request is made; the construct that routes to the end is the worker itself, which does not call the loop. It appends a `denied` row (`DENIED:` text, `prior` rule) for each valid gated call and a `not_executed` row ("not run: the batch was denied") for every other call of the batch, commits with status `hitl_denied` and the row deleted, sends the spec's deny reply, and records outcome `hitl_denied` (observed, spike 6).
  - The spec lets the model continue: resume with the gated calls pre-answered by `DENIED: <reason>` rows (automatic siblings run), set `resume_started` like an approve, and continue the loop; the model sees the denial.
  - A denied call still counts as requested (counted on first sight).
- Approval is not an authorization boundary against an untrusted client: only an authenticated approver identity resolved by ingress may produce a decision, and each sensitive tool checks authorization in its own body (inference; the API has no approval concept, a rejection is just a `tool_result` the build writes).
- Eval runner: the fixture's approvals enter the worker handler as decision messages and are parsed by the same builder; the runner never calls the loop itself.
- Spike 5, pause and resume (failure path: binding defect: STOP and report (build-guide Step 4)). Pass tests:
  - a response with one safe and one destructive call pauses with ZERO bodies run and the row holding both calls and the counters;
  - a NEW worker process resumes and each body runs exactly once, the destructive one with the key;
  - resume -> second pause -> second approval gives a new `approval_id`, distinct keys, and the second body runs;
  - a failed commit after the body ran leaves the row, and the redelivery runs the body again with the same key; a redelivery after a successful commit re-sends the stored reply with no model request; a failed commit sends and acks nothing;
  - a changed history length is refused with `interrupted` rows and the row deleted; a non-decision message leaves the row pending;
  - a follow-up turn on the same session succeeds against the real provider;
  - if the design sets `parallel_tool_calls` or `disable_parallel_tool_use` on the real route, a provider that still returns several calls is handled.
- Spike 6, deny and expiry (failure path: binding defect: STOP and report (build-guide Step 4)). Pass tests: after a deny under deny-ends-turn and after a step-2a expiry, a recording tool shows zero executions, the model double's request count is unchanged, every call in the batch has exactly one `DENIED:`, `EXPIRED:` or `not_executed` row, the row is gone, the expiry commit leaves `processed_at` unset, and a follow-up turn succeeds against the real provider. An ordinary deny writes "was not run"; a deny or expiry with `resume_started` already set writes "outcome unknown - do not retry without the user". Deny-and-continue (if the spec allows it) runs the gated body zero times and the next request contains the denial text.

## Caps
- Both caps are PER TURN: a new turn starts a fresh `Turn` (steps, calls_requested, elapsed_s all 0); a resume restores them from the row (observed, spike 7). Two separate counters, two separate exits; never one limit for both.
- Step cap: one step = one model request, 1:1 with the spec's step (inference); nothing converts. The check sits after a response that asks for tools and BEFORE its calls run (skeleton): a cap of N allows N requests, and a turn that spends all N on tool use trips instead of executing tools nobody will read. The final answer is also a request. Record this definition in `build.md`.
- Tool-call cap: counts each call REQUESTED, not each execution, and the WHOLE batch is counted on first sight, before any call of it executes or is gated, so parallel calls cannot overshoot (observed, spike 7: cap 2, batch of 3 -> none ran, one model request, all three `not_executed`).
  - Denied, rejected and unknown-tool calls count; a resume does not count the batch again.
  - If one response exceeds both caps the tool-call cap wins (checked first).
- Provider limits (`max_tokens`) are separate from the caps; a truncated response is outcome `error` (Model provider, stop-reason table).
- Both exits produce the spec's single failure reply and the cap outcome (`step_cap`, `tool_call_cap`, `wall_clock`, `error`). The reply is the spec's fixed text, never exception text or partial model text.
- Wall-clock cap: per TURN, resume time included.
  - The row stores `elapsed_s` at each pause and a resume gets `WALL_CLOCK - elapsed_s` (the wait for the approver is not counted; inference); a new turn gets the full limit (observed, spike 7: 0.95 s of 1.0 s used, the resume was cut after about 0.06 s).
  - `asyncio.timeout(remaining)` cancels the run, including a model call or an `async` tool; Python 3.11 or later is required (LiteLLM supports 3.10 to 3.14).
  - Tool bodies carry their own timeouts. A synchronous body run through `asyncio.to_thread` keeps running after the cancel (standard behavior, unverified here), so a wall-clock abort writes "outcome unknown - do not retry without the user" for every call without a row: the tool may have run.
- `harness_condition.force_step_cap`: the double scripts exactly `<step cap>` responses, each one safe call and no final answer, with the tool-call cap set above the step cap, so the step cap is the one that trips; a tool-cap case does the reverse. `tool_always_errors` = the tool's injected BACKEND double raises and the real tool returns the spec's error observation (build-guide Step 5); the tool surface never changes.
- No aborted turn (either cap, wall-clock, error, crash, deny-ends-turn) may leave an assistant row with calls lacking tool rows. The abort paths write their own rows at exit (`not_executed` for caps, `interrupted` for wall clock and error). The REPAIR runs at TURN START (idempotent, survives a crash), only when no approval is pending:
  - find the last assistant row, list its calls with no tool row after it, and append one notice row per missing call through the repository; stored rows are never edited;
  - text by the latest `turns` status: ONLY `step_cap`, `tool_call_cap`, `hitl_denied`, `hitl_expired` give "not executed: <status>" (kind `not_executed`); every other status (`wall_clock`, `error`, `running`) or no row gives "outcome unknown - do not retry without the user" (kind `interrupted`).
  - Observed (spike 8): statuses `running`, none and `step_cap` give the three texts, one notice per call.
- Spike 7, caps (failure path: binding defect: STOP and report (build-guide Step 4)). Pass tests:
  - (a) tool cap 2: one gated call pauses, the approval runs it, the model then requests 2 more: the third cumulative call trips `tool_call_cap` with neither extra call run;
  - (b) step cap N: exactly N requests then `step_cap`, and across a pause the total is still N;
  - (c) a batch of 3 under cap 2 runs none;
  - (d) both counters are 0 at the start of the next new turn;
  - (e) the wall-clock remainder is carried across a pause;
  - (f) invalid-JSON arguments, an unknown tool and a schema failure each produce a `rejected` row, count as requested, are never gated and do not stop the turn;
  - (g) one case PER ROUTE the spec names: a forced truncation (tiny token limit, long tool argument) on the real provider gives outcome `error`, and the truncated call is not stored or executed.
- Spike 8, abort and repair (failure path: binding defect: STOP and report (build-guide Step 4)). Pass tests: abort mid-turn (the tool cap, a wall-clock cancel during a tool, a model error), then run a follow-up turn on the same session against the real provider after the turn-start repair: it succeeds with every call paired (the provider returns a 400 on an unpaired call: https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls ). Run the repair twice: one notice per call. The next model request shows that the outcome is unknown, not that it was declined.

## Model provider
- Selection rule: when the spec pins ONE provider, call that provider's SDK directly (`anthropic` Messages API or `openai` Responses API). When the spec requires switching providers, several providers or a router, use the LiteLLM SDK (`litellm.acompletion(model="<provider>/<model>", messages=..., tools=...)`, in-process: https://docs.litellm.ai/docs/ ). The LiteLLM proxy is not part of this binding: a design that needs central keys or spend limits raises a design re-entry. The route is fixed in config, never chosen by the model.
- Route string: the spec's route is `provider/model` (LiteLLM's native form). For a direct adapter split on the first `/`: the prefix selects the adapter (`anthropic`, `openai`), the rest is the model id; any other prefix means LiteLLM. Keys come from the secret store, never from the route string.
- LiteLLM routes only: assert `litellm.supports_function_calling(model)` at startup (https://docs.litellm.ai/docs/completion/function_call ) and fail the factory otherwise. With `LITELLM_LOCAL_MODEL_COST_MAP=true` (Telemetry) a model newer than the bundled price map is unknown to that check: register it explicitly at startup (`litellm.register_model`, name unverified, spike 4 confirms) and record the model in `build.md`.
- Stop-reason normalization. Each adapter maps the route's stop signal to `Reply.stop` before the loop sees it:

  | Route | Final answer | Tool request | Everything else -> outcome error |
  |---|---|---|---|
  | Anthropic Messages | `end_turn` | `tool_use` | `max_tokens`, `stop_sequence` (the binding sets no `stop_sequences`), `pause_turn`, `refusal`, `model_context_window_exceeded` (values: https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons ) |
  | OpenAI Chat Completions | `stop` | `tool_calls` | `length`, `content_filter`, any other value (values not stated on the pages read, unverified) |
  | OpenAI Responses | status `completed`, no `function_call` item | `function_call` items | `incomplete`, `failed`, any other status (unverified) |
  | LiteLLM | `stop` | `tool_calls` (documented on the function_call page) | `length`, `content_filter`, any other value (provider values are mapped by LiteLLM, unverified) |

  - Rule: tool calls present win over the stop text, so a response with calls and a final-answer stop value is a tool request. A truncation, refusal, filter or incomplete signal is never accepted, with or without calls.
  - The Anthropic page advises retrying a truncated `tool_use` with a higher `max_tokens`; this binding deliberately does NOT: a truncated tool call is outcome `error` and nothing of it is stored.
- Route and history rules:
  - Each assistant row stores its `route` (provider/model). The route is fixed for the WHOLE turn, resume included (kept on the `Turn` and in the pending record).
  - `raw` blocks are replayed only to the same provider AND model, otherwise dropped.
  - A route change between turns counts as a switch only when the PROVIDER FAMILY changes. A model upgrade within a family is not a switch and never refuses a session.
  - For a family switch the adapter drops `raw` and remaps each id to `call_<n>` consistently in the call and its result for that request (inference; downstream reports of Anthropic rejecting tool-id formats and dropping thinking blocks through LiteLLM, status unverified: https://github.com/openai/openai-agents-python/issues/1147 , https://github.com/openai/openai-agents-python/issues/1797 ). The remap function is built ONLY when the spec names more than one provider family; otherwise the adapter refuses a history written by a foreign family and the build records that in `build.md`.
  - Ids on the same route are echoed unchanged: Gemini 3.5+ needs `functionResponse.id` to match exactly and the id embeds a thought signature (litellm >= 1.87.0.dev1: https://docs.litellm.ai/blog/gemini_3_5_flash ).
  - LiteLLM fallbacks and the Router are NOT used; any fallback is done by the adapter between turns.
- Spike 4, route conversion (real provider, once per route the spec names; failure path: fix the adapter). Pass tests:
  - one turn with a tool call returns the call with parsed arguments and a usage count above zero;
  - a response with two calls is answered by ONE request holding both results (Anthropic: one user message, results first), and the next request succeeds;
  - thinking or signature blocks (if the route returns them) round trip;
  - a history after a `DENIED:` row and after a repair notice succeeds;
  - the Gemini route (if named) echoes ids unchanged on 3 consecutive tool turns;
  - a model change inside a family continues the session; a family switch follows the rule above or is refused as stated.

## Telemetry
- Setup: `opentelemetry-sdk` and the OTLP exporter with a `BatchSpanProcessor`, endpoint = the design's backend.
  - Model-call (`chat`) spans come from exactly ONE source PER PROCESS: `AnthropicInstrumentor().instrument()` (`anthropic` SDK), `OpenAIInstrumentor().instrument()` (`openai` SDK; its docs cover chat completions and the Responses API), or `litellm.callbacks = ["otel"]` (LiteLLM route). LiteLLM may call the `openai` SDK internally (unverified), so a LiteLLM image does not also install the openai instrumentor.
  - Instrumentors are Beta (1.2b0) and the GenAI conventions are Development status, so attribute names are re-checked on every upgrade.
  - Sources: https://pypi.org/pypi/opentelemetry-instrumentation-genai-anthropic/json , https://pypi.org/pypi/opentelemetry-instrumentation-genai-openai/json , https://docs.litellm.ai/docs/observability/opentelemetry_integration
- Content capture is set EXPLICITLY, not left to defaults:
  - `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=NO_CONTENT` (the instrumentors default to no capture; the openai README writes `no_content` in lower case, so spike 10 confirms the case);
  - `litellm.turn_off_message_logging = True` (LiteLLM logs content by default);
  - `LITELLM_LOCAL_MODEL_COST_MAP=true` so importing LiteLLM does not fetch from github.com (https://raw.githubusercontent.com/BerriAI/litellm/v1.104.1/litellm/litellm_core_utils/get_model_cost_map.py ).
  - Content is switched on only when the spec's data policy allows prompts and tool output in traces.
- Own spans (the instrumentors create none of them); names and requirements: https://raw.githubusercontent.com/open-telemetry/semantic-conventions-genai/main/docs/gen-ai/gen-ai-agent-spans.md
  - `agent.turn` per turn: the spec's attributes, `agent.outcome`, steps and requested-call count (one span per run, linked by `turn_id`, when a turn spans a pause).
  - `invoke_agent {agent name}` (INTERNAL, child of `agent.turn`, one per run of the loop): `gen_ai.operation.name=invoke_agent`, `gen_ai.agent.name`, `gen_ai.conversation.id` = the session key, and `gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens` summed from the replies' provider usage.
  - `execute_tool {tool name}` (INTERNAL, child of `invoke_agent`): `gen_ai.operation.name=execute_tool`, `gen_ai.tool.name`, `gen_ai.tool.call.id`, `gen_ai.tool.type=function`, `error.type` on failure. Tool arguments and results are opt-in and sensitive and are not recorded by default.
- Fallback spans: `TracedModel` wraps any `ModelClient` and opens a `chat {model}` span from the reply's usage; it is switched on for a route whose instrumentor yields no usage (spike 10), never together with that route's instrumentor.
- Egress: no vendor egress by default. OTLP goes to the design's backend and requests go to the model provider host(s).
- Spike 10, telemetry and egress (REAL model call: a scripted double reports no usage). Pass tests:
  - one turn with a tool call emits exactly one `chat` span per model request (no duplicates from two sources), with `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens` above zero;
  - `invoke_agent` totals equal the sum of the replies; `execute_tool` spans equal the executed calls;
  - no `gen_ai.input.messages`, `gen_ai.output.messages` or tool argument attribute exists on any span;
  - with outbound traffic limited to the OTLP endpoint and the model provider, a traced turn completes and no other host is contacted, with a NEGATIVE CONTROL (an allow-list that omits the OTLP host makes the run fail, proving the check can see the traffic).
  - Failure path: switch on the fallback spans; if usage is still missing record the gap in `build.md` and raise a telemetry re-entry on the design; unexpected egress -> unset the offending callback or env and re-run, then a telemetry re-entry.

## Eval runner mapping
- Runner = worker: the eval runner drives the worker's single turn handler (dequeue logic, pending check, expiry, repair, resume-or-end, cap mapping, commit order) against an in-memory implementation of the repository interface, never the loop directly, so the deny, expiry and cap branches cannot diverge from production (observed, spike 9: the scratch tests drive the handler this way).
- Model double: a `ScriptedModel` implementing the same `complete(messages, tool_specs, route)` signature as the adapters; it returns scripted `Reply` objects (calls, then a final text), records every request, and makes no network call. A scripted reply may hold several calls, so batch and cap branches run without a provider. The provider-specific conversion is covered by spike 4 and by adapter unit tests on the request payload.
- Trajectory vs forbidden, one rule:
  - trajectory = the REQUESTED calls `(name, args)` read from the `tool_calls` of the stored assistant rows in order, including calls the cap blocked or the approver denied;
  - `forbidden` = the EXECUTED calls plus the reply text. The source of truth for executed is the tool wrapper: `_execute` records `(tool name, args, call id)` into `st.executed` at body entry, AFTER argument validation and immediately before the body runs, so a refusal (unknown tool, invalid JSON or schema, cap-blocked, denied, expired) never reaches it; executed = a tool body actually ran, whether it succeeded or raised. Tool rows of kind `result` or `error` agree with that list.
- The pipeline runner implements EXACT, IN_ORDER and ANY_ORDER itself over the trajectory list with `args_subset` matching (golden-format: expected args a subset of actual; never full-argument equality). pass^k is computed by the pipeline runner from its own per-case results (k live runs through the same handler). No framework evaluator exists or is needed.
- Approvals in a case: the fixture's approvals enter the handler as decision messages; when they run out while a pause is pending the runner fails the case with an explicit error, never waits.
- Tool-surface preflight: the eval runner AND a permanent CI unit test assert that the FIRST model request's tool names equal the spec's tool set (this binding keeps no built-in tool; any addition needs its reason in `build.md`).
  - Capture source: the `tool_specs` argument of the first `complete()` call recorded by the double. The CI test also builds each real adapter's request payload (a `build_request` dry run, no network) and compares its tool names to the same set, so a converting adapter cannot add one.
  - Negative control: the same test with one extra registered tool must fail (observed, spike 9). Test doubles do not change the tool surface.
- Spike 9, eval double and preflight (failure path: binding defect: STOP and report (build-guide Step 4)). Pass tests: the double drives a full pause, resume and finish through the worker handler on the in-memory repository and on the real repository with the same trajectory; the preflight and its negative control pass; `force_step_cap`, a tool-cap case and `tool_always_errors` give the specified outcomes.

## A2A and MCP
- A2A: own server built with `a2a-sdk` 1.2.x (spec 1.0, 0.3 compatibility; client and server roles; extras `http-server`, `fastapi`, `telemetry` and SQL task stores exist: https://pypi.org/pypi/a2a-sdk/json , https://github.com/a2aproject/a2a-python ).
  - The server sits IN FRONT of the ingress queue: each A2A task becomes a queue message with the session key as ordering key and is answered from the repository (the dedupe record's reply, or the pending state), so HITL and the caps hold. The task store holds A2A task state only, not the conversation (inference).
  - A turn that ended in a pause is answered as a task waiting for the approver (the SDK's task state name is checked in spike 12).
  - The A2A client is a tool whose tier follows the design; its result is untrusted data like any tool result (https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls ). Record the path in `interop.md`.
  - Spike 12 (when the design names A2A; failure path: binding defect: STOP and report (build-guide Step 4)): a task through the server appears in the ingress queue with the session key as ordering key, a gated tool reached through it pauses, and a decision sent as a second task message resumes it.
- MCP: `mcp` 2.3.0 (MIT, Production/Stable), `from mcp import Client`; `async with Client("https://host/mcp") as client` (Streamable HTTP; a stdio parameters object or an in-memory server for tests are the other forms: https://py.sdk.modelcontextprotocol.io/whats-new/ ).
  - The build lists the tools once at startup (`client.list_tools()`), maps each to a provider tool schema under a server-prefixed name (a collision is a startup error), and routes matching calls to `client.call_tool(name, args)` inside `execute_tool` spans, serializing the result to the tool row text.
  - An MCP tool missing from the tier table is filtered out (never offered to the model) and logged; it is not a startup crash.
  - Per-user credentials need one `Client` per session (inference). The v2 renames (`FastMCP` -> `MCPServer`, `streamablehttp_client` -> `streamable_http_client`) apply to any server code. The list result shape and the content blocks of `call_tool` are checked in spike 11.
  - Spike 11 (when the design names an MCP server; failure path: binding defect: STOP and report (build-guide Step 4)): the server's tool names appear in the first model request, an unlisted server tool does not, a destructive MCP tool pauses, and the resume runs it once with the key.

## Pinned version and traps
- Every package gets an exact pin in a LOCKFILE WITH HASHES; any ">=" in this text is a minimum, never a requirement spec. Verified on PyPI 2026-10-08 (the research file's date for the others is 2026-10-07): `litellm==1.104.1` (1.104.2 exists; not adopted, re-run the spikes before any bump), `anthropic==1.12.0` (1.12.1 exists), `openai==3.26.0` (3.26.1 exists) only in an image WITHOUT litellm; with litellm the lock must resolve `openai` below 3 (observed: `openai==2.54.0`), `mcp==2.3.0`, `a2a-sdk==1.2.2`, `opentelemetry-sdk==1.45.1`, `opentelemetry-exporter-otlp` (exact, as resolved), `opentelemetry-instrumentation-genai-anthropic==1.2b0` and `-genai-openai==1.2b0`, plus the DB driver of the chosen adapter. Python 3.11 to 3.14.
- Obligation (security): LiteLLM 1.82.7 and 1.82.8 were malicious (2026-03-24); the PyPI project listing no longer shows them (observed 2026-10-08: 1.82.6 then 1.83.0). Generate the lock with hashes (`uv pip compile requirements.in --generate-hashes`: observed, 102 packages, every one hashed; anchor `litellm-1.104.1.tar.gz` sha256 `c06d0aeef8b3f14dd6c9c6f128a7c0722bfd190f9d127e1477577fd9f0b0f37d`) and install only with `--require-hashes` (`uv pip install --require-hashes -r requirements.txt` or `pip install --require-hashes -r requirements.txt`). Sources: https://www.netspi.com/blog/executive-blog/ai-ml-pentesting/litellm-supply-chain-compromise/ , https://www.comet.com/site/blog/litellm-supply-chain-attack/
- Spike 3, locked install (failure path: fix the lock). Pass tests: a clean environment installs from the lock with `--require-hashes`; removing one hash line makes the install fail (negative control); a CI test asserts every requirement line carries `--hash`, `litellm` is neither 1.82.7 nor 1.82.8, and no package is unpinned; the lock is regenerated, never hand-edited, and the SDK versions in the image equal the lock.
- Obligation (ops): tool ids and history conversion are the build's code; run spike 4 per route and on any LiteLLM bump (Gemini needs >= 1.87.0.dev1). Sources: https://docs.litellm.ai/blog/gemini_3_5_flash , https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls
- Obligation (ops): the agent and tool spans are the build's code; the instrumentors cover model calls only. Source: https://pypi.org/pypi/opentelemetry-instrumentation-genai-anthropic/json
- Obligation (churn): OTel GenAI conventions are Development; the instrumentors are Beta; re-run spike 10 on any upgrade and keep the attribute names in one module. Source: https://raw.githubusercontent.com/open-telemetry/semantic-conventions-genai/main/docs/gen-ai/gen-ai-agent-spans.md
- Obligation (data): set content capture, `turn_off_message_logging` and `LITELLM_LOCAL_MODEL_COST_MAP=true` explicitly and prove them in spike 10. Source: https://docs.litellm.ai/docs/observability/opentelemetry_integration
- Obligation (security): tool results (web pages, email, MCP, A2A) are untrusted data; they stay in `tool` rows, never in the system prompt (https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls ).
