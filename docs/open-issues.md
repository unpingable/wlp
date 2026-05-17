# WLP open issues

Issues recorded but deliberately not solved in v0.1. Each entry names a
question, the reason it's open, and the explicit non-decision so future
versions don't accidentally treat the v0.1 behavior as ratified.

---

## OPEN: validation/action coupling

**Status:** open, deferred to a future version. Do not solve in v0.1.

Current v0.1 `HandlingReceipt` couples validation success and `acted = true`
in the acceptance path: the validator's `handle()` returns `acted: true`
exactly when `verdict = accepted`.

Future versions may need to separate three concerns:

- validation verdict — did the artifact survive the boundary?
- consumer decision — does the consumer choose to act?
- execution/action attestation — did the action complete?

### Reason

A consumer may validate an artifact, then decline to act for out-of-band
reasons such as:

- quorum failure
- resource unavailability
- cancellation
- local policy not represented in the WLP artifact

The v0.1 coupling collapses "validated" with "acted on," which is fine for
the three forced fixtures but will get in the way once consumers need to
emit "I validated but did not act, here is why."

### Non-decision

No redesign now. If the separation lands, it should fall out of an existing
fixture demand, not a speculative refactor.
