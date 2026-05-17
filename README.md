# WLP

**Wire protocol for preserving admissibility across system boundaries.**

WLP is domain-semantically neutral and admissibility-semantically opinionated.

## What WLP is not

- an ontology
- a workflow engine
- a policy evaluator
- an agent protocol
- a daemon
- a trust layer
- a ledger product
- a decision engine (that is Wicket / Governor territory)
- a replacement for any local domain schema
- a substitute for transport security (TLS, mTLS, signed bundles)

WLP validates artifacts. It does not decide whether the world should have
produced them.

## Constitution

> Every WLP artifact must carry the terms under which it stops binding.

## Design rule

> WLP should make laundering harder than refusal.

## Success criterion

WLP succeeds when an artifact crosses a system boundary without losing standing,
scope, evidence, time, revocation, or contestability — and when any loss is
visible as **degradation or refusal**, never silently laundered as authority.

## The v0.1 loop

```
producer  emits   AuthorizationReceipt
consumer  validates envelope / custody / standing surface
consumer  emits   HandlingReceipt
```

The HandlingReceipt is load-bearing. It records what the consumer received,
what it accepted, what it rejected or degraded, whether it acted, and why —
linked back to its parent artifact by content hash.

## Status

v0.1 names five artifact classes:

- `ClaimReceipt`
- `AuthorizationReceipt`
- `HandlingReceipt`
- `RevocationReceipt`
- `ContestReceipt`

Three behaviors are proven by fixture:

1. Expired authorization is refused; a `HandlingReceipt` records the refusal.
2. Unsupported policy reference is refused or degraded — never silently accepted.
3. Valid authorization can be handled; a child `HandlingReceipt` references
   the parent by content hash.

See [`SPEC.md`](./SPEC.md).

## License

Apache-2.0. See [`LICENSE`](./LICENSE) and [`NOTICE`](./NOTICE).
