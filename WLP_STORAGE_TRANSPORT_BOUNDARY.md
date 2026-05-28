# WLP_STORAGE_TRANSPORT_BOUNDARY

**Status:** candidate / non-binding. Boundary record, not an integration
plan and not authorization to build.
**Filed:** 2026-05-28
**Trigger:** the operator surfaced the question of Continuity-as-WLP-
store. The answer is "plausibly yes for persistence; not for transport,"
and the distinction is load-bearing enough to record before any first
binding gets near it.

## The keepers

> **WLP preserves the artifact contract. Persistence preserves custody.
> Transport moves artifacts. Consumers decide reliance.**

> **A receipt store is not a reliance engine.**

## Position

WLP is the wire-format-and-validation layer for admissible receipts
(SPEC §1, §10; `docs/open-issues.md`). It is transport-independent by
design: artifacts may travel by files, queues, HTTP, object storage,
signed bundles, or any future substrate. Storage, discovery, indexing,
event delivery, subscription, and consumer reaction belong to adopters.

WLP can be **used by** both storage and transport substrates. WLP must
not **become** either. The roles factor cleanly:

```
WLP                     defines the artifact contract

persistence adapter     stores / retrieves WLP artifacts,
                        preserving custody metadata

transport adapter       moves / announces / subscribes /
                        replays / propagates WLP artifacts

consumer                evaluates an artifact in supplied context
                        and decides what (if anything) to rely on
```

The collapse this note exists to prevent:

```
artifact in store
  → consumer noticed
    → consumer must update
      → store became transport
        → transport became authority
```

A store does not earn delivery semantics by accumulating receipts.
A transport does not earn validation by carrying them. A consumer does
not earn reliance by retrieving.

## Naming discipline

The abstraction is **`persistence adapter`**. The descriptive phrasing,
when emphasizing what it does, is **`custody-preserving persistence
adapter`**.

Do **not** use `custody adapter` as the noun. `custody` is a load-bearing
wire-format section in every WLP artifact (SPEC §6.4 — `issuer`,
`artifact_hash`, `signature`, `causal_parents`, `receipt_hash`). A
"custody adapter" would create a second overloaded `custody`-shaped
object and force every future reader to disambiguate "the `custody`
block" from "the custody adapter." The namespace-collision shape is the
same one already worked out for verifier-the-project vs verifier-the-role
in `~/git/cartography/coordination/SELF-SUBJECT-COLLAPSE.md`.

Family, for completeness — names the slots, does not authorize them:

```
WLP persistence adapter   concrete persistence substrate binding
WLP transport adapter     future, separate; event / subscription /
                          replay / propagation surface
```

## Required invariants

A persistence adapter that claims WLP-compatibility must hold every line:

- `stored ≠ valid`
- `retrieved ≠ trusted`
- `indexed ≠ endorsed`
- `latest ≠ canonical`
- `missing ≠ false`
- `imported ≠ accepted`
- `WLP-valid envelope ≠ authorized action`
- `revocation encoded ≠ revocation propagated`
- `custody preserved ≠ channel secured`
- `persistence ≠ transport`

These are negations of the failure modes the doctrine refuses. A
candidate adapter that cannot hold them is either a transport in
disguise or a reliance engine in disguise.

## Continuity as candidate persistence substrate

Continuity is a plausible WLP persistence substrate. Its existing
discipline — *"storage is not authority; retrieval is not currency"*
(from the 2026-05-27 agent-control-surface positioning note) — is
exactly the shape WLP needs from a store: receipts whose admissibility
is judged at retrieval against `temporal_envelope` and revocation, not
by being on disk.

That fit is necessary, not sufficient. A Continuity-backed WLP
persistence adapter would require, at minimum:

- A concrete adapter mapping `Artifact` ↔ Continuity's storage primitive
  (`MemoryObject` or its successor) that preserves every `custody` field
  on round-trip — `issuer`, `artifact_hash`, `signature`, `causal_parents`,
  `receipt_hash` — without lossy summarization.
- Hash-stable retrieval. The retrieved artifact must canonicalize back
  to the same `artifact_hash` it was stored under; if not, the adapter
  is laundering and must refuse.
- Explicit non-implementation of transport semantics. No subscription,
  no notification, no presence/absence signaling, no replay ordering
  guarantees. A consumer that reads a Continuity-backed store gets an
  artifact and nothing else.

Continuity-as-WLP-**transport** is not implied by Continuity-as-WLP-
**persistence** and would require a separate gap addressing every non-
goal below.

## Non-goals

This note does **not** authorize, scope, or imply:

- A Continuity implementation plan, design preflight, or schema work.
- A registry.
- A daemon.
- A discovery protocol.
- An event stream.
- Subscription semantics.
- A revocation propagation mechanism.
- A consumer reliance policy.

Adapter implementation is downstream of any candidate adopter actually
needing it. Naming the abstraction is not authorization to build it.

## Containment

This note does not:

- Add a `persistence_adapter` or `transport_adapter` interface to WLP's
  public API.
- Modify any WLP artifact class, wire grammar, or `SPEC.md` section.
- Bind WLP to any particular storage substrate.
- Bind Continuity to any particular WLP version.
- Move any responsibility WLP currently delegates to adopters back into
  WLP itself.

WLP remains the artifact contract. Adapters remain adopter concerns.
This file names the boundary so the first persistence binding does not
silently grow transport semantics.

## Composes with

- [[WLP_STANDING_BOUNDARY_CROSSREF]] — WLP's relationship to the cross-
  constellation remote-standing doctrine. Same shape: WLP names the
  artifact; adopters name the substrate; refusing collapse between the
  two is the discipline.
- `~/git/cartography/coordination/nq-REMOTE_STANDING_BOUNDARY.md` — the
  remote-standing doctrine WLP sits beneath at the receipt/audit slot.
  Persistence vs transport is a sibling distinction at the same layer:
  storage is not delivery; delivery is not authority.
- `~/git/cartography/2026-05-27-agent-control-surface-constellation.md`
  — the positioning note that pins Continuity's *"storage is not
  authority"* discipline. This file is consistent with that posture; it
  does not extend it into integration work.

## Provenance

Filed 2026-05-28 by Wicket-Claude (acting as WLP coordinator) after the
operator surfaced *"does it make sense for Continuity to become the
store for WLP?"* The operator and chatgpt jointly factored the question
into the storage-as-evidence vs storage-as-transport split this note
records. The naming-discipline section caught the `custody` namespace
collision before it could repeat the verifier-role / verifier-project
shape worked out earlier the same day in `SELF-SUBJECT-COLLAPSE.md`.
