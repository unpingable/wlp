# WLP open issues

Issues recorded but deliberately not solved in v0.1. Each entry names a
question, the reason it's open, and the explicit non-decision so future
versions don't accidentally treat the v0.1 behavior as ratified.

Bounded debt has a named seam, a documented failure mode, an explicit
non-authority claim, and a fixture trigger for repayment. Vibes-debt does
not. Entries here are the former.

---

## OPEN: validation_result is not action_attestation

**Status:** open, deferred to a future version. Do not solve in v0.1.

Current v0.1 behavior couples accepted handling with `acted = true` in the
happy path: the validator's `handle()` returns `acted: true` exactly when
`verdict = accepted`.

This is intentionally deferred, not resolved.

### Risk

A `HandlingReceipt` with `acted: true` may be misread downstream as proof
that WLP itself authorized or performed the underlying domain action. WLP
does neither.

### Invariant

- WLP may validate admissibility preservation across a boundary.
- WLP must not claim that the domain-side mutation actually occurred unless
  that fact is supplied by the consumer as an execution attestation.

### Repayment trigger

The first fixture where a consumer validates an artifact but declines to act
must split validation from action attestation. Until such a fixture exists,
the v0.1 coupling is acceptable.

### Likely v0.2+ shape

- `validation_verdict` — did the artifact survive the boundary?
- `consumer_decision` — does the consumer choose to act?
- `action_attestation` / `execution_claim` — did the action complete?

No redesign now. The separation should fall out of a forced fixture, not a
speculative refactor.
