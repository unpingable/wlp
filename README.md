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

v0.2 names five artifact classes:

- `ClaimReceipt`
- `AuthorizationReceipt`
- `HandlingReceipt`
- `RevocationReceipt`
- `ContestReceipt`

`AuthorizationReceipt`, `HandlingReceipt`, and `RevocationReceipt` are
load-bearing in v0.2. v0.2 adds revocation-aware handling: a consumer may
consider a target artifact together with one or more `RevocationReceipt`s
and must refuse action when the target's standing has been revoked.
Inadmissible revocations must not bind, and revocation never erases the
historical validity of an artifact that already failed its own check.

The widened consumer API:

```
fn handle(parent: &Artifact, context: &[&Artifact], opts: &HandleOpts) -> Artifact
```

Graph-awareness is wire contract, not opt-in: every consumer declares a
context, even an empty one. See [`SPEC.md`](./SPEC.md) for the full grammar,
fail-closed rules, and v0.1 + v0.2 acceptance criteria.

## License

Apache-2.0. See [`LICENSE`](./LICENSE) and [`NOTICE`](./NOTICE).
