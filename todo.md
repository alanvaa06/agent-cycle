# To do — decisions to revisit

## v0.13 (B2, orchestrator): when to re-record a delegate's recorded responses

Decided 2026-10-08: re-record only when the delegate's **contract version**
changes (the shape of what it returns: Agent Card / input-output schema), not
on every ship of the delegate.

Known risk: a delegate can keep the same shape and return worse content (e.g.
a wrong price). Ship does not catch that. The weekly live check catches it
only on the probe request: it compares the live probe reply with the pinned
schema (schema drift) and with the recorded golden probe response or its
rubric (same shape, worse content). Worse content on any other request is not
caught. Drift or worse content without a contract bump routes to the delegate;
it is never re-recorded.

Revisit when: delegates ship often and a content regression slips past ship,
or the weekly live check keeps finding drift. Alternative: pin the delegate's
shipped version (its ship tag), so every delegate ship forces the
orchestrator's review.
