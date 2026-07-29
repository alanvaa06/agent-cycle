# Adapter bindings — agent-cycle:build

Self-contained reference. The agent core never forks per cloud — only the
adapter does, across exactly 5 bindings. Webhook-driven agents converge on the
same invariant architecture on every target because the channel's delivery
semantics (fast ack, retries, duplicates) force it:

```
INGRESS (verify + ack fast) → QUEUE (per-user ordering) → WORKER (the loop)
→ STATE (durable sessions + dedupe) → EGRESS (reply + model calls)
```

## The 5 bindings per target

| Binding | VPS (self-hosted) | AWS | GCP |
|---|---|---|---|
| Ingress | Caddy/Traefik reverse proxy → FastAPI/ASGI endpoint; TLS automatic (Caddy) | API Gateway HTTP API → thin Lambda | Cloud Run ingress service |
| Queue | Redis/Valkey list or stream, worker process consumes; strict serial per sender | SQS FIFO, MessageGroupId = user id | Pub/Sub, ordering key = user id |
| State | Postgres (or Supabase Postgres) behind the repository interface | DynamoDB behind the repository interface | Firestore / Cloud SQL behind the repository interface |
| Secrets | .env file mode 0600 loaded by systemd/compose, or SOPS+age; never committed | Secrets Manager | Secret Manager |
| Deploy recipe | Docker Compose (worker + queue + proxy [+ db]); systemd only as the thing that starts Docker | SAM/CDK (Lambda) or ECS/Fargate task | gcloud run deploy / Cloud Build |

Universal rules regardless of target:
- Ingress verifies the channel signature over the RAW body before parsing,
  returns 200 fast, and drops non-allowlisted senders BEFORE the loop.
- Dedupe on the channel's message id with a unique index / conditional put —
  retries and duplicates are guaranteed by the channel, not hypothetical.
- The worker consumes the queue serially per sender; a running turn is never
  cancelled by a new message.
- Bind containers/services to localhost internally; only the proxy/gateway
  listens publicly.
- Health endpoint (`GET /health` or platform equivalent) for the smoke test.

## Runner mapping per framework

The eval suite is data; the runner binds it to a framework:

- **ADK (first documented target):** `AgentEvaluator` consumes trajectory
  expectations natively; map golden `trajectory.mode` to ADK's
  EXACT / IN_ORDER / ANY_ORDER; fixtures via session-service fakes;
  harness_condition via callback-injected step caps / erroring tool doubles.
- **Any Python framework (Pydantic AI, LangGraph, custom):** a pytest harness:
  one parametrized test per case file; fixtures build fake tool backends from
  `input.fixture`; `messages[]` replayed through the debounce path with its
  offsets; `harness_condition.force_step_cap` monkeypatches the cap,
  `tool_always_errors` swaps the named tool for an erroring double;
  trajectory captured from the loop's tool-call log and compared per mode;
  `forbidden` checked against outbound calls AND reply text; llm_judge cases
  call the judge model named in the rubric and enforce the rubric's pass
  threshold; config.yaml `thresholds` drive pytest reruns for pass^k tiers.
- Exit code contract is identical everywhere: 0 = every case at threshold.

## Telemetry binding

OTel GenAI semantic conventions on every target; exporter is configuration:
self-hosted → OTLP to Phoenix/Langfuse/collector; AWS → ADOT; GCP → Cloud
Trace. Required attributes: the spec's per-turn list PLUS
`gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens` per model call
(cost calibration depends on these). Token-spend alarm: implement the
economics artifact's threshold as a metric alarm where the target supports it,
else a daily aggregation job + notification.
