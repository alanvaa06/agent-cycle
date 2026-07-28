# Eval runs — agent-cycle:spec

One row per check, per run. Verdict: PASS / FAIL. Evidence: one line.

| Date | Case | Check # | Verdict | Evidence |
|---|---|---|---|---|
| 2026-07-28 | SPC-E01* | 1 | PASS (owner) | No re-ask attested via gate approval; spec opens "design decisions are settled law here" and anchors every section in design refs |
| 2026-07-28 | SPC-E01* | 2 | PASS (owner) | All 9 design open questions map to fixed runtime decisions (Pydantic AI, Sonnet 5, .env 0600, TTL 30min, in-app HMAC, tier confirms, baseline protocol, plain read path, coverage counter) |
| 2026-07-28 | SPC-E01* | 3 | PASS | C1-C5 with BHV-001..021, unique and sequential, no gaps |
| 2026-07-28 | SPC-E01* | 4 | PASS | Every capability has happy+wrong+edge; security scenarios on top (BHV-008/012/013/020/021) |
| 2026-07-28 | SPC-E01* | 5 | PASS | "6 rows, 7 distinct operations" explicit; 7 contracts present, session_read/session_write split; none invented |
| 2026-07-28 | SPC-E01* | 6 | PASS | whatsapp_send_text kept reversible with structural justification (no recipient field = misdelivery unrepresentable); session_read split to safe, marked as tier change |
| 2026-07-28 | SPC-E01* | 7 | PASS | Conversation table: 24h window, allowlist drop, fallbacks, debounce 3s ("decided at spec level; the design was silent"), per-turn language mirroring, reply cardinality |
| 2026-07-28 | SPC-E01* | 8 | PASS | 3 untrusted surfaces each with injection BHV (008/012/013, instructions-treated-as-data); notion search titles added as surface beyond design's list; WhatsApp inbound explicitly classified trusted-by-design with reason |
| 2026-07-28 | SPC-E01* | 9 | PASS | 4-credential least-privilege table (read-only scopes) + outbound sanitizer inside send path + BHV-021 |
| 2026-07-28 | SPC-E01* | 10 | PASS | SessionRepository/DeliveryLog behind interfaces; agent_session + wa_delivery schemas, TTL and dedupe policies |
| 2026-07-28 | SPC-E01* | 11 | PASS | MD headers + tables; YAML only for the nested entity block; no JSON blobs in prose |
| 2026-07-28 | SPC-E01* | 12 | PASS | Traceability table: 21 BHV rows, eval/test columns em-dashed |
| 2026-07-28 | SPC-E01* | 13 | PASS | Frontmatter 5 fields incl. design_version: 1; approved only at owner gate |

\* Real-agent run: `whatsapp-owner-assistant` spec in `C:\Proyectos\Whatsapp_agent` (input differs from the case's literal scenario; scored mutatis mutandis). Approved without manual rework — DoD met. Notable: spec fixed the runtime as Python + Pydantic AI on VPS (was design open question 2) — /build's first adapter follows the dogfood, not the plan's ADK assumption. SPC-E02×2/E03/E04 scratch runs pending for formal graduation tag.
