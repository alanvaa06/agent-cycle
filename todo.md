# To do — decisions to revisit

## v0.13 (B2, orchestrator): when to re-record a delegate's recorded responses

Decided 2026-10-08: re-record only when the delegate's **contract version**
changes (the shape of what it returns: Agent Card / input-output schema), not
on every ship of the delegate.

Known risk: a delegate can keep the same shape and return worse content (e.g.
a wrong price). Ship does not catch that; the weekly live check against the
real delegates does.

Revisit when: delegates ship often and a content regression slips past ship,
or the weekly live check keeps finding drift. Alternative: pin the delegate's
shipped version (its ship tag), so every delegate ship forces the
orchestrator's review.
