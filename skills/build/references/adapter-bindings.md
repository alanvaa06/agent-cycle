# Adapter bindings — agent-cycle:build

Self-contained reference. The agent core never forks per cloud — only the
adapter does, across exactly 5 bindings. Webhook-driven agents converge on the
same invariant architecture on every target because the channel's delivery
semantics (fast ack, retries, duplicates) force it:

```
INGRESS (verify + ack fast) → QUEUE (per-session ordering) → WORKER (the loop)
→ STATE (durable sessions + dedupe) → EGRESS (reply + model calls)
```

## The 5 bindings per target

| Binding | VPS (self-hosted) | AWS | GCP |
|---|---|---|---|
| Ingress | Caddy/Traefik reverse proxy → FastAPI/ASGI endpoint; TLS automatic (Caddy) | API Gateway HTTP API → thin Lambda | Cloud Run ingress service |
| Queue | Redis/Valkey list or stream, worker process consumes; strict serial per session key (per-user by default; an approver's reply is keyed to the requester's session) | SQS FIFO, MessageGroupId = session key (per-user by default; an approver's reply uses the requester's session key) | Pub/Sub, ordering key = session key (per-user by default; an approver's reply uses the requester's session key) |
| State | Postgres behind the repository interface — self-hosted in the Compose stack, or any managed Postgres (e.g. Supabase) | DynamoDB, or any managed Postgres (e.g. Supabase, RDS) behind the repository interface | Cloud SQL Postgres, Firestore, or any managed Postgres (e.g. Supabase) behind the repository interface |
| Secrets | .env file mode 0600 loaded by systemd/compose, or SOPS+age; never committed | Secrets Manager | Secret Manager |
| Deploy recipe | Docker Compose (worker + queue + proxy [+ db]); systemd only as the thing that starts Docker | SAM/CDK (Lambda) or ECS/Fargate task | gcloud run deploy / Cloud Build |

Universal rules regardless of target:
- Ingress verifies the channel signature over the RAW body before parsing,
  returns 200 fast, and drops non-allowlisted senders BEFORE the loop.
- Dedupe on the channel's message id with a unique index / conditional put —
  retries and duplicates are guaranteed by the channel, not hypothetical. The
  dedupe record also carries `processed_at`, `outcome` and the reply text, written in the
  worker's post-run transaction; on dequeue a message whose record has
  `processed_at` set is not re-run (re-send the stored reply if the send may
  not have happened, then ack). Ingress dedupe alone only catches channel
  retries; this closes queue redelivery after a worker crash.
- The worker consumes the queue serially per session key (per-user by default;
  an approver's reply is keyed to the requester's session, so ingress resolves
  it to the pending session's key before enqueueing); a running turn is never
  cancelled by a new message.
- Bind containers/services to localhost internally; only the proxy/gateway
  listens publicly.
- Health endpoint (`GET /health` or platform equivalent) for the smoke test.

Managed Postgres (Supabase) rules — any target:
- Connect directly (IPv6 or the IPv4 add-on) or through Supavisor **session**
  mode (port 5432). Never the **transaction** pooler (port 6543) with psycopg3 or asyncpg
  (prepared statements): it does not support prepared statements (psycopg3
  uses them by default, inference).
  Source: https://supabase.com/docs/guides/database/connecting-to-postgres
- State tables live in a schema not exposed by the Data API, with RLS enabled
  as defense in depth; verify with Supabase's security advisors.
  Source: https://supabase.com/docs/guides/api/securing-your-api
- The Free plan pauses projects after 7 days (1 week) of low activity and caps
  the database at 500 MB — never for a production agent.
  Sources: https://supabase.com/docs/guides/platform/free-project-pausing,
  https://supabase.com/pricing

## Runner mapping per stack

Moved to `references/bindings/<card-id>.md`, one file per stack card (the
spec's `runtime` field names the card). Each binding's "Eval runner mapping"
section gives the model double, trajectory capture, the
EXACT / IN_ORDER / ANY_ORDER mapping and harness_condition injection. The
exit-code contract is identical everywhere: 0 = every case at threshold;
pass^k is always computed by the pipeline runner.

Universal: trajectory = requested calls; `forbidden` = executed calls (the tool
wrapper records a call at body entry, after argument validation) plus reply
text; off-catalog stacks use build.md's "Off-catalog binding".

## Telemetry binding

OTel GenAI semantic conventions on every target; exporter is configuration:
self-hosted → OTLP to Phoenix/Langfuse/collector; AWS → ADOT; GCP → Cloud
Trace. Required attributes: the spec's per-turn list PLUS
`gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens` per model call
(cost calibration depends on these). Token-spend alarm: implement the
economics artifact's threshold as a metric alarm where the target supports it,
else a daily aggregation job + notification.
